#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 OracleXI 品牌头像(精确复刻站点 logo:深底 + 柠檬绿斜切"XI"标 + ORACLEXI 字标)。
PIL 确定性渲染,保证字母正确、小尺寸清晰、与站点视觉一致。输出 assets/avatar.png(1024方图)。"""
import os

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.abspath(__file__))
S = 1024
BG = (10, 11, 13)
LIME = (212, 255, 46)
INK = (10, 11, 13)
WHITE = (244, 242, 236)


def font_path(*cands):
    for c in cands:
        if os.path.exists(c):
            return c
    return cands[-1]


BLACK = font_path("/System/Library/Fonts/Supplemental/Arial Black.ttf",
                  "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
                  "/System/Library/Fonts/Helvetica.ttc")


def F(sz):
    return ImageFont.truetype(BLACK, sz)


def ctr(d, txt, cx, y, font, fill, spacing=0):
    if spacing:
        txt = (" " * 0).join(txt)  # 占位,真正字距下面手动
    w = d.textbbox((0, 0), txt, font=font)[2]
    d.text((cx - w / 2, y), txt, font=font, fill=fill)


def ctr_spaced(d, txt, cx, y, font, fill, gap):
    # 带字距居中
    widths = [d.textbbox((0, 0), ch, font=font)[2] for ch in txt]
    total = sum(widths) + gap * (len(txt) - 1)
    x = cx - total / 2
    for ch, w in zip(txt, widths):
        d.text((x, y), ch, font=font, fill=fill)
        x += w + gap


def make_banner():
    """X 头图 1500×500:左 XI 标 + 右品牌字与网址,内容居中带避开左下角(头像遮挡区)。"""
    W, H = 1500, 500
    img = Image.new("RGB", (W, H), BG)
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for r, a in ((460, 28), (320, 34), (210, 40)):
        gd.ellipse([W*0.5-r, H/2-r, W*0.5+r, H/2+r], fill=(212, 255, 46, a))
    glow = glow.filter(ImageFilter.GaussianBlur(150))
    img = Image.alpha_composite(img.convert("RGBA"), glow).convert("RGB")

    mk = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    md = ImageDraw.Draw(mk)
    bw, bh = 290, 188
    bx, by = 430, (H - bh) / 2
    md.rounded_rectangle([bx, by, bx + bw, by + bh], radius=30, fill=LIME)
    xf = F(150)
    tb = md.textbbox((0, 0), "XI", font=xf)
    md.text((bx + (bw-(tb[2]-tb[0]))/2 - tb[0], by + (bh-(tb[3]-tb[1]))/2 - tb[1]), "XI", font=xf, fill=INK)
    mk = mk.transform((W, H), Image.AFFINE, (1, -0.12, 0.12*(by+bh/2), 0, 1, 0), resample=Image.BICUBIC)
    img = Image.alpha_composite(img.convert("RGBA"), mk).convert("RGB")
    d = ImageDraw.Draw(img)

    tx = bx + bw + 56
    d.text((tx, 150), "ORACLEXI", font=F(86), fill=WHITE)
    ctr_left = tx
    # 字距小标
    x = ctr_left
    for ch in "AI WORLD CUP PREDICTIONS":
        d.text((x, 258), ch, font=F(28), fill=LIME)
        x += d.textbbox((0, 0), ch, font=F(28))[2] + 3
    d.text((ctr_left, 300), "oraclexi.com", font=F(40), fill=WHITE)
    img.save(os.path.join(ROOT, "assets", "x_banner.png"))


def main():
    img = Image.new("RGB", (S, S), BG)
    d = ImageDraw.Draw(img)

    # 柔和的绿色光晕(径向感,简化为几层透明椭圆)
    glow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for r, a in ((520, 30), (400, 34), (300, 40)):
        gd.ellipse([S/2-r, S/2-r-40, S/2+r, S/2+r-40], fill=(212, 255, 46, a))
    glow = glow.filter(ImageFilter.GaussianBlur(120))
    img = Image.alpha_composite(img.convert("RGBA"), glow).convert("RGB")
    d = ImageDraw.Draw(img)

    # "XI" 斜切标:画在子层 → 水平错切 → 贴回(复刻 skewX(-7deg))
    mark = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    md = ImageDraw.Draw(mark)
    bw, bh = 560, 360
    bx, by = (S - bw) / 2, (S - bh) / 2 - 70
    md.rounded_rectangle([bx, by, bx + bw, by + bh], radius=46, fill=LIME)
    xf = F(300)
    tw = md.textbbox((0, 0), "XI", font=xf)
    md.text(((S - (tw[2] - tw[0])) / 2 - tw[0], by + (bh - (tw[3] - tw[1])) / 2 - tw[1]),
            "XI", font=xf, fill=INK)
    s = 0.12
    mark = mark.transform((S, S), Image.AFFINE, (1, -s, s * (by + bh / 2), 0, 1, 0), resample=Image.BICUBIC)
    img = Image.alpha_composite(img.convert("RGBA"), mark).convert("RGB")
    d = ImageDraw.Draw(img)

    # ORACLEXI 字标
    ctr_spaced(d, "ORACLEXI", S / 2, by + bh + 70, F(86), WHITE, 6)
    # 底部小标语
    ctr_spaced(d, "AI WORLD CUP PREDICTIONS", S / 2, by + bh + 180, F(30), LIME, 4)

    out = os.path.join(ROOT, "assets", "avatar.png")
    img.save(out)
    img.resize((400, 400), Image.LANCZOS).save(os.path.join(ROOT, "assets", "avatar_400.png"))

    # 圆形头像专用:大号 XI 标居中、无文字(圆裁不丢内容)
    ico = Image.new("RGB", (S, S), BG)
    g2 = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    g2d = ImageDraw.Draw(g2)
    for r, a in ((560, 34), (420, 40), (300, 46)):
        g2d.ellipse([S/2-r, S/2-r, S/2+r, S/2+r], fill=(212, 255, 46, a))
    ico = Image.alpha_composite(ico.convert("RGBA"), g2.filter(ImageFilter.GaussianBlur(120))).convert("RGB")
    mk = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    mkd = ImageDraw.Draw(mk)
    bw2, bh2 = 660, 430
    bx2, by2 = (S - bw2) / 2, (S - bh2) / 2
    mkd.rounded_rectangle([bx2, by2, bx2 + bw2, by2 + bh2], radius=56, fill=LIME)
    xf2 = F(360)
    tb = mkd.textbbox((0, 0), "XI", font=xf2)
    mkd.text(((S - (tb[2]-tb[0]))/2 - tb[0], by2 + (bh2-(tb[3]-tb[1]))/2 - tb[1]), "XI", font=xf2, fill=INK)
    mk = mk.transform((S, S), Image.AFFINE, (1, -0.12, 0.12 * (S/2), 0, 1, 0), resample=Image.BICUBIC)
    ico = Image.alpha_composite(ico.convert("RGBA"), mk).convert("RGB")
    icp = os.path.join(ROOT, "assets", "avatar_icon.png")
    ico.save(icp)
    ico.resize((400, 400), Image.LANCZOS).save(os.path.join(ROOT, "assets", "avatar_icon_400.png"))
    make_banner()
    print(out + "\n" + icp + "\n" + os.path.join(ROOT, "assets", "x_banner.png"))


if __name__ == "__main__":
    main()
