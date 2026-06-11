#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把全站 URL 提交给 IndexNow（Bing/Yandex 快速收录）。CI 每次部署后调用。"""
import urllib.request, json, os, re

ROOT = os.path.dirname(os.path.abspath(__file__))

def base_url():
    # 从 build.py 的 BASE 常量读取，保持单一事实来源
    src = open(os.path.join(ROOT, "build.py"), encoding="utf-8").read()
    m = re.search(r'BASE\s*=\s*"([^"]+)"', src)
    return m.group(1) if m else None

def main():
    keyf = os.path.join(ROOT, ".indexnow_key")
    if not os.path.exists(keyf):
        print("no indexnow key, skip"); return
    KEY = open(keyf).read().strip()
    base = base_url()
    if not base: print("no BASE, skip"); return
    host = re.sub(r"https?://", "", base).split("/")[0]
    data = json.load(open(os.path.join(ROOT, "data", "groups.json"), encoding="utf-8"))
    urls = [f"{base}/", f"{base}/sitemap.xml"]
    for L in "ABCDEFGHIJKL":
        urls.append(f"{base}/group/{L}.html")
        for m in data[L]["matches"]:
            urls.append(f"{base}/match/{m['group'].lower()}{m['match_no']}.html")
    payload = {"host": host, "key": KEY, "keyLocation": f"{base}/{KEY}.txt", "urlList": urls}
    req = urllib.request.Request("https://api.indexnow.org/indexnow",
        data=json.dumps(payload).encode(), headers={"Content-Type": "application/json; charset=utf-8"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            print(f"IndexNow {r.status} ({len(urls)} urls)")
    except urllib.error.HTTPError as e:
        print(f"IndexNow HTTP {e.code} ({len(urls)} urls)")

if __name__ == "__main__":
    main()
