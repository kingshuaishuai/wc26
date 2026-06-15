#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""赛前情报聚合:为一场比赛拼出喂给 AI 的"档案"(dossier)。
权威主干(football-data.org 免费档):官方积分榜 + 官方比分/战绩。API 挂了自动降级到 groups.json 本地算。
best-effort(DDGS 网搜,失败就降级):伤停/首发新闻、预测阵容。
数据源可插拔:升级到付费档(赔率/阵容)只需在此扩展。"""
from __future__ import annotations

import json
import os
import time
import urllib.request

GROUPS = "ABCDEFGHIJKL"
_FD_CACHE: dict | None = None


# ---------- football-data.org(权威赛果/积分) ----------
def _fd_get(path: str) -> dict | None:
    key = os.environ.get("FOOTBALL_DATA_API_KEY", "")   # 调用时读,避免 import 早于 load_dotenv
    if not key:
        return None
    req = urllib.request.Request("https://api.football-data.org/v4" + path,
                                 headers={"X-Auth-Token": key})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read())
    except Exception as e:
        print("  fd err:", str(e)[:80])
        return None


def fd_load() -> dict:
    """一次性拉官方赛程+积分榜,整个进程缓存(省额度,10次/分钟)。"""
    global _FD_CACHE
    if _FD_CACHE is not None:
        return _FD_CACHE
    matches = _fd_get("/competitions/WC/matches") or {}
    time.sleep(7)                                        # 守 10次/分钟 限额
    standings = _fd_get("/competitions/WC/standings") or {}
    _FD_CACHE = {"matches": matches.get("matches", []), "standings": standings.get("standings", [])}
    return _FD_CACHE


def _norm(s: str) -> str:
    s = s.lower()
    for junk in (" islands", " republic", " the ", "  "):
        s = s.replace(junk, " ")
    return s.strip()


def _same_team(a: str, b: str) -> bool:
    na, nb = _norm(a), _norm(b)
    if not na or not nb:
        return False
    return na == nb or na in nb or nb in na or na.split()[0] == nb.split()[0]


# ---------- 积分榜 / 战绩 ----------
def standings_text(letter: str, data: dict) -> str:
    fd = fd_load()
    table = None
    for grp in fd["standings"]:
        if (grp.get("group") or "").upper().endswith(letter):
            table = grp.get("table")
            break
    if table:                                            # 官方积分榜
        lines = [f"Group {letter} OFFICIAL table (top 2 + best 3rd advance):"]
        for r in table:
            lines.append(f"  {r['position']}. {r['team']['name']} — {r['points']}pts "
                         f"({r['won']}W {r['draw']}D {r['lost']}L, GD {r['goalDifference']:+d}, "
                         f"played {r['playedGames']})")
        return "\n".join(lines)
    return _standings_local(letter, data)               # 降级:本地算


def team_form(team: str, data: dict) -> str:
    fd = fd_load()
    res = []
    for m in fd["matches"]:
        if m.get("status") != "FINISHED":
            continue
        h, a = m["homeTeam"]["name"], m["awayTeam"]["name"]
        ft = m.get("score", {}).get("fullTime", {})
        if ft.get("home") is None:
            continue
        if _same_team(h, team):
            res.append(f"{team} {ft['home']}-{ft['away']} {a}")
        elif _same_team(a, team):
            res.append(f"{h} {ft['home']}-{ft['away']} {team}")
    if res:
        return "; ".join(res)
    return _form_local(team, data)                       # 降级:本地算


# ---------- 降级:从 groups.json 本地算 ----------
def _standings_local(letter: str, data: dict) -> str:
    g = data[letter]
    names = [t["en"] if isinstance(t, dict) else t for t in g["teams"]]
    tb = {n: {"team": n, "p": 0, "w": 0, "d": 0, "l": 0, "gf": 0, "ga": 0, "pts": 0} for n in names}
    for m in g["matches"]:
        r = m.get("result") or {}
        if not r.get("played"):
            continue
        for side, gf, ga in ((m["home"], r["hs"], r["as"]), (m["away"], r["as"], r["hs"])):
            if side not in tb:
                continue
            t = tb[side]
            t["p"] += 1; t["gf"] += gf; t["ga"] += ga
            t["pts"] += 3 if gf > ga else (1 if gf == ga else 0)
            t["w"] += gf > ga; t["d"] += gf == ga; t["l"] += gf < ga
    rows = sorted(tb.values(), key=lambda x: (x["pts"], x["gf"] - x["ga"], x["gf"]), reverse=True)
    if not any(r["p"] for r in rows):
        return f"Group {letter}: no matches played yet."
    lines = [f"Group {letter} table (top 2 + best 3rd advance):"]
    for i, r in enumerate(rows, 1):
        lines.append(f"  {i}. {r['team']} — {r['pts']}pts ({r['w']}W {r['d']}D {r['l']}L, "
                     f"GD {r['gf']-r['ga']:+d}, played {r['p']})")
    return "\n".join(lines)


def _form_local(team: str, data: dict) -> str:
    res = []
    for L in GROUPS:
        for m in data[L]["matches"]:
            r = m.get("result") or {}
            if not r.get("played"):
                continue
            if m["home"] == team:
                res.append(f"{team} {r['hs']}-{r['as']} {m['away']}")
            elif m["away"] == team:
                res.append(f"{m['home']} {r['hs']}-{r['as']} {team}")
    return "; ".join(res) if res else "no matches played yet this tournament"


# ---------- DDGS 网搜(flaky,带重试+多查询降级) ----------
def _search(query: str, max_results: int = 4) -> list[dict]:
    try:
        from ddgs import DDGS
    except Exception:
        return []
    for fn_name in ("news", "text"):
        for _ in range(2):
            try:
                rows = list(getattr(DDGS(timeout=10), fn_name)(query, max_results=max_results))
                if rows:
                    return [{"title": str(r.get("title", "")).strip(),
                             "body": str(r.get("body", "")).strip()} for r in rows]
            except Exception:
                time.sleep(1.5)
    return []


def _fmt(rows: list[dict], limit: int = 600) -> str:
    out = []
    for r in rows:
        t, b = r.get("title", ""), r.get("body", "")
        out.append(f"- {t}: {b[:160]}" if b else f"- {t}")
    return "\n".join(out)[:limit] or "(no recent items found)"


# ---------- 组装档案 ----------
def build_dossier(m: dict, data: dict, light: bool = False) -> dict:
    """light=True:跳过 DDGS 网搜(远期比赛伤停/阵容尚不可知,且省限额),只用官方积分/战绩。"""
    home, away = m["home"], m["away"]
    if light:
        none = "(match is far out — squad news/lineups not yet available)"
        home_news = away_news = lineups = none
    else:
        home_news = _fmt(_search(f"{home} national football team injury suspension news 2026", 4))
        away_news = _fmt(_search(f"{away} national football team injury suspension news 2026", 4))
        lineups = _fmt(_search(f"{home} vs {away} World Cup 2026 predicted lineup starting XI", 3), 500)
    return {
        "standings": standings_text(m["group"], data),
        "home_form": team_form(home, data),
        "away_form": team_form(away, data),
        "home_news": home_news, "away_news": away_news, "lineups": lineups,
    }


if __name__ == "__main__":  # 自测
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
    d = json.load(open(os.path.join(os.path.dirname(__file__), "data", "groups.json"), encoding="utf-8"))
    for L in GROUPS:
        for m in d[L]["matches"]:
            if not (m.get("result") or {}).get("played") and m.get("kickoff_utc"):
                print(f"=== {m['home']} vs {m['away']} (Group {L}) ===")
                for k, v in build_dossier(m, d).items():
                    print(f"\n[{k}]\n{v}")
                raise SystemExit
