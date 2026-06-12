#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""博客生成器:已踢比赛每场出一篇英文图文。
- 文:DeepSeek(deepseek-v4-pro)。命中→"how we called it";失手→诚实复盘。
- 图:MiniMax 文生图(原创编辑级配图,避开版权;不扒直播画面)。
幂等:已生成的(data/blog.json 里有)跳过。供 CI 自动调用。"""
import json, os, re, time, urllib.request, urllib.parse

ROOT = os.path.dirname(os.path.abspath(__file__))
DK_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
MM_KEY = os.environ.get("MINIMAX_API_KEY", "")
DK_URL = "https://api.deepseek.com/chat/completions"
MM_URL = "https://api.minimaxi.com/v1/image_generation"
IMG_DIR = os.path.join(ROOT, "assets", "blog")
BLOG_JSON = os.path.join(ROOT, "data", "blog.json")


def _post(url, key, payload, timeout=120):
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def write_post(m):
    """DeepSeek 写一篇 match recap,返回 {title, dek, body:[段落...]}。"""
    r = m["result"]; p = m.get("pred_en", {})
    ph_pa = p.get("score", "")
    pm = re.match(r"(\d+)-(\d+)", ph_pa or "")
    exact = bool(pm) and int(pm.group(1)) == r["hs"] and int(pm.group(2)) == r["as"]
    po = ao = None
    if pm:
        po = "h" if int(pm.group(1)) > int(pm.group(2)) else ("a" if int(pm.group(1)) < int(pm.group(2)) else "d")
        ao = "h" if r["hs"] > r["as"] else ("a" if r["hs"] < r["as"] else "d")
    hit = exact or (po == ao)
    angle = ("We predicted this result correctly — write a confident but classy 'how our model "
             "called it' recap, noting what our pre-match read got right." if hit else
             "Our prediction MISSED. Write an HONEST post-mortem: own the miss plainly, then analyse "
             "what actually happened and why our model was wrong. No spin, no excuses.")
    sys_p = ("You are a sharp football writer for OracleXI, an AI-prediction site. Write tight, "
             "engaging English match blog posts. Be specific and honest. No betting advice.")
    usr = (f"Match: {m['home']} {r['hs']}-{r['as']} {m['away']} (2026 World Cup, Group {m['group']}).\n"
           f"Our pre-match AI prediction: {ph_pa}. Key player tip: {p.get('star','')}.\n"
           f"Pre-match analysis we published: {p.get('analysis','')}\n"
           f"ANGLE: {angle}\n"
           "Return STRICT JSON: {\"title\":\"<punchy <=70 chars>\","
           "\"dek\":\"<1-sentence standfirst <=120 chars>\","
           "\"body\":[\"<para>\",\"<para>\",\"<para>\",\"<para>\"]}. 4 paragraphs, ~70-90 words each.")
    d = _post(DK_URL, DK_KEY, {
        "model": "deepseek-v4-pro",
        "messages": [{"role": "system", "content": sys_p}, {"role": "user", "content": usr}],
        "response_format": {"type": "json_object"}, "temperature": 0.7})
    out = json.loads(d["choices"][0]["message"]["content"])
    out["verdict"] = "exact" if exact else ("hit" if hit else "miss")
    return out


def make_image(m, slug):
    """MiniMax 文生图 → 下载到 assets/blog/{slug}.jpg,返回相对路径(失败返回 '')。"""
    prompt = (f"Editorial sports magazine cover illustration evoking a football match between "
              f"{m['home']} and {m['away']}, dramatic stadium atmosphere, dynamic action, "
              f"cinematic lighting, dark charcoal background with lime-green and teal accents, "
              f"premium minimal poster style, NO text, NO logos, NO real faces.")
    try:
        d = _post(MM_URL, MM_KEY, {"model": "image-01", "prompt": prompt,
                                   "aspect_ratio": "16:9", "n": 1}, timeout=90)
        url = (d.get("data") or {}).get("image_urls", [None])[0]
        if not url:
            print("  image: no url", str(d.get("base_resp")))
            return ""
        os.makedirs(IMG_DIR, exist_ok=True)
        path = os.path.join(IMG_DIR, f"{slug}.jpg")
        urllib.request.urlretrieve(url, path)
        return f"assets/blog/{slug}.jpg"
    except Exception as e:
        print("  image err:", str(e)[:100])
        return ""


def main():
    data = json.load(open(os.path.join(ROOT, "data", "groups.json"), encoding="utf-8"))
    blog = {"posts": []}
    if os.path.exists(BLOG_JSON):
        blog = json.load(open(BLOG_JSON, encoding="utf-8"))
    done = {p["match"] for p in blog["posts"]}
    played = [m for L in "ABCDEFGHIJKL" for m in data[L]["matches"]
              if (m.get("result") or {}).get("played")]
    new = 0
    for m in played:
        mid = f"{m['group'].lower()}{m['match_no']}"
        if mid in done:
            continue
        slug = slugify(f"{m['home']}-{m['result']['hs']}-{m['result']['as']}-{m['away']}")
        print(f"[blog] generating {mid}: {m['home']} vs {m['away']}")
        try:
            post = write_post(m)
        except Exception as e:
            print("  text err:", str(e)[:120]); continue
        img = make_image(m, slug)
        blog["posts"].append({
            "match": mid, "slug": slug, "date": m["date"],
            "home": m["home"], "away": m["away"],
            "score": f"{m['result']['hs']}-{m['result']['as']}",
            "pred": m.get("pred_en", {}).get("score", ""),
            "verdict": post["verdict"], "title": post["title"], "dek": post["dek"],
            "body": post["body"], "image": img,
        })
        new += 1
        time.sleep(1)
    blog["posts"].sort(key=lambda p: (p["date"], p["match"]), reverse=True)
    json.dump(blog, open(BLOG_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"✅ blog: +{new} new, {len(blog['posts'])} total")


if __name__ == "__main__":
    main()
