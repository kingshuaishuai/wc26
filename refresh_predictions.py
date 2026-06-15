#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""动态预测:赛前用聚合情报(官方积分/战绩 + 新闻/阵容)逐因子重算未踢比赛的预测。
诚实铁律:**只更新未开球的比赛**,开球即冻结,战绩永远只算开球时锁定的那版。
没变就不动:只有实质变化(比分/概率/出线含义变)才落库 groups.json + 追加一条预测分析(pred_history),
            触发重建部署;否则只更新本地节流状态(pred_state.json,不进 git,不触发空部署)。
节流:每场默认约每天刷一次,临近开球(<12h)加密到每3h(抓首发)。供本地 cron 调用(密钥仅本地)。"""
import datetime
import json
import os
import time
import urllib.request

from dotenv import load_dotenv

ROOT = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(ROOT, "..", "..", ".env"))

import scout  # noqa: E402  (scout 调用时读 env,放 load_dotenv 之后)

DK_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DK_URL = "https://api.deepseek.com/chat/completions"
STATE_PATH = os.path.join(ROOT, "data", "pred_state.json")
GROUPS_PATH = os.path.join(ROOT, "data", "groups.json")

WINDOW_H = 72            # 只刷新未来72h内开球的比赛
NEAR_H = 12             # 12h内算"临近"(首发将出),刷新更勤
REFRESH_NEAR_MIN = 180  # 临近:距上次>3h才再刷
REFRESH_FAR_MIN = 1200  # 较远:>20h才再刷(≈每天一次)
PROB_DELTA = 0.07       # 胜平负概率变化≥7个百分点=实质变化


def _post(url, key, payload, timeout=120):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def now_utc():
    return datetime.datetime.now(datetime.timezone.utc)


def parse_iso(s):
    return datetime.datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)


def iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


SYS_P = (
    "You are OracleXI's lead football analyst producing disciplined, evidence-based 2026 FIFA World Cup "
    "match predictions. Hard rules:\n"
    "1. Reason FACTOR BY FACTOR from the EVIDENCE provided (group standings & qualification stakes, both "
    "teams' tournament form, injuries/suspensions, predicted lineups). Do not invent facts unsupported by "
    "the evidence or well-established reality.\n"
    "2. CALIBRATE probabilities to reality: draws are common (often 22-32%); blowouts are rare; evenly "
    "matched sides get close probabilities. Reserve lopsided splits (e.g. 75/18/7) for genuine "
    "mismatches backed by evidence. win+draw+lose must sum to ~1.0.\n"
    "3. Be DISCIPLINED, not reactive: only change a prior call when evidence justifies it; if news is thin "
    "or irrelevant, keep your prior call and say so.\n"
    "4. 'star' MUST be a real, named player likely to feature — never a number or a position.\n"
    "5. Output STRICT JSON only, no prose outside it."
)


def repredict(m, dossier):
    p = m.get("pred_en", {})
    usr = (
        f"MATCH: {m['home']} vs {m['away']} — 2026 World Cup, Group {m['group']}, "
        f"kickoff {m.get('kickoff_utc')} UTC, venue {m.get('venue') or 'TBD'}.\n\n"
        f"=== EVIDENCE ===\n"
        f"GROUP SITUATION:\n{dossier['standings']}\n\n"
        f"{m['home']} TOURNAMENT FORM: {dossier['home_form']}\n"
        f"{m['away']} TOURNAMENT FORM: {dossier['away_form']}\n\n"
        f"{m['home']} NEWS (injuries/suspensions/form):\n{dossier['home_news']}\n\n"
        f"{m['away']} NEWS (injuries/suspensions/form):\n{dossier['away_news']}\n\n"
        f"PREDICTED LINEUPS / PREVIEW:\n{dossier['lineups']}\n\n"
        f"=== YOUR PRIOR CALL ===\n"
        f"score {p.get('score')}, win/draw/lose {p.get('win')}/{p.get('draw')}/{p.get('lose')}, "
        f"star {p.get('star')}.\nprior analysis: {p.get('analysis', '')}\n\n"
        "Return STRICT JSON:\n"
        '{"score":"H-A","win":0.0,"draw":0.0,"lose":0.0,"star":"<named player>",'
        '"confidence":"low|medium|high",'
        '"key_factors":["<short factor>","<short factor>"],'
        '"analysis":"<120-180 words, evidence-based; cite the specific standings/form/injury factors '
        'that drive your call; calibrated and honest>",'
        '"changed":true/false,'
        '"change_reason":"<if changed vs prior, the new evidence that drove it; else empty>"}'
    )
    d = _post(DK_URL, DK_KEY, {"model": "deepseek-v4-pro",
        "messages": [{"role": "system", "content": SYS_P}, {"role": "user", "content": usr}],
        "response_format": {"type": "json_object"}, "temperature": 0.3})
    out = json.loads(d["choices"][0]["message"]["content"])
    # 概率归一化,保证和≈1
    s = sum(float(out.get(k, 0) or 0) for k in ("win", "draw", "lose"))
    if s > 0:
        for k in ("win", "draw", "lose"):
            out[k] = round(float(out.get(k, 0) or 0) / s, 2)
    return out


def is_material(old, new):
    """新预测相对当前是否实质变化(决定是否落库+追加分析)。"""
    if not old or not old.get("score"):
        return True                                      # 首次接地气预测
    if old.get("score") != new.get("score"):
        return True
    for k in ("win", "draw", "lose"):
        if abs(float(old.get(k) or 0) - float(new.get(k) or 0)) >= PROB_DELTA:
            return True
    return False


def main():
    data = json.load(open(GROUPS_PATH, encoding="utf-8"))
    state = json.load(open(STATE_PATH, encoding="utf-8")) if os.path.exists(STATE_PATH) else {}
    now = now_utc()
    changed = checked = 0

    for L in "ABCDEFGHIJKL":
        for m in data[L]["matches"]:
            if (m.get("result") or {}).get("played"):
                continue
            ko = m.get("kickoff_utc")
            if not ko:
                continue
            kt = parse_iso(ko)
            if now >= kt:                                # 冻结:已开球绝不更新
                continue
            hrs = (kt - now).total_seconds() / 3600
            if hrs > WINDOW_H:
                continue
            mid = f"{m['group'].lower()}{m['match_no']}"
            last = state.get(mid)
            if last:                                     # 节流
                mins = (now - parse_iso(last)).total_seconds() / 60
                if mins < (REFRESH_NEAR_MIN if hrs <= NEAR_H else REFRESH_FAR_MIN):
                    continue

            checked += 1
            state[mid] = iso(now)                        # 记录本次已检查(无论是否变化)
            try:
                dossier = scout.build_dossier(m, data)
                up = repredict(m, dossier)
            except Exception as e:
                print("  repredict err", m["home"], str(e)[:90])
                continue

            old = dict(m.get("pred_en", {}))
            first = not (m.get("pred_history"))          # 首次接地气预测:即便同分也入库,补真分析+真球员
            if not first and not is_material(old, up):
                print(f"  no change: {m['home']} vs {m['away']} (still {old.get('score')})")
                continue

            p = m.setdefault("pred_en", {})              # 落库当前预测
            for k in ("score", "star", "analysis", "confidence"):
                if up.get(k):
                    p[k] = up[k]
            for k in ("win", "draw", "lose"):
                if up.get(k) is not None:
                    p[k] = up[k]
            p["key_factors"] = up.get("key_factors") or []
            p["updated_utc"] = iso(now)

            hist = m.setdefault("pred_history", [])      # 追加一条预测分析(详情页时间线)
            hist.append({
                "ts": iso(now), "date": now.strftime("%Y-%m-%d"),
                "score": up.get("score"), "win": up.get("win"), "draw": up.get("draw"),
                "lose": up.get("lose"), "star": up.get("star"),
                "confidence": up.get("confidence"), "key_factors": up.get("key_factors") or [],
                "analysis": up.get("analysis", ""),
                "change_reason": (up.get("change_reason") or
                                  ("Initial evidence-based prediction from official standings, form and "
                                   "team news." if first else "Updated on new evidence.")),
            })
            changed += 1
            print(f"CHANGED {m['home']} vs {m['away']} → {up.get('score')} "
                  f"({old.get('score')}→{up.get('score')}, {hrs:.0f}h to KO, conf={up.get('confidence')})")
            time.sleep(1)

    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    json.dump(state, open(STATE_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    if changed:                                          # 只有实质变化才改 groups.json(避免空部署)
        json.dump(data, open(GROUPS_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"✅ checked {checked}, materially changed {changed}")


if __name__ == "__main__":
    main()
