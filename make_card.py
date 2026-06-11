#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""分享卡生成器：从 groups.json 读取某场比赛，叠加 AI 预测，输出竖版社媒卡。
用法: python3 make_card.py A 1 [bg.jpg]"""
import sys, os, json
from PIL import Image, ImageDraw, ImageFont

ROOT=os.path.dirname(os.path.abspath(__file__))
DATA=json.load(open(os.path.join(ROOT,"data","groups.json"),encoding="utf-8"))
HEITI="/System/Library/Fonts/STHeiti Medium.ttc"
LIME=(212,255,46); CORAL=(255,77,46); INK=(244,242,236); MUTE=(154,162,173); BG=(10,11,13); GOLD=(229,180,91)
W,H=1080,1350

def F(sz): return ImageFont.truetype(HEITI,sz)

def find(group, idx):
    """idx = 组内第几场 (1-6)"""
    ms=DATA[group]["matches"]
    if 1<=idx<=len(ms): return ms[idx-1]
    raise SystemExit(f"未找到 {group} 第{idx}场")

def make(group, no, bg_path):
    m=find(group,int(no)); p=m.get("pred",{})
    card=Image.new("RGB",(W,H),BG)
    bg=Image.open(bg_path).convert("RGB")
    bgr=bg.resize((W,int(W*bg.height/bg.width)))
    card.paste(bgr.crop((0,0,W,760)),(0,0))
    # 渐变压暗
    grad=Image.new("L",(1,H),0)
    for y in range(H):
        grad.putpixel((0,y), 0 if y<480 else (int(255*(y-480)/280) if y<760 else 255))
    card=Image.composite(Image.new("RGB",(W,H),BG),card,grad.resize((W,H)))
    m2=Image.new("L",(W,H),0); ImageDraw.Draw(m2).rectangle([0,0,W,200],fill=90)
    card=Image.composite(Image.new("RGB",(W,H),BG),card,m2)
    d=ImageDraw.Draw(card)
    def ctr(txt,y,font,fill):
        w=d.textbbox((0,0),txt,font=font)[2]; d.text(((W-w)/2,y),txt,font=font,fill=fill)
    # 日期标签
    md=m["date"][5:].replace("-","月")+"日" if m["date"] else ""
    ctr(f"● 2026世界杯 {m['group']}组 · {md}",70,F(34),CORAL)
    # 对阵（长名自动缩字号）
    vs=f"{m['home_zh']}  VS  {m['away_zh']}"
    fs=74
    while d.textbbox((0,0),vs,font=F(fs))[2] > W-80 and fs>40: fs-=4
    ctr(vs,560,F(fs),INK)
    ctr("AI 预测比分",840,F(38),MUTE)
    ctr(p.get("score","-"),905,F(150),LIME)
    w,dr,l=p.get("win",0)*100,p.get("draw",0)*100,p.get("lose",0)*100
    ctr(f"{m['home_zh']}胜 {w:.0f}%   平 {dr:.0f}%   {m['away_zh']}胜 {l:.0f}%",1110,F(32),INK)
    star=p.get("star","")
    if star: ctr(f"看点：{star}"[:22],1170,F(30),GOLD)
    d.rectangle([0,1270,W,H],fill=LIME)
    ctr("全部72场AI预测 → kingshuaishuai.github.io/wc26",1295,F(34),BG)
    out=os.path.join(ROOT,"assets",f"card_{group}{no}.jpg")
    card.save(out,quality=90)
    return out

if __name__=="__main__":
    g,n=sys.argv[1],sys.argv[2]
    bg=sys.argv[3] if len(sys.argv)>3 else os.path.join(ROOT,"assets","opener_bg.jpg")
    print(make(g,n,bg))
