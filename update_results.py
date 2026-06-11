#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从维基百科拉取已踢比赛的真实比分，合并进 groups.json，
计算积分榜与 AI 预测命中率，写入 data/meta.json。可被 CI 定时调用。"""
import urllib.request, urllib.parse, json, re, os, time

ROOT = os.path.dirname(os.path.abspath(__file__))
UA = {"User-Agent": "OracleXI/1.0 (worldcup predictions; contact@oraclexi.dev)"}

def fetch(page):
    url = f"https://en.wikipedia.org/w/api.php?action=parse&page={urllib.parse.quote(page)}&prop=text&format=json&disablelimitreport=1"
    req = urllib.request.Request(url, headers=UA)
    for a in range(3):
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                return json.loads(r.read())["parse"]["text"]["*"]
        except Exception as e:
            if a == 2: raise
            time.sleep(2)

def clean(s):
    import html as H
    s = re.sub(r"<[^>]+>", "", s); s = H.unescape(s).replace("\xa0", " ")
    return re.sub(r"\s+", " ", s).strip()

def parse_scores(raw):
    """返回 [(home, away, hs, as)] 仅含已出比分的比赛。"""
    out = []
    boxes = re.split(r'class="footballbox"', raw)[1:]
    homes = re.findall(r'class="fhome"[^>]*>(.*?)</th>', raw, re.S)
    scores = re.findall(r'class="fscore"[^>]*>(.*?)</th>', raw, re.S)
    aways = re.findall(r'class="faway"[^>]*>(.*?)</th>', raw, re.S)
    for i in range(min(len(homes), len(aways))):
        h = clean(homes[i]); a = clean(aways[i])
        sc = clean(scores[i]) if i < len(scores) else ""
        m = re.match(r"(\d+)\s*[–\-:]\s*(\d+)", sc)
        if h and a and m:
            out.append((h, a, int(m.group(1)), int(m.group(2))))
    return out

def standings(teams_en, matches):
    tbl = {t: {"team": t, "P":0,"W":0,"D":0,"L":0,"GF":0,"GA":0,"GD":0,"Pts":0} for t in teams_en}
    for m in matches:
        r = m.get("result")
        if not r or not r.get("played"): continue
        h, a, hs, as_ = m["home"], m["away"], r["hs"], r["as"]
        if h not in tbl or a not in tbl: continue
        for t,gf,ga in [(h,hs,as_),(a,as_,hs)]:
            tbl[t]["P"]+=1; tbl[t]["GF"]+=gf; tbl[t]["GA"]+=ga; tbl[t]["GD"]=tbl[t]["GF"]-tbl[t]["GA"]
        if hs>as_: tbl[h]["W"]+=1; tbl[h]["Pts"]+=3; tbl[a]["L"]+=1
        elif hs<as_: tbl[a]["W"]+=1; tbl[a]["Pts"]+=3; tbl[h]["L"]+=1
        else: tbl[h]["D"]+=1; tbl[a]["D"]+=1; tbl[h]["Pts"]+=1; tbl[a]["Pts"]+=1
    return sorted(tbl.values(), key=lambda x:(-x["Pts"],-x["GD"],-x["GF"]))

def main():
    data = json.load(open(os.path.join(ROOT,"data","groups.json"), encoding="utf-8"))
    played = 0; correct_outcome = 0; correct_score = 0
    for L in "ABCDEFGHIJKL":
        g = data[L]
        idx = {(m["home"], m["away"]): m for m in g["matches"]}
        try:
            results = parse_scores(fetch(f"2026 FIFA World Cup Group {L}"))
        except Exception as e:
            print(f"Group {L} fetch failed: {e}"); results=[]
        for h,a,hs,as_ in results:
            m = idx.get((h,a))
            if not m: continue
            m["result"] = {"played": True, "hs": hs, "as": as_}
            played += 1
            # 命中率：以英文预测为准
            pred = m.get("pred_en", {})
            ps = pred.get("score","")
            pm = re.match(r"(\d+)\s*-\s*(\d+)", ps or "")
            actual_out = "h" if hs>as_ else ("a" if hs<as_ else "d")
            if pm:
                phs,pas = int(pm.group(1)),int(pm.group(2))
                pred_out = "h" if phs>pas else ("a" if phs<pas else "d")
                if pred_out==actual_out: correct_outcome += 1
                if phs==hs and pas==as_: correct_score += 1
        g["standings"] = standings([t["en"] for t in g["teams"]], g["matches"])
        time.sleep(0.3)
    meta = {
        "played": played, "total": 72,
        "outcome_acc": round(correct_outcome/played*100,1) if played else None,
        "score_acc": round(correct_score/played*100,1) if played else None,
        "updated_utc": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()),
    }
    json.dump(data, open(os.path.join(ROOT,"data","groups.json"),"w"), ensure_ascii=False, indent=2)
    json.dump(meta, open(os.path.join(ROOT,"data","meta.json"),"w"), ensure_ascii=False, indent=2)
    print(f"已更新：已踢 {played} 场 | 胜负命中 {meta['outcome_acc']}% | 比分命中 {meta['score_acc']}% | {meta['updated_utc']}")

if __name__ == "__main__":
    main()
