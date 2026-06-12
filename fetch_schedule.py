#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从维基百科抓每场的开球时间(含未踢场次),算出 UTC 时间写进 groups.json 的 kickoff_utc。
footballbox 文本格式: "( 2026-06-11 ) 1:00 p.m. UTC−6 Mexico 2–0 ..."。供 CI 调用,best-effort。"""
import urllib.request, urllib.parse, json, re, os, time, html as H, datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
UA = {"User-Agent": "OracleXI/1.0 (worldcup predictions)"}


def fetch(page):
    url = f"https://en.wikipedia.org/w/api.php?action=parse&page={urllib.parse.quote(page)}&prop=text&format=json&disablelimitreport=1"
    req = urllib.request.Request(url, headers=UA)
    for a in range(3):
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                return json.loads(r.read())["parse"]["text"]["*"]
        except Exception:
            if a == 2:
                raise
            time.sleep(2)


def clean(s):
    s = re.sub(r"<[^>]+>", "", s)
    return re.sub(r"\s+", " ", H.unescape(s).replace("\xa0", " ")).strip()


_KO = re.compile(
    r"\(\s*(\d{4})-(\d{2})-(\d{2})\s*\)\s*(\d{1,2}):(\d{2})\s*(a\.m\.|p\.m\.)\s*UTC([+−\-])(\d{1,2})")


def parse_kickoffs(raw):
    """返回 [(home, away, kickoff_utc_iso)]。"""
    boxes = re.split(r'class="footballbox"', raw)[1:]
    homes = re.findall(r'class="fhome"[^>]*>(.*?)</th>', raw, re.S)
    aways = re.findall(r'class="faway"[^>]*>(.*?)</th>', raw, re.S)
    out = []
    for i, box in enumerate(boxes):
        if i >= len(homes) or i >= len(aways):
            break
        h, a = clean(homes[i]), clean(aways[i])
        txt = H.unescape(re.sub(r"<[^>]+>", " ", box[:700]))
        m = _KO.search(txt)
        if not (h and a and m):
            continue
        y, mo, d, hh, mm, ap, sign, off = (int(m.group(1)), int(m.group(2)), int(m.group(3)),
                                           int(m.group(4)) % 12, int(m.group(5)), m.group(6),
                                           m.group(7), int(m.group(8)))
        if ap == "p.m.":
            hh += 12
        if sign in ("−", "-"):
            off = -off
        dt = datetime.datetime(y, mo, d, hh, mm) - datetime.timedelta(hours=off)
        out.append((h, a, dt.strftime("%Y-%m-%dT%H:%M:%SZ")))
    return out


def main():
    path = os.path.join(ROOT, "data", "groups.json")
    data = json.load(open(path, encoding="utf-8"))
    n = 0
    for L in "ABCDEFGHIJKL":
        idx = {(m["home"], m["away"]): m for m in data[L]["matches"]}
        try:
            kos = parse_kickoffs(fetch(f"2026 FIFA World Cup Group {L}"))
        except Exception as e:
            print(f"Group {L} failed: {e}"); kos = []
        for h, a, ko in kos:
            m = idx.get((h, a))
            if m:
                m["kickoff_utc"] = ko
                n += 1
        time.sleep(3)  # 放慢避免维基 429
    json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"✅ kickoff times set on {n} matches")


if __name__ == "__main__":
    main()
