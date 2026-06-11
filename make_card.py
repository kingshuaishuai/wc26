#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""English share-card generator: reads a fixture from groups.json, overlays the AI
prediction, outputs a vertical social card for Pinterest/IG/X.
Usage: python3 make_card.py A 1 [bg.jpg]   (A = group, 1 = nth fixture in group)"""
import sys, os, json
from PIL import Image, ImageDraw, ImageFont
from datetime import date

ROOT=os.path.dirname(os.path.abspath(__file__))
DATA=json.load(open(os.path.join(ROOT,"data","groups.json"),encoding="utf-8"))
# Latin fonts (Anton-like). Fall back to a bundled system font.
def font_path(*cands):
    for c in cands:
        if os.path.exists(c): return c
    return cands[-1]
BOLD = font_path("/System/Library/Fonts/Supplemental/Arial Bold.ttf","/Library/Fonts/Arial Bold.ttf","/System/Library/Fonts/Helvetica.ttc")
BLACK = font_path("/System/Library/Fonts/Supplemental/Arial Black.ttf","/System/Library/Fonts/Supplemental/Arial Bold.ttf","/System/Library/Fonts/Helvetica.ttc")
LIME=(212,255,46); CORAL=(255,77,46); INK=(244,242,236); MUTE=(154,162,173); BG=(10,11,13); GOLD=(229,180,91)
W,H=1080,1350
MON=["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]

def F(p,sz): return ImageFont.truetype(p,sz)

def find(group, idx):
    ms=DATA[group]["matches"]
    if 1<=idx<=len(ms): return ms[idx-1]
    raise SystemExit(f"not found {group} #{idx}")

def make(group, no, bg_path):
    m=find(group,int(no)); p=m.get("pred_en",{})
    card=Image.new("RGB",(W,H),BG)
    bg=Image.open(bg_path).convert("RGB")
    bgr=bg.resize((W,int(W*bg.height/bg.width)))
    card.paste(bgr.crop((0,0,W,760)),(0,0))
    grad=Image.new("L",(1,H),0)
    for y in range(H):
        grad.putpixel((0,y), 0 if y<480 else (int(255*(y-480)/280) if y<760 else 255))
    card=Image.composite(Image.new("RGB",(W,H),BG),card,grad.resize((W,H)))
    m2=Image.new("L",(W,H),0); ImageDraw.Draw(m2).rectangle([0,0,W,200],fill=90)
    card=Image.composite(Image.new("RGB",(W,H),BG),card,m2)
    d=ImageDraw.Draw(card)
    def ctr(txt,y,font,fill):
        w=d.textbbox((0,0),txt,font=font)[2]; d.text(((W-w)/2,y),txt,font=font,fill=fill)
    # date label
    md=""
    if m.get("date"):
        y,mo,dd=map(int,m["date"].split("-")); md=f"{MON[mo-1]} {dd}"
    ctr(f"2026 WORLD CUP   ·   GROUP {m['group']}   ·   {md}",78,F(BOLD,30),CORAL)
    # fixture (auto-shrink for long names)
    vs=f"{m['home']}  v  {m['away']}"
    fs=70
    while d.textbbox((0,0),vs,font=F(BLACK,fs))[2] > W-70 and fs>34: fs-=3
    ctr(vs,560,F(BLACK,fs),INK)
    ctr("AI PREDICTED SCORE",838,F(BOLD,34),MUTE)
    ctr(p.get("score","-"),892,F(BLACK,150),LIME)
    w=round((p.get("win") or 0)*100); dr=round((p.get("draw") or 0)*100); l=round((p.get("lose") or 0)*100)
    ctr(f"{m['home']} {w}%    Draw {dr}%    {m['away']} {l}%",1112,F(BOLD,30),INK)
    star=p.get("star","")
    if star: ctr(f"Key player: {star}"[:40],1168,F(BOLD,28),GOLD)
    d.rectangle([0,1272,W,H],fill=LIME)
    ctr("All 104 AI predictions  ·  oraclexi.com",1296,F(BLACK,34),BG)
    out=os.path.join(ROOT,"assets",f"card_{group}{no}.jpg")
    card.save(out,quality=90)
    return out

if __name__=="__main__":
    g,n=sys.argv[1],sys.argv[2]
    bg=sys.argv[3] if len(sys.argv)>3 else os.path.join(ROOT,"assets","opener_bg.jpg")
    print(make(g,n,bg))
