#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""每日 X 帖助手:挑当天最该发的一场比赛 → 生成预测卡图 + 写好 X 文案 →
飞书推送给用户(可直接复制的主推文 + 带链接的回复 + 卡图本地路径),用户手动发(30秒)。
不自动发帖(X新号自动发=对空气喊+可能违规),只把"写好+提醒"这步包掉。供本地 cron 调用。"""
import datetime
import json
import os
import subprocess

from dotenv import load_dotenv

ROOT = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(ROOT, "..", "..", ".env"))

import make_card  # noqa: E402  复用出卡逻辑

DK_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DK_URL = "https://api.deepseek.com/chat/completions"
LARK = "/Users/yishuai/.nvm/versions/node/v22.21.1/bin/lark-cli"
USER_OPEN_ID = "ou_59d7058088d720766c3387c9aeafdb98"
BASE = "https://oraclexi.com"
STATE_PATH = os.path.join(ROOT, "data", "x_posted.json")
GROUPS_PATH = os.path.join(ROOT, "data", "groups.json")
BG = os.path.join(ROOT, "assets", "opener_bg.jpg")


def now_utc():
    return datetime.datetime.now(datetime.timezone.utc)


def parse_iso(s):
    return datetime.datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)


def lark(markdown):
    if not os.path.exists(LARK):
        print("[x_daily] lark-cli 不在,改打印到 stdout\n" + markdown)
        return
    subprocess.run([LARK, "im", "+messages-send", "--as", "bot", "--user-id", USER_OPEN_ID,
                    "--markdown", markdown, "--json"], capture_output=True, text=True, timeout=30)


def _slug(s):
    return "".join(c for c in s if c.isalnum())


def pick_match(data, posted):
    """挑:未踢、有开球时间、还没发过的,最近开球那场(最具时效=最该发)。"""
    cand = []
    now = now_utc()
    for L in "ABCDEFGHIJKL":
        for i, m in enumerate(data[L]["matches"], 1):
            if (m.get("result") or {}).get("played"):
                continue
            ko = m.get("kickoff_utc")
            if not ko:
                continue
            kt = parse_iso(ko)
            if kt <= now:
                continue
            mid = f"{L}{m['match_no']}"
            if mid in posted:
                continue
            cand.append((kt, L, i, m, mid))
    cand.sort(key=lambda x: x[0])
    return cand[0] if cand else None


def write_copy(m):
    """DeepSeek 写主推文(无链接,争取最大触达);失败用模板兜底。"""
    p = m.get("pred_en", {})
    w = round((p.get("win") or 0) * 100)
    dr = round((p.get("draw") or 0) * 100)
    l = round((p.get("lose") or 0) * 100)
    factor = (p.get("key_factors") or [""])[0]
    fallback = (f"🔮 {m['home']} vs {m['away']}: our AI calls it {p.get('score','-')}. "
                f"{m['home']} {w}% · Draw {dr}% · {m['away']} {l}%. "
                f"Watch {p.get('star','')}. #WorldCup2026 #{_slug(m['home'])} #{_slug(m['away'])}")
    if not DK_KEY:
        return fallback
    sys_p = ("You are the social editor for OracleXI, an AI World Cup prediction site. Write ONE punchy, "
             "value-first X post about an upcoming match's AI prediction. Lead with a hook or sharp insight, "
             "state the predicted score and the single most interesting reason, confident not hypey, "
             "UNDER 250 characters, NO link (it goes in a reply), end with 2-3 relevant hashtags. "
             "Return STRICT JSON.")
    usr = (f"Match: {m['home']} vs {m['away']} (2026 World Cup, Group {m['group']}).\n"
           f"AI prediction: score {p.get('score')}, win/draw/lose {w}%/{dr}%/{l}%, key player {p.get('star')}.\n"
           f"Top factor: {factor}\nAnalysis: {(p.get('analysis') or '')[:300]}\n"
           'Return JSON: {"tweet":"<the post, <250 chars, with hashtags, no link>"}')
    try:
        import urllib.request
        req = urllib.request.Request(DK_URL, data=json.dumps({
            "model": "deepseek-v4-pro",
            "messages": [{"role": "system", "content": sys_p}, {"role": "user", "content": usr}],
            "response_format": {"type": "json_object"}, "temperature": 0.8}).encode(),
            headers={"Authorization": f"Bearer {DK_KEY}", "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=90) as r:
            out = json.loads(json.loads(r.read())["choices"][0]["message"]["content"])
        return (out.get("tweet") or fallback)[:275]
    except Exception as e:
        print("[x_daily] copy err:", str(e)[:90])
        return fallback


def main():
    data = json.load(open(GROUPS_PATH, encoding="utf-8"))
    posted = json.load(open(STATE_PATH, encoding="utf-8")) if os.path.exists(STATE_PATH) else []
    picked = pick_match(data, posted)
    if not picked:
        print("没有可发的未来比赛")
        return
    kt, L, idx, m, mid = picked
    card = make_card.make(L, str(idx), BG)
    tweet = write_copy(m)
    url = f"{BASE}/match/{m['group'].lower()}{m['match_no']}"
    reply = f"Full breakdown + all 104 AI predictions 👉 {url}"
    hrs = (kt - now_utc()).total_seconds() / 3600
    msg = (f"📣 **今日 X 帖(到点发)** — {m['home']} v {m['away']}(约{hrs:.0f}h后开球)\n"
           f"━━━━━━━━━━━━━━\n"
           f"**① 主推文**(复制这段,配卡图发):\n{tweet}\n\n"
           f"**② 发完在自己推文下回复这条**(带链接):\n{reply}\n\n"
           f"🖼 预测卡图:`{card}`\n"
           f"🔗 比赛页:{url}\n"
           f"━━━━━━━━━━━━━━\n"
           f"发法:发①+附卡图 → 在该推文下回复②。链接放回复=主推触达更高。")
    lark(msg)
    posted.append(mid)
    json.dump(posted[-200:], open(STATE_PATH, "w", encoding="utf-8"), ensure_ascii=False)
    print(f"✅ 已推送今日 X 帖:{m['home']} v {m['away']} | 卡图 {card}")


if __name__ == "__main__":
    main()
