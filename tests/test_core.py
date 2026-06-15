# -*- coding: utf-8 -*-
"""核心纯函数单测:URL 清洗、队名匹配、脏数据守卫、实质变化判定。
都是曾出过 bug(空队名崩溃、URL 残留 .html、star 显示数字)的地方。"""
import build
import refresh_predictions as rp
import scout


# ---------- URL 干净化(对齐 Cloudflare) ----------
def test_clean_strips_html():
    assert build.clean("") == ""
    assert build.clean("index.html") == ""
    assert build.clean("about.html") == "about"
    assert build.clean("blog/index.html") == "blog/"
    assert build.clean("match/b51.html") == "match/b51"
    assert build.clean("group/A") == "group/A"        # 已干净不变


def test_clean_links_internal_only():
    assert build._clean_links('<a href="about.html">') == '<a href="about">'
    assert build._clean_links('<a href="../index.html">') == '<a href="../">'
    assert build._clean_links('<a href="blog/index.html">') == '<a href="blog/">'
    assert build._clean_links('<a href="x.html#groups">') == '<a href="x#groups">'
    # 外链 / 资源不动
    assert build._clean_links('<a href="https://x.com/a.html">') == '<a href="https://x.com/a.html">'
    assert build._clean_links('<a href="style.css">') == '<a href="style.css">'


# ---------- 脏数据守卫:star 曾是数字 ----------
def test_star_name_guards_numbers():
    assert build.star_name({"star": "Lionel Messi"}) == "Lionel Messi"
    assert build.star_name({"star": "3"}) == "—"
    assert build.star_name({"star": ""}) == "—"
    assert build.star_name({}) == "—"
    assert build.star_name({"star": "AB"}) == "—"        # 太短当脏数据


# ---------- 队名匹配:曾因空名 IndexError 崩溃 ----------
def test_same_team_empty_guard():
    assert scout._same_team("", "Brazil") is False        # 这条曾触发 ''.split()[0] 崩溃
    assert scout._same_team("Brazil", "") is False


def test_same_team_variants():
    assert scout._same_team("Brazil", "Brazil") is True
    assert scout._same_team("Czechia", "Czech Republic") is True
    assert scout._same_team("South Korea", "Korea Republic") is True
    assert scout._same_team("Spain", "Portugal") is False


# ---------- 实质变化判定(决定是否落库+追加历史) ----------
def test_is_material():
    base = {"score": "1-0", "win": 0.5, "draw": 0.3, "lose": 0.2}
    assert rp.is_material({}, base) is True                       # 无旧预测=首次
    assert rp.is_material(dict(base), dict(base)) is False        # 完全相同
    assert rp.is_material(base, {**base, "score": "2-0"}) is True  # 比分变
    assert rp.is_material(base, {**base, "win": 0.6}) is True      # 概率变≥0.07(0.5→0.6)
    assert rp.is_material(base, {**base, "win": 0.52}) is False    # 概率变<0.07
