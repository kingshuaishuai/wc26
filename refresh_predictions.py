#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""动态预测:赛前用最新球队新闻(伤停/首发/状态)重算未踢比赛的预测。
诚实铁律:**只更新未开球的比赛**;一旦开球就冻结,战绩永远只算开球时锁定的那版。
节流:只刷新未来 WINDOW_H 内开球的;临近开球刷得更勤(抓首发)。供本地 cron 调用(密钥仅本地)。"""
import json, os, re, time, urllib.request, datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
DK_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DK_URL = "https://api.deepseek.com/chat/completions"
WINDOW_H = 48          # 只刷新未来48h内开球的比赛
NEAR_H = 4             # 4h内算"临近"(首发将出),刷新更勤
REFRESH_NEAR_MIN = 60  # 临近:距上次更新>60min才再刷
REFRESH_FAR_MIN = 360  # 较远:>6h才再刷


def _post(url, key, payload, timeout=90):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def now_utc():
    return datetime.datetime.now(datetime.timezone.utc)


def parse_iso(s):
    return datetime.datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)


def team_news(team):
    """搜某队最近一周的伤停/首发/状态新闻,返回标题拼接(失败空串)。"""
    try:
        from ddgs import DDGS
        rows = list(DDGS(timeout=8).news(
            f"{team} football team news injury lineup", max_results=4, timelimit="w"))
        if not rows:
            rows = list(DDGS(timeout=8).text(f"{team} World Cup squad injury news", max_results=4))
        return " | ".join(str(r.get("title", "")).strip() for r in rows if r.get("title"))[:600]
    except Exception as e:
        print("  news err:", str(e)[:80]); return ""


def repredict(m, nh, na):
    p = m.get("pred_en", {})
    sys_p = ("You are a professional football match predictor for OracleXI. Update your pre-match "
             "prediction using the latest team news (injuries, suspensions, likely lineups, form). "
             "If the news is thin or irrelevant, keep your prior call. Be disciplined, not reactive. "
             "Return STRICT JSON only.")
    usr = (f"Match: {m['home']} vs {m['away']} (2026 World Cup, Group {m['group']}, "
           f"kickoff {m.get('kickoff_utc')} UTC).\n"
           f"CURRENT prediction: score {p.get('score')}, win/draw/lose "
           f"{p.get('win')}/{p.get('draw')}/{p.get('lose')}, key player {p.get('star')}.\n"
           f"Prior analysis: {p.get('analysis','')}\n"
           f"LATEST {m['home']} news: {nh or '(none found)'}\n"
           f"LATEST {m['away']} news: {na or '(none found)'}\n"
           'Return JSON: {"score":"H-A","win":0.0,"draw":0.0,"lose":0.0,"star":"player",'
           '"analysis":"<=70 words; if team news changed the call, say what and why",'
           '"changed":true/false}')
    d = _post(DK_URL, DK_KEY, {"model": "deepseek-v4-pro",
        "messages": [{"role": "system", "content": sys_p}, {"role": "user", "content": usr}],
        "response_format": {"type": "json_object"}, "temperature": 0.4})
    return json.loads(d["choices"][0]["message"]["content"])


def main():
    path = os.path.join(ROOT, "data", "groups.json")
    data = json.load(open(path, encoding="utf-8"))
    now = now_utc()
    refreshed = 0
    for L in "ABCDEFGHIJKL":
        for m in data[L]["matches"]:
            if (m.get("result") or {}).get("played"):
                continue
            ko = m.get("kickoff_utc")
            if not ko:
                continue
            kt = parse_iso(ko)
            if now >= kt:           # 冻结:已开球绝不更新
                continue
            hrs = (kt - now).total_seconds() / 3600
            if hrs > WINDOW_H:      # 太远,先不动
                continue
            last = m.get("pred_updated_utc")
            if last:                # 节流:还没到再刷的间隔就跳过
                mins = (now - parse_iso(last)).total_seconds() / 60
                if mins < (REFRESH_NEAR_MIN if hrs <= NEAR_H else REFRESH_FAR_MIN):
                    continue
            nh, na = team_news(m["home"]), team_news(m["away"])
            try:
                up = repredict(m, nh, na)
            except Exception as e:
                print("  repredict err", m["home"], str(e)[:90]); continue
            p = m.setdefault("pred_en", {})
            for k in ("score", "star", "analysis"):
                if up.get(k):
                    p[k] = up[k]
            for k in ("win", "draw", "lose"):
                if up.get(k) is not None:
                    p[k] = up[k]
            m["pred_updated_utc"] = now.strftime("%Y-%m-%dT%H:%M:%SZ")
            refreshed += 1
            print(f"refreshed {m['home']} vs {m['away']} → {p.get('score')} "
                  f"(changed={up.get('changed')}, {hrs:.0f}h to KO)")
            time.sleep(1)
    json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"✅ refreshed {refreshed} matches")


if __name__ == "__main__":
    main()
