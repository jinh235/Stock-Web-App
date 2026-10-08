# -*- coding: utf-8 -*-
"""
미국 시장 히트맵(트리맵) 그리기 담당.

  - 타일 크기 = 시가총액, 색 = 전일 대비 등락률 (목업 범례와 같은 7단계 색)
  - 업종 상자 → 그 안의 종목 타일, 두 단계로 나눕니다.
  - 배치는 "squarify(정사각형에 가깝게 나누기)" 방식: 큰 값부터 줄을 채워 나가며
    타일 모양이 가늘고 길어지지 않도록 합니다.
  - 위치는 % 단위로 적어서 상자 크기가 조금 달라져도 그대로 맞습니다.
"""
import html

from config import HEATMAPS
from data import fetch_daily_changes, fetch_market_caps

# 히트맵 상자의 기준 크기(px). 글자 크기를 정할 때만 쓰고, 실제 배치는 % 단위입니다.
BOX_W, BOX_H = 880, 450
HEADER_H = 18          # 업종 이름 줄 높이
MINUS = "−"

# 목업 범례와 같은 색: −3% 이하 … 0 … +3% 이상 (한국식: 오르면 빨강)
COLOR_STEPS = [(-2.5, "#2f63c9"), (-1.5, "#2d4f8e"), (-0.5, "#334363"), (0.5, "#3b3f47"),
               (1.5, "#5f3b40"), (2.5, "#8e3a41")]
COLOR_TOP = "#c0343f"


def tile_color(pct):
    for limit, color in COLOR_STEPS:
        if pct < limit:
            return color
    return COLOR_TOP


def _pct_text(pct):
    sign = "+" if pct > 0.005 else (MINUS if pct < -0.005 else "")
    return f"{sign}{abs(pct):.2f}%"


# ------------------------------------------------------------------ 배치 계산 (squarify)
def _worst_ratio(row, side):
    """한 줄에 놓인 타일들 중 가장 길쭉한 것의 가로세로 비율 (1에 가까울수록 정사각형)."""
    total = sum(row)
    thickness = total / side
    return max(max(thickness / (v / thickness), (v / thickness) / thickness) for v in row)


def squarify(values, x, y, w, h):
    """values(큰 것부터 정렬된 넓이 목록)를 (x, y, w, h) 상자 안에 나눠 담은 사각형 목록을 돌려줍니다."""
    total = sum(values)
    if total <= 0 or w <= 0 or h <= 0:
        return [(x, y, 0, 0) for _ in values]
    areas = [v * w * h / total for v in values]   # 상자 넓이에 맞게 비율 조정
    rects = []
    while areas:
        side = min(w, h)                           # 짧은 변을 따라 한 줄씩 채움
        row = [areas.pop(0)]
        while areas and _worst_ratio(row + [areas[0]], side) <= _worst_ratio(row, side):
            row.append(areas.pop(0))
        thickness = sum(row) / side
        pos = 0
        for a in row:
            length = a / thickness
            if w >= h:     # 세로로 쌓는 줄 (왼쪽부터)
                rects.append((x, y + pos, thickness, length))
            else:          # 가로로 늘어놓는 줄 (위쪽부터)
                rects.append((x + pos, y, length, thickness))
            pos += length
        if w >= h:
            x, w = x + thickness, w - thickness
        else:
            y, h = y + thickness, h - thickness
    return rects


# ------------------------------------------------------------------ HTML 만들기
def _box(x, y, w, h, inner_style, content=""):
    """기준 크기(BOX_W×BOX_H) 좌표를 % 위치로 바꾼 상자 하나."""
    return (f'<div style="position: absolute; left: {x / BOX_W * 100:.3f}%; top: {y / BOX_H * 100:.3f}%; '
            f'width: {w / BOX_W * 100:.3f}%; height: {h / BOX_H * 100:.3f}%; {inner_style}">{content}</div>')


def _tile(ticker, cap, price, pct, x, y, w, h):
    gap = 1   # 타일 사이 틈 (양쪽 1px씩 = 2px)
    x, y, w, h = x + gap, y + gap, max(0, w - 2 * gap), max(0, h - 2 * gap)
    color = tile_color(pct)
    # 타일 크기에 맞춰 글자 크기 결정. 티커(굵은 글씨)는 글자당 약 0.75em, 등락률(고정폭 6~7자)은 약 0.6em 폭입니다.
    inner = w - 6
    font = min(26, h * 0.36, inner / (len(ticker) * 0.75))
    pfont = min(font * 0.62, inner / (6.5 * 0.6))
    text = ""
    if font >= 8 and h >= 12:
        text = f'<span class="tn" style="font-size: {font:.0f}px;">{ticker}</span>'
        if pfont >= 8.5 and h >= font * 1.25 + pfont + 4:
            text += f'<span class="tp" style="font-size: {pfont:.0f}px;">{_pct_text(pct)}</span>'
    tip = f"{ticker}  ${price:,.2f}  {_pct_text(pct)}  · 시가총액 ${cap / 1e9:,.0f}B"
    style = (f"background: {color}; display: flex; flex-direction: column; justify-content: center; align-items: center; "
             f"gap: 1px; overflow: hidden; color: #fff; text-align: center; border-radius: 2px; box-sizing: border-box;")
    return (f'<div title="{html.escape(tip)}" style="position: absolute; left: {x / BOX_W * 100:.3f}%; '
            f'top: {y / BOX_H * 100:.3f}%; width: {w / BOX_W * 100:.3f}%; height: {h / BOX_H * 100:.3f}%; {style}">'
            f'{text}</div>')


def _build_one(groups, changes, caps):
    """히트맵 하나(예: S&P 500)의 HTML. 자료가 있는 종목만 그립니다."""
    sectors = []
    for name, tickers in groups:
        items = [(t, caps[t], *changes[t]) for t in tickers if t in caps and t in changes]
        if items:
            items.sort(key=lambda it: it[1], reverse=True)
            sectors.append((name, items))
    if not sectors:
        return ""
    sectors.sort(key=lambda s: sum(it[1] for it in s[1]), reverse=True)

    parts = []
    sector_rects = squarify([sum(it[1] for it in items) for _, items in sectors], 0, 0, BOX_W, BOX_H)
    for (name, items), (sx, sy, sw, sh) in zip(sectors, sector_rects):
        total = sum(it[1] for it in items)
        avg = sum(it[1] * it[3] for it in items) / total          # 시가총액 가중 평균 등락률
        avg_color = "#f07178" if avg > 0.005 else ("#7fb0ff" if avg < -0.005 else "#a3a9b3")
        pad = 1.5   # 업종 상자 사이 틈
        bx, by, bw, bh = sx + pad, sy + pad, sw - 2 * pad, sh - 2 * pad
        show_header = bh > 60 and bw > 70
        header = ""
        if show_header:
            header = (f'<div style="height: {HEADER_H}px; padding: 0 6px; font-size: 11px; color: #a3a9b3; display: flex; '
                      f'align-items: center; justify-content: space-between; white-space: nowrap; overflow: hidden;">'
                      f'<span>{html.escape(name)}</span><span class="num" style="color: {avg_color};">{_pct_text(avg)}</span></div>')
        parts.append(_box(bx, by, bw, bh, "background: #14171c;", header))
        top = by + (HEADER_H if show_header else 0)
        tile_rects = squarify([it[1] for it in items], bx + 1, top, bw - 2, bh - (top - by) - 1)
        for (ticker, cap, price, pct), (tx, ty, tw, th) in zip(items, tile_rects):
            parts.append(_tile(ticker, cap, price, pct, tx, ty, tw, th))
    return "\n".join(parts)


def build_heatmaps():
    """(전환 버튼 HTML, 히트맵 HTML, 받아오지 못한 자료 이름 목록)을 돌려줍니다."""
    tickers = tuple(sorted({t for groups in HEATMAPS.values() for _, ts in groups for t in ts}))
    changes = fetch_daily_changes(tickers)
    caps = fetch_market_caps(tickers)

    tabs, maps, failed = [], [], []
    for key, groups in HEATMAPS.items():
        body = _build_one(groups, changes, caps)
        if not body:
            failed.append(f"{key} 히트맵")
            body = ('<div style="position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; '
                    'font-size: 13px; color: #a3a9b3;">시세를 받아오지 못했어요. 잠시 후 다시 시도됩니다.</div>')
        maps.append(f'<div class="hm" data-key="{html.escape(key)}" style="position: absolute; inset: 3px; display: none;">{body}</div>')
        tabs.append(f'<button class="hm-tab" data-key="{html.escape(key)}" style="height: 30px; padding: 0 14px; border: 0; '
                    f'border-radius: 7px; background: transparent; color: #a3a9b3; font-size: 13px; cursor: pointer;">'
                    f'{html.escape(key)}</button>')

    tabs_html = ('        <div style="display: flex; padding: 3px; gap: 2px; background: #0f1115; border-radius: 9px;">'
                 + "".join(tabs) + '</div>')
    map_html = ('    <div style="flex-grow: 1; min-height: 0; position: relative; background: #0b0d10; border-radius: 8px;">\n'
                + "\n".join(maps) + '\n    </div>')
    return tabs_html, map_html, failed
