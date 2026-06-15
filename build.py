#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""WC26 Predictions — English static site generator (home + 12 groups + 72 match pages)."""
import json, os, shutil, html, math
from datetime import date, datetime, timedelta

ROOT = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(ROOT, "dist")
DATA = json.load(open(os.path.join(ROOT, "data", "groups.json"), encoding="utf-8"))
_meta_path = os.path.join(ROOT, "data", "meta.json")
META = json.load(open(_meta_path, encoding="utf-8")) if os.path.exists(_meta_path) else {}
_blog_path = os.path.join(ROOT, "data", "blog.json")
BLOG = json.load(open(_blog_path, encoding="utf-8")) if os.path.exists(_blog_path) else {"posts": []}
TODAY = date.today().isoformat()
BASE = "https://oraclexi.com"
SITE = "OracleXI"
# 填入 AdSense 发布商ID(形如 ca-pub-1234567890123456)后，自动广告脚本会注入全站 <head>，并生成 ads.txt
ADSENSE_PUB = os.environ.get("ADSENSE_PUB", "")
DESC = "AI predictions for all 104 matches of the 2026 FIFA World Cup — score predictions, win probabilities and expert analysis for every fixture across all 12 groups."

MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
WK = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
def fmt_date(d):
    if not d: return "TBD"
    y,m,dd = map(int, d.split("-"))
    return f"{WK[date(y,m,dd).weekday()]}, {MONTHS[m-1]} {dd}"

def esc(s): return html.escape(str(s)) if s else ""

# 内联 SVG 图标集(Lucide 风格,描边,currentColor 跟随主题色)。替代廉价 emoji。
_ICON = {
    "target": '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>',
    "check": '<circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/>',
    "x": '<circle cx="12" cy="12" r="10"/><path d="m15 9-6 6"/><path d="m9 9 6 6"/>',
    "pin": '<path d="M20 10c0 4.993-5.539 10.193-7.399 11.799a1 1 0 0 1-1.202 0C9.539 20.193 4 14.993 4 10a8 8 0 0 1 16 0"/><circle cx="12" cy="10" r="3"/>',
    "star": '<path d="M11.525 2.295a.53.53 0 0 1 .95 0l2.31 4.679a2.123 2.123 0 0 0 1.595 1.16l5.166.756a.53.53 0 0 1 .294.904l-3.736 3.638a2.123 2.123 0 0 0-.611 1.878l.882 5.14a.53.53 0 0 1-.771.56l-4.618-2.428a2.122 2.122 0 0 0-1.973 0L6.396 21.01a.53.53 0 0 1-.77-.56l.881-5.139a2.122 2.122 0 0 0-.611-1.879L2.16 9.795a.53.53 0 0 1 .294-.906l5.165-.755a2.122 2.122 0 0 0 1.597-1.16z"/>',
    "alert": '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"/><path d="M12 9v4"/><path d="M12 17h.01"/>',
    "download": '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="M7 10l5 5 5-5"/><path d="M12 15V3"/>',
    "trophy": '<path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6"/><path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18"/><path d="M4 22h16"/><path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22"/><path d="M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22"/><path d="M18 2H6v7a6 6 0 0 0 12 0V2Z"/>',
    "refresh": '<path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/><path d="M8 16H3v5"/>',
}
def icon(name, cls=""):
    return (f'<svg class="ic {cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
            f'{_ICON[name]}</svg>')

def adsense_head():
    if not ADSENSE_PUB: return "<!-- AD_HEAD_SLOT -->"
    return (f'<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js'
            f'?client={ADSENSE_PUB}" crossorigin="anonymous"></script>')

ALL = []
for L in "ABCDEFGHIJKL":
    for m in DATA[L]["matches"]:
        ALL.append(m)
ALL.sort(key=lambda m:(m["date"] or "9999", m.get("match_no") or 0))

def mslug(m): return f"{m['group'].lower()}{m['match_no']}"
def murl(m): return f"match/{mslug(m)}"
def P(m): return m.get("pred_en", {})
import re as _re
def tslug(name): return _re.sub(r"[^a-z0-9]+","-",name.lower()).strip("-")
def turl(name): return f"team/{tslug(name)}"
def clean(p):
    # Cloudflare 服务的是去.html的干净URL,canonical/sitemap必须对齐,否则Google吃到308=Page with redirect
    if p in ("", "index.html"): return ""              # 首页 → 根
    if p.endswith("/index.html"): return p[:-10]       # blog/index.html → blog/
    return p[:-5] if p.endswith(".html") else p        # about.html → about

def _clean_links(html):
    # 构建后统一把站内 a 链接的 .html 去掉,对齐 Cloudflare 的干净URL(外链/锚点/资源不动)
    def repl(m):
        path, anchor = m.group(1), m.group(2) or ""
        if path == "index": path = ""                  # index.html → 目录
        elif path.endswith("/index"): path = path[:-5] # blog/index → blog/
        return f'href="{path}{anchor}"'
    return _re.sub(r'href="(?!https?:|//|mailto:)([^"#]*?)\.html(#[^"]*)?"', repl, html)
# 队名 -> 所在组
TEAM_GROUP = {t["en"]: L for L in "ABCDEFGHIJKL" for t in DATA[L]["teams"]}

def jsonld(obj):
    return f'<script type="application/ld+json">{json.dumps(obj, ensure_ascii=False)}</script>'

def crumbs_ld(items):
    return jsonld({"@context":"https://schema.org","@type":"BreadcrumbList",
        "itemListElement":[{"@type":"ListItem","position":i+1,"name":n,"item":f"{BASE}/{clean(u)}"} for i,(n,u) in enumerate(items)]})

def head(title, desc, rel="", canon="", ld="", img="", meta_extra=""):
    og_img = f"{BASE}/{img}" if img else f"{BASE}/assets/og.jpg"
    return f"""<!DOCTYPE html><html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{BASE}/{clean(canon)}">
{meta_extra}<meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(desc)}">
<meta property="og:type" content="website"><meta property="og:url" content="{BASE}/{clean(canon)}">
<meta property="og:image" content="{og_img}"><meta name="twitter:image" content="{og_img}">
<meta name="twitter:card" content="summary_large_image">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Anton&family=Sora:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{rel}style.css">
<link rel="icon" href="{rel}favicon.svg" type="image/svg+xml">
{adsense_head()}
{ld}
</head><body>
<header class="nav"><div class="wrap">
<a class="brand" href="{rel}index.html"><span class="mark"><span>XI</span></span> OracleXI</a>
<input type="checkbox" id="nav-toggle" class="nav-toggle" hidden>
<label for="nav-toggle" class="hamburger" aria-label="Menu"><span></span><span></span><span></span></label>
<nav><a href="{rel}index.html">Home</a><a href="{rel}index.html#groups">Groups</a><a href="{rel}index.html#upcoming">Predictions</a><a href="{rel}blog/index.html">Blog</a><a href="{rel}data.html">Free Data</a></nav>
</div></header>"""

def foot(rel=""):
    return f"""<footer><div class="wrap">
<div>© 2026 OracleXI · Data from public schedules · Predictions generated by AI for entertainment only</div>
<div><a href="{rel}index.html">Home</a> · <a href="{rel}blog/index.html">Blog</a> · <a href="{rel}about.html">About</a> · <a href="{rel}privacy.html">Privacy</a> · <a href="mailto:contact@oraclexi.com">Contact</a></div>
</div></footer>
<script>
const io=new IntersectionObserver((es)=>es.forEach(e=>{{if(e.isIntersecting){{e.target.style.animationDelay=(e.target.dataset.d||0)+'ms';e.target.classList.add('fade');io.unobserve(e.target)}}}}),{{threshold:.08}});
document.querySelectorAll('[data-reveal]').forEach((el,i)=>{{el.dataset.d=(i%6)*60;io.observe(el)}});
(function(){{
 var cd=document.querySelector('.countdown[data-kickoff]'); if(!cd) return;
 var ko=cd.getAttribute('data-kickoff'), label=document.querySelector('.next-label'),
     clock=cd.querySelector('.cd-clock'), cdl=cd.querySelector('.cd-label');
 if(!ko){{cd.style.display='none'; return;}}
 var t=new Date(ko).getTime(), p=function(n){{return (n<10?'0':'')+n;}};
 function tick(){{
  var diff=t-Date.now();
  if(diff>0){{var s=Math.floor(diff/1000),d=Math.floor(s/86400),h=Math.floor(s%86400/3600),m=Math.floor(s%3600/60),x=s%60;
   clock.textContent=(d>0?d+'d ':'')+p(h)+'h '+p(m)+'m '+p(x)+'s'; cdl.textContent='Kicks off in'; if(label)label.textContent='Next match';}}
  else if(diff>-9000000){{clock.textContent='LIVE'; cd.classList.add('live'); cdl.textContent='Now playing'; if(label)label.textContent='Live now';}}
  else {{clock.textContent='Full time'; cdl.textContent='';}}
 }}
 tick(); setInterval(tick,1000);
}})();
(function(){{
 var chips=document.querySelectorAll('.ko-chip[data-ko]'); if(!chips.length) return;
 function rel(ko){{var diff=new Date(ko).getTime()-Date.now();
  if(diff<=0) return diff>-9000000?'LIVE':'FT';
  var s=Math.floor(diff/1000),d=Math.floor(s/86400),h=Math.floor(s%86400/3600),m=Math.floor(s%3600/60);
  return d>0?('in '+d+'d '+h+'h'):(h>0?('in '+h+'h '+m+'m'):('in '+m+'m'));}}
 function up(){{chips.forEach(function(c){{var t=rel(c.getAttribute('data-ko'));
  c.textContent=t; c.classList.toggle('live',t==='LIVE');}});}}
 up(); setInterval(up,1000);
}})();
(function(){{
 var f=document.querySelector('.pred-fresh[data-updated]'); if(!f) return;
 var w=f.querySelector('.pf-when'), u=new Date(f.getAttribute('data-updated')).getTime();
 var diff=Date.now()-u, h=Math.floor(diff/3600000), m=Math.floor(diff%3600000/60000);
 var ago=h>0?(h+'h '+m+'m ago'):(m+'m ago');
 if(w) w.textContent='Updated with latest team news '+ago;
}})();
</script></body></html>"""

AADS_UNIT = "2443595"  # A-ADS Banner Ad Unit(加密收款,匿名)
def ad():
    return (f'<div class="ad-slot"><iframe data-aa="{AADS_UNIT}" '
            f'src="//acceptable.a-ads.com/{AADS_UNIT}/?size=Adaptive" '
            f'style="border:0;padding:0;width:100%;height:auto;overflow:hidden;'
            f'display:block;margin:auto"></iframe></div>')

def accuracy_strip():
    if not META.get("played"): return ""
    return (f'<div class="acc-strip"><span>Model track record</span>'
            f'<span>Outcome called right <b>{META.get("outcome_acc","–")}%</b></span>'
            f'<span class="muted">over {META["played"]} matches · exact score {META.get("score_acc","–")}% (hardest call)</span>'
            f'<span class="upd">Updated {esc(META.get("updated_utc",""))}</span></div>')

def standings_table(g):
    st = g.get("standings") or []
    if not any(r["P"] for r in st): return ""
    rows = "".join(
        f'<tr><td class="pos">{i+1}</td><td class="tm">{esc(r["team"])}</td>'
        f'<td>{r["P"]}</td><td>{r["W"]}</td><td>{r["D"]}</td><td>{r["L"]}</td>'
        f'<td>{r["GF"]}:{r["GA"]}</td><td class="pts">{r["Pts"]}</td></tr>'
        for i,r in enumerate(st))
    return (f'<div class="sec-head"><span class="idx">#</span><h2 class="disp">Standings</h2><div class="line"></div></div>'
            f'<table class="standings"><thead><tr><th>#</th><th>Team</th><th>P</th><th>W</th><th>D</th><th>L</th><th>GF:GA</th><th>Pts</th></tr></thead><tbody>{rows}</tbody></table>')

def probs(m):
    p=P(m); w=p.get("win") or 0; d=p.get("draw") or 0; l=p.get("lose") or 0
    t=(w+d+l) or 1; return w/t*100, d/t*100, l/t*100

def result_badge(m):
    r = m.get("result")
    if not r or not r.get("played"): return ""
    p = P(m); ps = p.get("score","")
    pm = _re.match(r"(\d+)-(\d+)", ps or "")
    hit = ""
    if pm:
        po = "h" if int(pm.group(1))>int(pm.group(2)) else ("a" if int(pm.group(1))<int(pm.group(2)) else "d")
        ao = "h" if r["hs"]>r["as"] else ("a" if r["hs"]<r["as"] else "d")
        exact = int(pm.group(1))==r["hs"] and int(pm.group(2))==r["as"]
        hit = (f' <span class="hit ok">{icon("target")} exact</span>' if exact else
               f' <span class="hit ok">{icon("check")} called</span>' if po==ao else
               f' <span class="hit no">{icon("x")} missed</span>')
    return f'<span class="ft">FT {r["hs"]}–{r["as"]}{hit}</span>'

def verdict_badge(m, big=False):
    """醒目角标:预测对错的一眼判定。精准=EXACT(金),胜负对=CORRECT(绿),错=MISSED(红)。"""
    r = m.get("result")
    if not r or not r.get("played"): return ""
    p = P(m); pm = _re.match(r"(\d+)-(\d+)", p.get("score","") or "")
    if not pm: return ""
    ph, pa = int(pm.group(1)), int(pm.group(2))
    po = "h" if ph>pa else ("a" if ph<pa else "d")
    ao = "h" if r["hs"]>r["as"] else ("a" if r["hs"]<r["as"] else "d")
    sz = " big" if big else ""
    if ph==r["hs"] and pa==r["as"]:
        return f'<span class="verdict exact{sz}">{icon("target")}<span>Exact</span></span>'
    if po==ao:
        return f'<span class="verdict hit{sz}">{icon("check")}<span>Correct</span></span>'
    return f'<span class="verdict miss{sz}">{icon("x")}<span>Missed</span></span>'

def _pois(k, lam):
    return math.exp(-lam) * lam**k / math.factorial(k)

def scorelines(m, top=3):
    """Top-N most likely scorelines from a blended Poisson model derived from the headline
    pick + a baseline goal rate. Deterministic (no LLM), defensible, auto-updates per fixture."""
    p = P(m); pm = _re.match(r"(\d+)\s*-\s*(\d+)", p.get("score","") or "")
    if not pm: return []
    ph, pa = int(pm.group(1)), int(pm.group(2))
    avg = 1.30  # 联赛级基线进球,避免 2-0 推断出对手永不进球
    lh, la = max(0.25, 0.7*ph + 0.3*avg), max(0.25, 0.7*pa + 0.3*avg)
    grid = [(f"{h}-{a}", _pois(h,lh)*_pois(a,la)) for h in range(6) for a in range(6)]
    tot = sum(pr for _,pr in grid) or 1
    grid.sort(key=lambda x:-x[1])
    return [(s, round(pr/tot*100)) for s,pr in grid[:top]]

def scorelines_html(m):
    sl = scorelines(m)
    if not sl: return ""
    pick = (P(m).get("score","") or "").replace(" ","")
    rows = "".join(
        f'<div class="slrow{" pick" if s==pick else ""}"><span class="sls">{s}</span>'
        f'<span class="slbar"><i style="width:{pct}%"></i></span>'
        f'<span class="slp">{pct}%</span>'
        f'{" <span class=ourpick>our pick</span>" if s==pick else ""}</div>' for s,pct in sl)
    return (f'<div class="scorelines"><div class="lbl">Most likely scorelines '
            f'<span class="muted">· Poisson model</span></div>{rows}</div>')

def pred_fresh(m):
    """未踢比赛若已动态刷新过,显示"最近更新 + 开球锁定"。前端按 data-updated 渲染相对时间。"""
    if (m.get("result") or {}).get("played"):
        return ""
    u = (m.get("pred_en") or {}).get("updated_utc") or m.get("pred_updated_utc")
    if not u:
        return ""
    return (f'<div class="pred-fresh" data-updated="{u}">{icon("refresh")}'
            f'<span class="pf-when">Updated with latest team news</span>'
            f'<span class="pf-lock">· Locks at kickoff</span></div>')

def congrats(m):
    """已踢比赛:热烈恭喜获胜方并加油(平局则致敬双方)。"""
    r = m.get("result")
    if not r or not r.get("played"): return ""
    if r["hs"] == r["as"]:
        return (f'<div class="congrats draw">{icon("trophy")}<div>'
                f'<b>Honours even — {esc(m["home"])} {r["hs"]}–{r["as"]} {esc(m["away"])}.</b> '
                f'A point apiece and everything still to play for. Heads high, both sides!</div></div>')
    win = esc(m["home"]) if r["hs"] > r["as"] else esc(m["away"])
    return (f'<div class="congrats">{icon("trophy")}<div>'
            f'<b>Congratulations, {win}!</b> A {r["hs"]}–{r["as"]} result to savour — '
            f'the campaign rolls on. Keep it going, fans behind you all the way!</div></div>')

def hit_card(m):
    """已踢比赛的醒目命中/失手横幅(首页与详情页用)。命中是病毒传播钩子。"""
    r = m.get("result")
    if not r or not r.get("played"): return ""
    p = P(m); pm = _re.match(r"(\d+)-(\d+)", p.get("score","") or "")
    if not pm: return ""
    ph, pa = int(pm.group(1)), int(pm.group(2))
    exact = ph==r["hs"] and pa==r["as"]
    po = "h" if ph>pa else ("a" if ph<pa else "d")
    ao = "h" if r["hs"]>r["as"] else ("a" if r["hs"]<r["as"] else "d")
    fixture = f'{esc(m["home"])} {r["hs"]}–{r["as"]} {esc(m["away"])}'
    if exact:
        return (f'<div class="hitcard bull"><div class="bigtag">{icon("target")} BULLSEYE</div>'
                f'<div class="ht">Called it <b>{ph}–{pa}</b> — exact score.</div>'
                f'<div class="hs">{fixture} · nailed to the goal.</div></div>')
    if po==ao:
        side = esc(m["home"]) if po=="h" else (esc(m["away"]) if po=="a" else "the draw")
        return (f'<div class="hitcard win"><div class="bigtag">{icon("check")} CALLED IT</div>'
                f'<div class="ht">Right result — we tipped {side}.</div>'
                f'<div class="hs">Predicted {ph}–{pa} · final {fixture}.</div></div>')
    return (f'<div class="hitcard miss"><div class="bigtag">{icon("x")} MISSED</div>'
            f'<div class="ht">We tipped {ph}–{pa}, it finished {r["hs"]}–{r["as"]}.</div>'
            f'<div class="hs">{fixture} · post-match breakdown coming.</div></div>')

def card_time(m):
    """卡片右上角:已踢→FT比分;未踢→带倒计时的时间chip(前端按 kickoff 渲染 in 2d 4h / LIVE)。"""
    if (m.get("result") or {}).get("played"):
        return result_badge(m)
    ko = m.get("kickoff_utc", "")
    attr = f' data-ko="{ko}"' if ko else ""
    return f'<span class="ko-chip"{attr}>{fmt_date(m["date"])}</span>'

def match_card(m, rel=""):
    w,d,l = probs(m); p=P(m)
    return f"""<a class="mcard" href="{rel}{murl(m)}" data-reveal>{verdict_badge(m)}
<div class="top"><span class="grp">Group {m['group']} · Match {m.get('match_no','')}</span>{card_time(m)}</div>
<div class="fixture"><div class="t">{esc(m['home'])}</div><div class="sc">{esc(p.get('score','-'))}</div><div class="t away">{esc(m['away'])}</div></div>
<div class="bar"><i class="w" style="width:{w:.0f}%"></i><i class="d" style="width:{d:.0f}%"></i><i class="l" style="width:{l:.0f}%"></i></div>
<div class="barlbl"><span>1 {w:.0f}%</span><span>X {d:.0f}%</span><span>2 {l:.0f}%</span></div>
<div class="ana">{esc(p.get('analysis',''))}</div>
</a>"""

def results_section():
    """首页战绩区:已踢比赛的命中卡(最新在前),把精准命中亮出来当病毒钩子。"""
    played = [m for m in ALL if (m.get("result") or {}).get("played")]
    if not played: return ""
    played.sort(key=lambda m:(m["date"] or "", m.get("match_no") or 0), reverse=True)
    cards = "".join(hit_card(m) for m in played[:6])
    acc = (f' — outcome called right <b>{META.get("outcome_acc","–")}%</b>, '
           f'exact score <b>{META.get("score_acc","–")}%</b>') if META.get("played") else ""
    return (f'<section id="results"><div class="wrap">'
            f'<div class="sec-head"><span class="idx">★</span>'
            f'<h2 class="disp">Results So Far</h2><div class="line"></div></div>'
            f'<p class="results-sub">{META.get("played",0)} matches played{acc}.</p>'
            f'<div class="hitgrid">{cards}</div>'
            f'</div></section>')

_VMAP = {"exact": ("verdict exact", "Exact call"), "hit": ("verdict hit", "Correct"),
         "miss": ("verdict miss", "Missed")}

def blog_card(p, rel=""):
    vc, vl = _VMAP.get(p.get("verdict"), ("verdict hit", "Correct"))
    img = (f'<div class="bimg" style="background-image:url({rel}{p["image"]})"></div>'
           if p.get("image") else '')
    return (f'<a class="bcard" href="{rel}blog/{p["slug"]}.html" data-reveal>{img}'
            f'<div class="bbody"><div class="bmeta">'
            f'<span class="{vc}" style="position:static">{vl}</span>'
            f'<span>{fmt_date(p["date"])}</span></div>'
            f'<h3>{esc(p["title"])}</h3><p>{esc(p["dek"])}</p></div></a>')

def build_blog_index():
    posts = BLOG.get("posts", [])
    cards = "".join(blog_card(p, rel="../") for p in posts) or \
        '<p class="muted">Match reports are published after each game. Check back soon.</p>'
    title = "Blog — 2026 World Cup Match Reports & Prediction Reviews | OracleXI"
    desc = ("Honest match-by-match reviews of our 2026 World Cup AI predictions — where we "
            "called it and where we missed, with analysis of every result.")
    out = head(title, desc, rel="../", canon="blog/index.html") + f"""
<div class="wrap"><div class="crumb"><a href="../index.html">Home</a> / Blog</div></div>
<section class="detail-hero"><div class="wrap">
<div class="grp">OracleXI Journal</div>
<h1 class="disp" style="font-size:clamp(38px,7vw,72px);margin-top:8px">Match Reports</h1>
<p class="sub" style="margin-top:10px">Every game, reviewed. Where our model called it — and, honestly, where it missed.</p>
</div></section>
<div class="wrap">{ad()}<div class="blog-grid">{cards}</div>{ad()}</div>
""" + foot("../")
    open(os.path.join(DIST, "blog", "index.html"), "w", encoding="utf-8").write(out)

def build_blog_post(p):
    vc, vl = _VMAP.get(p.get("verdict"), ("verdict hit", "Correct"))
    body = "".join(f"<p>{esc(par)}</p>" for par in p.get("body", []))
    hero = (f'<div class="post-hero" style="background-image:url(../{p["image"]})"></div>'
            if p.get("image") else '')
    title = f'{esc(p["title"])} | OracleXI'
    desc = esc(p.get("dek", ""))[:155]
    cr_ld = crumbs_ld([("Home", "index.html"), ("Blog", "blog/index.html"),
                       (p["title"], f"blog/{p['slug']}.html")])
    art_ld = jsonld({"@context": "https://schema.org", "@type": "NewsArticle",
                     "headline": p["title"], "datePublished": p["date"],
                     **({"image": f"{BASE}/{p['image']}"} if p.get("image") else {}),
                     "author": {"@type": "Organization", "name": SITE},
                     "publisher": {"@type": "Organization", "name": SITE}})
    out = head(title, desc, rel="../", canon=f"blog/{p['slug']}.html", ld=cr_ld+art_ld,
               img=p.get("image", "")) + f"""
<div class="wrap"><div class="crumb"><a href="../index.html">Home</a> / <a href="../blog/index.html">Blog</a> / {esc(p['title'])}</div></div>
{hero}
<article class="wrap post">
<div class="bmeta"><span class="{vc}" style="position:static">{vl}</span><span>{fmt_date(p['date'])}</span>
<span>Predicted {esc(p['pred'])} · Final {esc(p['score'])}</span></div>
<h1 class="disp post-title">{esc(p['title'])}</h1>
<p class="dek">{esc(p['dek'])}</p>
{ad()}
<div class="post-body">{body}</div>
<a class="back" href="../blog/index.html">← All match reports</a>
{ad()}
</article>
""" + foot("../")
    open(os.path.join(DIST, "blog", f"{p['slug']}.html"), "w", encoding="utf-8").write(out)

def next_match():
    """下一场未踢的比赛(按日期/场次);没有则回退到最后一场。前端按 kickoff 显示倒计时/进行中。"""
    unplayed = [m for m in ALL if not (m.get("result") or {}).get("played")]
    return unplayed[0] if unplayed else ALL[-1]

def build_index():
    nm = next_match(); op = P(nm)
    ko = nm.get("kickoff_utc", "")
    upcoming = [m for m in ALL if not (m.get("result") or {}).get("played")][:12]
    groups_html=""
    for L in "ABCDEFGHIJKL":
        lis="".join(f'<li><span class="seed">{i+1}</span>{esc(t["en"])}</li>' for i,t in enumerate(DATA[L]["teams"]))
        groups_html+=f'<a class="gcard" href="group/{L}.html" data-reveal><div class="gh"><div class="gl">{L}</div><div class="gt">Group {L}</div></div><ul>{lis}</ul></a>'
    site_ld = jsonld({"@context":"https://schema.org","@graph":[
        {"@type":"WebSite","name":SITE,"url":f"{BASE}/","description":DESC},
        {"@type":"Organization","name":SITE,"url":f"{BASE}/","logo":f"{BASE}/favicon.svg"}]})
    out = head(f"{SITE} — 2026 World Cup AI Predictions for all 104 matches", DESC, canon="", ld=site_ld) + f"""
<section class="hero"><div class="wrap">
<div class="kicker"><span class="dot"></span><span class="next-label" data-kickoff="{ko}">Next match</span></div>
<h1 class="disp">2026 World Cup<br><em>AI Predictions</em></h1>
<p class="sub">The first 48-team World Cup. 104 matches. We run a data model on <b>every fixture</b> — score predictions, win probabilities and analysis. Know before kickoff.</p>
{accuracy_strip()}
<a class="opener" href="{murl(nm)}">
<div class="team"><div class="name">{esc(nm['home'])}</div><div class="meta">{esc(nm['venue'] or 'TBD')}</div></div>
<div><div class="vs">VS</div><div class="score">{esc(op.get('score','-'))}</div><div class="ko-pred">AI pick</div></div>
<div class="team"><div class="name">{esc(nm['away'])}</div><div class="meta">{fmt_date(nm['date'])}</div></div>
</a>
<div class="countdown" data-kickoff="{ko}"><span class="cd-label">Kicks off in</span><span class="cd-clock">—</span></div>
<div class="tag">FIFA 2026</div>
</div></section>
{results_section()}
<div class="wrap">{ad()}</div>
<section id="upcoming"><div class="wrap">
<div class="sec-head"><span class="idx">01</span><h2 class="disp">Upcoming Predictions</h2><div class="line"></div></div>
<div class="matches">{"".join(match_card(m) for m in upcoming)}</div>
</div></section>
<section id="groups"><div class="wrap">
<div class="sec-head"><span class="idx">02</span><h2 class="disp">Groups A–L</h2><div class="line"></div></div>
<div class="groups">{groups_html}</div>
</div></section>
<div class="wrap">{ad()}</div>
<section id="fixtures"><div class="wrap">
<div class="sec-head"><span class="idx">03</span><h2 class="disp">All Group Fixtures</h2><div class="line"></div></div>
<div class="matches">{"".join(match_card(m) for m in ALL)}</div>
</div></section>
""" + foot()
    open(os.path.join(DIST,"index.html"),"w",encoding="utf-8").write(out)

def build_group(L):
    g=DATA[L]
    teams_html="".join(f'<li><span class="seed">{i+1}</span><a href="../{turl(t["en"])}" style="color:inherit">{esc(t["en"])}</a></li>' for i,t in enumerate(g["teams"]))
    title=f"Group {L} — {', '.join(t['en'] for t in g['teams'])} | 2026 World Cup Predictions"
    desc=f"2026 World Cup Group {L}: {', '.join(t['en'] for t in g['teams'])}. All 6 fixtures with AI score predictions and win probabilities."
    out=head(title,desc,rel="../",canon=f"group/{L}.html")+f"""
<div class="wrap"><div class="crumb"><a href="../index.html">Home</a> / <a href="../index.html#groups">Groups</a> / Group {L}</div></div>
<section class="detail-hero"><div class="wrap">
<div class="grp">Group {L} · Group Stage</div>
<h1 class="disp" style="font-size:clamp(40px,8vw,80px);margin-top:8px">Group {L}</h1>
<div class="groups" style="margin-top:24px;grid-template-columns:1fr"><div class="gcard"><ul>{teams_html}</ul></div></div>
</div></section>
<div class="wrap">{ad()}</div>
<section><div class="wrap">
{standings_table(g)}
<div class="sec-head"><span class="idx">VS</span><h2 class="disp">Group {L} · 6 Predictions</h2><div class="line"></div></div>
<div class="matches">{"".join(match_card(m, rel="../") for m in g["matches"])}</div>
</div></section>
""" + foot("../")
    open(os.path.join(DIST,"group",f"{L}.html"),"w",encoding="utf-8").write(out)

def build_static(slug, title, body_html):
    out = head(f"{title} | {SITE}", f"{title} — OracleXI 2026 World Cup AI predictions.", canon=f"{slug}.html") + f"""
<div class="wrap"><div class="crumb"><a href="index.html">Home</a> / {esc(title)}</div></div>
<section><div class="wrap" style="max-width:760px">
<div class="sec-head"><span class="idx">i</span><h2 class="disp">{esc(title)}</h2><div class="line"></div></div>
<div class="analysis-box" style="border-left-color:var(--gold)">{body_html}</div>
</div></section>
""" + foot()
    open(os.path.join(DIST, f"{slug}.html"), "w", encoding="utf-8").write(out)

ABOUT_HTML = """<p>OracleXI provides data-driven AI predictions for every match of the 2026 FIFA World Cup — score forecasts, win/draw/loss probabilities and concise analysis for all 104 fixtures across the 12 groups.</p>
<p>Our predictions are produced by a language model that weighs public information such as recent form, FIFA rankings, head-to-head records and playing styles. Results pages update automatically as matches are played, and we track how accurate the model is over time.</p>
<p>OracleXI is an independent project for football fans and is not affiliated with FIFA. Predictions are for entertainment and informational purposes only and are not betting advice.</p>"""

PRIVACY_HTML = """<p><b>Last updated: June 2026.</b></p>
<p>This Privacy Policy explains how OracleXI ("we", "us") handles information when you visit oraclexi.com.</p>
<p><b>Information we collect.</b> We do not ask you to create an account or submit personal data. Standard server and analytics logs may record non-identifying technical data such as browser type, device and pages visited.</p>
<p><b>Cookies and advertising.</b> We may display ads served by third-party vendors, including Google. Third-party vendors, including Google, use cookies to serve ads based on your prior visits to this and other websites. Google's use of advertising cookies enables it and its partners to serve ads to you based on your visits to our site and/or other sites on the Internet. You may opt out of personalized advertising by visiting <a href="https://www.google.com/settings/ads" style="color:var(--lime)">Google Ads Settings</a>. You can also opt out of third-party vendor cookies at <a href="https://www.aboutads.info" style="color:var(--lime)">www.aboutads.info</a>.</p>
<p><b>Third-party links.</b> Our site may link to external sites whose privacy practices we do not control.</p>
<p><b>Children.</b> This site is not directed at children under 13.</p>
<p><b>Contact.</b> Questions about this policy can be sent via the channels listed on our About page.</p>"""

def build_team(team):
    name = team["en"]; L = TEAM_GROUP[name]
    fixtures = [m for m in DATA[L]["matches"] if name in (m["home"], m["away"])]
    title = f"{name} — 2026 World Cup Fixtures, Predictions & Group {L} Outlook"
    desc = f"{name} at the 2026 FIFA World Cup: Group {L} fixtures, AI score predictions and squad outlook. {(team.get('outlook') or '')[:90]}"
    out = head(title, desc, rel="../", canon=turl(name)) + f"""
<div class="wrap"><div class="crumb"><a href="../index.html">Home</a> / <a href="../group/{L}.html">Group {L}</a> / {esc(name)}</div></div>
<section class="detail-hero"><div class="wrap">
<div class="grp">2026 World Cup · Group {L}</div>
<h1 class="disp" style="font-size:clamp(34px,7vw,68px);margin-top:8px">{esc(name)}</h1>
</div></section>
<div class="wrap">{ad()}
<div class="analysis-box" style="border-left-color:var(--gold)"><div class="lbl">Team Outlook</div>{esc(team.get('outlook') or 'Outlook coming soon.')}</div>
</div>
<section><div class="wrap">
<div class="sec-head"><span class="idx">VS</span><h2 class="disp">{esc(name)} · Group Fixtures</h2><div class="line"></div></div>
<div class="matches">{"".join(match_card(m, rel="../") for m in fixtures)}</div>
</div></section>
""" + foot("../")
    open(os.path.join(DIST, "team", f"{tslug(name)}.html"), "w", encoding="utf-8").write(out)

def build_data_page():
    title="Free 2026 World Cup Dataset — Fixtures, Teams & AI Predictions (CSV + JSON)"
    desc="Download the complete 2026 FIFA World Cup dataset for free: all 48 teams and 72 group fixtures with AI score predictions, probabilities and analysis. CSV + JSON."
    out=head(title,desc,canon="data.html") + f"""
<div class="wrap"><div class="crumb"><a href="index.html">Home</a> / Free Dataset</div></div>
<section class="detail-hero"><div class="wrap">
<div class="grp">Free Download · CSV + JSON</div>
<h1 class="disp" style="font-size:clamp(34px,7vw,64px);margin-top:8px">2026 World Cup<br>Dataset <em style="color:var(--lime);font-style:normal">+ AI Predictions</em></h1>
<p class="sub">Every 2026 FIFA World Cup group fixture and all 48 teams — cleaned and ready to use, with AI score predictions, win probabilities, key players and analysis. Free for personal & commercial projects.</p>
<a class="opener" href="worldcup2026-dataset.zip" download style="grid-template-columns:1fr;text-align:center;text-decoration:none">
<div><div class="vs" style="color:var(--lime)">{icon("download")} DOWNLOAD</div><div class="meta" style="margin-top:6px">worldcup2026-dataset.zip · CSV + JSON + docs · 27 KB</div></div>
</a>
</div></section>
<div class="wrap">{ad()}
<div class="analysis-box"><div class="lbl">What's inside</div>
<b>fixtures_predictions.csv</b> — 72 group matches: date, venue, teams, predicted score, win/draw/loss probabilities, key player, analysis.<br>
<b>teams.csv</b> — all 48 teams with group, seeding and an AI squad outlook.<br>
<b>worldcup2026_full.json</b> — everything as clean nested JSON for apps & scripts.<br>
<b>README</b> — full data dictionary.</div>
<p style="color:var(--mute);font-size:14px">License: free for personal & commercial use in your own content/apps. Please don't resell the raw files. Predictions are AI-generated for information & entertainment only — not betting advice. Prefer the live data? Browse <a href="index.html" style="color:var(--lime)">all match predictions</a>.</p>
{ad()}
</div>
""" + foot()
    open(os.path.join(DIST,"data.html"),"w",encoding="utf-8").write(out)

_CA_V = ("toronto", "bmo", "vancouver", "bc place")
_MX_V = ("azteca", "monterrey", "guadalajara", "akron", "estadio")

def _venue_country(v):
    s = (v or "").lower()
    if any(k in s for k in _CA_V): return "CA"
    if any(k in s for k in _MX_V): return "MX"
    return "US"  # 2026 世界杯绝大多数场馆在美国

def event_ld(m):
    """SportsEvent 结构化数据(补全 Google 推荐字段:performer/organizer/description/endDate/image/address)。"""
    p = P(m); home, away = m["home"], m["away"]
    teams = [{"@type": "SportsTeam", "name": home}, {"@type": "SportsTeam", "name": away}]
    ev = {"@context": "https://schema.org", "@type": "SportsEvent",
          "name": f"{home} vs {away} — 2026 FIFA World Cup Group {m['group']}",
          "sport": "Soccer",
          "description": (f"2026 FIFA World Cup Group {m['group']} match: {home} vs {away}. "
                          f"AI prediction {p.get('score','-')} with win probabilities and analysis."),
          "url": f"{BASE}/{murl(m)}", "image": f"{BASE}/assets/og.jpg",
          "eventStatus": "https://schema.org/EventScheduled",
          "organizer": {"@type": "Organization", "name": "FIFA", "url": "https://www.fifa.com"},
          "performer": teams, "competitor": teams}
    start = m.get("kickoff_utc") or m.get("date")
    if start:
        ev["startDate"] = start
    ko = m.get("kickoff_utc")
    if ko:
        try:
            ev["endDate"] = (datetime.strptime(ko, "%Y-%m-%dT%H:%M:%SZ")
                             + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
        except Exception:
            pass
    venue = m.get("venue")
    if venue:                                            # 有场馆:完整 Place + 地址
        ev["location"] = {"@type": "Place", "name": venue,
                          "address": {"@type": "PostalAddress", "name": venue,
                                      "addressCountry": _venue_country(venue)}}
    else:                                                # 兜底:venue缺失也必有location,免Google报缺字段
        ev["location"] = {"@type": "Place", "name": "FIFA World Cup 2026 Stadium"}
    return jsonld(ev)

def star_name(p):
    s=(p.get("star") or "").strip()
    return s if len(s)>2 and not s.isdigit() else "—"   # 旧数据 star 存的是数字,挡掉

def pred_timeline(m):
    hist=m.get("pred_history") or []
    if not hist:
        return ""
    items=[]
    for h in reversed(hist):                             # 最新在上
        facts="".join(f"<li>{esc(x)}</li>" for x in (h.get("key_factors") or []))
        facts_html=f"<ul class='pf'>{facts}</ul>" if facts else ""
        conf=h.get("confidence") if h.get("confidence") in ("low","medium","high") else None
        conf_html=f"<span class='conf {conf}'>{conf} confidence</span>" if conf else ""
        reason=h.get("change_reason")
        reason_html=f"<div class='chg'>{esc(reason)}</div>" if reason else ""
        items.append(
            f"<div class='tl-item'><div class='tl-head'><span class='tl-date'>{esc(h.get('date',''))}</span>"
            f"<span class='tl-score'>{esc(h.get('score','-'))}</span>{conf_html}</div>"
            f"{reason_html}<p>{esc(h.get('analysis',''))}</p>{facts_html}</div>")
    return ("<div class='timeline'><div class='lbl'>Prediction Updates &amp; Analysis</div>"
            +"".join(items)+"</div>")

def team_recent(team, n=5):
    res=[]
    for L in "ABCDEFGHIJKL":
        for mm in DATA[L]["matches"]:
            r=mm.get("result") or {}
            if not r.get("played"): continue
            if mm["home"]==team: res.append((mm.get("date") or "", mm["away"], r["hs"], r["as"]))
            elif mm["away"]==team: res.append((mm.get("date") or "", mm["home"], r["as"], r["hs"]))
    res.sort(key=lambda x:x[0])
    return res[-n:]

def form_pills(team):
    rec=team_recent(team)
    if not rec:
        return '<span class="fp-none">Tournament opener</span>'
    out=[]
    for date,opp,gf,ga in rec:
        o="w" if gf>ga else ("d" if gf==ga else "l")
        out.append(f'<span class="fp {o}" title="vs {esc(opp)} {gf}-{ga}">{o.upper()}</span>')
    return "".join(out)

def match_extras(m):
    """详情页加厚:两队近况 + 小组积分榜 + 同组其他比赛卡 + 两队队页深链(治薄内容&内链死路)。"""
    L=m["group"]; home,away=m["home"],m["away"]
    related=[mm for mm in DATA[L]["matches"] if mm.get("match_no")!=m.get("match_no")]
    cards="".join(match_card(mm, rel="../") for mm in related)
    return f"""<div class="form-row">
<div class="form-team"><a href="../{turl(home)}" style="color:inherit"><b>{esc(home)}</b></a> · {form_pills(home)}</div>
<div class="form-team"><a href="../{turl(away)}" style="color:inherit"><b>{esc(away)}</b></a> · {form_pills(away)}</div>
</div>
{standings_table(DATA[L])}
<div class="sec-head"><span class="idx">VS</span><h2 class="disp">More Group {L} Predictions</h2><div class="line"></div></div>
<div class="matches">{cards}</div>
<div class="team-links"><a class="tl-btn" href="../{turl(home)}">{esc(home)} squad &amp; fixtures →</a><a class="tl-btn" href="../{turl(away)}">{esc(away)} squad &amp; fixtures →</a></div>"""

def build_match(m):
    p=P(m); w,d,l=probs(m)
    title=f"{m['home']} vs {m['away']} Prediction: {p.get('score','-')} | 2026 World Cup Group {m['group']}"
    desc=f"{m['home']} vs {m['away']} prediction (2026 World Cup, Group {m['group']}): AI tips {p.get('score','-')}. Win probabilities {w:.0f}%/{d:.0f}%/{l:.0f}%. {(p.get('analysis') or '')[:70]}"
    ev_ld=event_ld(m)
    cr_ld=crumbs_ld([("Home","index.html"),(f"Group {m['group']}",f"group/{m['group']}.html"),(f"{m['home']} vs {m['away']}",murl(m))])
    out=head(title,desc,rel="../",canon=murl(m),ld=ev_ld+cr_ld)+f"""
<div class="wrap"><div class="crumb"><a href="../index.html">Home</a> / <a href="../group/{m['group']}.html">Group {m['group']}</a> / {esc(m['home'])} vs {esc(m['away'])}</div></div>
<section class="detail-hero"><div class="wrap">
<div class="grp">Group {m['group']} · Match {m.get('match_no','')} · {fmt_date(m['date'])}</div>
<div class="vs-row"><div class="name"><a href="../{turl(m['home'])}" style="color:inherit">{esc(m['home'])}</a></div><div><div class="vs">VS</div><div class="pscore">{esc(p.get('score','-'))}</div>{verdict_badge(m, big=True)}</div><div class="name"><a href="../{turl(m['away'])}" style="color:inherit">{esc(m['away'])}</a></div></div>
<div class="meta-row"><span>{icon("pin")} <b>{esc(m['venue'] or 'TBD')}</b></span><span>{icon("star")} Watch: <b>{esc(star_name(p))}</b></span></div>
{pred_fresh(m)}
</div></section>
<div class="wrap">
{congrats(m)}
{hit_card(m)}
{ad()}
<div class="prob-big">
<div class="p win"><div class="v">{w:.0f}%</div><div class="k">{esc(m['home'])} win</div></div>
<div class="p draw"><div class="v">{d:.0f}%</div><div class="k">Draw</div></div>
<div class="p lose"><div class="v">{l:.0f}%</div><div class="k">{esc(m['away'])} win</div></div>
</div>
{scorelines_html(m)}
{pred_timeline(m) or f'<div class="analysis-box"><div class="lbl">AI Match Analysis</div>{esc(p.get("analysis") or "Analysis coming soon.")}</div>'}
{match_extras(m)}
<div class="disclaimer">{icon("alert")} Predictions are generated by an AI model from historical and public data, for entertainment and informational purposes only. Not betting advice.</div>
{ad()}
</div>
""" + foot("../")
    open(os.path.join(DIST,"match",f"{mslug(m)}.html"),"w",encoding="utf-8").write(out)

def main():
    if os.path.exists(DIST):
        for n in os.listdir(DIST):
            if n==".git": continue
            pth=os.path.join(DIST,n); shutil.rmtree(pth) if os.path.isdir(pth) else os.remove(pth)
    else: os.makedirs(DIST)
    os.makedirs(os.path.join(DIST,"group"),exist_ok=True)
    os.makedirs(os.path.join(DIST,"match"),exist_ok=True)
    os.makedirs(os.path.join(DIST,"team"),exist_ok=True)
    os.makedirs(os.path.join(DIST,"blog"),exist_ok=True)
    _assets=os.path.join(ROOT,"assets")  # 博客配图/OG分享图随站部署
    if os.path.isdir(_assets):
        shutil.copytree(_assets, os.path.join(DIST,"assets"), dirs_exist_ok=True)
    shutil.copy(os.path.join(ROOT,"static","style.css"),os.path.join(DIST,"style.css"))
    open(os.path.join(DIST,"favicon.svg"),"w").write('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="14" fill="#d4ff2e"/><text x="32" y="45" font-family="Arial Black,Arial" font-weight="900" font-size="26" fill="#0a0b0d" text-anchor="middle">XI</text></svg>')
    keyf = os.path.join(ROOT, ".indexnow_key")
    if os.path.exists(keyf):
        k = open(keyf).read().strip()
        open(os.path.join(DIST, f"{k}.txt"), "w").write(k)
    zipsrc=os.path.join(ROOT,"static","worldcup2026-dataset.zip")
    if os.path.exists(zipsrc): shutil.copy(zipsrc, os.path.join(DIST,"worldcup2026-dataset.zip"))
    build_index()
    build_data_page()
    build_static("about", "About OracleXI", ABOUT_HTML)
    build_static("privacy", "Privacy Policy", PRIVACY_HTML)
    for L in "ABCDEFGHIJKL": build_group(L)
    for m in ALL: build_match(m)
    ALL_TEAMS=[t for L in "ABCDEFGHIJKL" for t in DATA[L]["teams"]]
    for t in ALL_TEAMS: build_team(t)
    build_blog_index()
    for p in BLOG.get("posts", []): build_blog_post(p)
    urls=(["index.html","data.html","about.html","privacy.html","blog/index.html"]+[f"group/{L}.html" for L in "ABCDEFGHIJKL"]
          +[f"blog/{p['slug']}.html" for p in BLOG.get("posts",[])]
          +[turl(t["en"]) for t in ALL_TEAMS]+[murl(m) for m in ALL])
    for root,_,files in os.walk(DIST):               # 构建后统一清洗站内链接的 .html
        for fn in files:
            if fn.endswith(".html"):
                fp=os.path.join(root,fn)
                html=open(fp,encoding="utf-8").read()       # 必须先读后写,否则open(w)先截断成空
                open(fp,"w",encoding="utf-8").write(_clean_links(html))
    sm='<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    sm+="".join(f"<url><loc>{BASE}/{clean(u)}</loc><lastmod>{TODAY}</lastmod></url>\n" for u in urls)+"</urlset>"
    open(os.path.join(DIST,"sitemap.xml"),"w").write(sm)
    open(os.path.join(DIST,"robots.txt"),"w").write(f"User-agent: *\nAllow: /\nSitemap: {BASE}/sitemap.xml\n")
    if ADSENSE_PUB:
        pub = ADSENSE_PUB.replace("ca-", "")
        open(os.path.join(DIST,"ads.txt"),"w").write(f"google.com, {pub}, DIRECT, f08c47fec0942fa0\n")
    print(f"✅ Built {2+12+len(ALL)} pages (English){' + AdSense' if ADSENSE_PUB else ''}")

if __name__=="__main__":
    main()
