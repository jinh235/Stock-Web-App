# -*- coding: utf-8 -*-
"""
목업 HTML(templates/dashboard.html)의 빈칸({{이름}})을 실제 숫자로 채우는 담당.

목업에서 숫자가 들어가던 자리는 {{INDEX_CARDS}}, {{MACRO_ROWS}} 같은 표시로 바꿔 두었고,
여기서 목업과 똑같은 모양의 HTML 조각을 만들어 그 자리에 끼워 넣습니다.
"""
import html
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from config import INDEX_CARDS, MACRO_ITEMS
from data import fetch_ecos, fetch_fred, fetch_price_history, fetch_price_series, fetch_watch_quote
from heatmap import build_heatmaps
from sheets import load_watchlist

TEMPLATE_PATH = Path(__file__).resolve().parent / "templates" / "dashboard.html"
KST = ZoneInfo("Asia/Seoul")
NEW_YORK = ZoneInfo("America/New_York")

# 목업의 색: 오르면 빨강, 내리면 파랑 (한국식)
UP, DOWN, FLAT, MUTED = "#f07178", "#7fb0ff", "#ecebe6", "#a3a9b3"
MINUS = "−"   # 목업에서 쓰는 긴 빼기 기호(−)


def _color(diff):
    if diff is None or abs(diff) < 1e-12:
        return FLAT
    return UP if diff > 0 else DOWN


def _quote_texts(ticker, kind, scale):
    """한 종목의 (값 글자, 변화 글자, 색, 날짜 목록, 값 목록)을 만듭니다. 자료가 없으면 목록은 None."""
    series = fetch_price_series(ticker)
    if not series:
        return "—", "자료 없음", MUTED, None, None
    dates, values = series[0], [v * scale for v in series[1]]
    last, prev = values[-1], values[-2]
    diff = last - prev
    color = _color(diff)
    arrow = "▲" if diff > 0 else ("▼" if diff < 0 else "")
    if kind == "yield":   # 금리는 %, 변화는 %p
        return f"{last:.2f}%", f"{arrow} {abs(diff):.2f}%p".strip(), color, dates, values
    pct = diff / prev * 100 if prev else 0
    sign = "+" if pct > 0 else (MINUS if pct < 0 else "")
    if kind == "usd":
        value_text, diff_text = f"${last:,.0f}", f"{abs(diff):,.0f}"
    else:
        value_text = f"{last:,.2f}"
        diff_text = f"{abs(diff):,.2f}" if abs(diff) < 100 else f"{abs(diff):,.1f}"  # 목업처럼 114.6
    return value_text, f"{arrow} {diff_text} {sign}{abs(pct):.2f}%".strip(), color, dates, values


CHART_W, CHART_H = 300, 72   # 카드 그래프의 기준 크기 (실제로는 카드 폭에 맞춰 늘어남)


def _card_chart(dates, values, color, kind):
    """카드 아래쪽의 큰 선 그래프. 마우스를 올리면 그날 날짜와 값이 보입니다 (dashboard.html의 스크립트가 처리)."""
    lo, hi = min(values), max(values)
    span = (hi - lo) or 1
    step = CHART_W / (len(values) - 1)
    pts = [(i * step, CHART_H - 6 - (v - lo) / span * (CHART_H - 12)) for i, v in enumerate(values)]
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    area = f"0,{CHART_H} {line} {CHART_W},{CHART_H}"          # 선 아래를 옅게 칠하는 영역
    data = html.escape(json.dumps({"d": dates, "v": [round(v, 4) for v in values], "k": kind}))
    return (f'<div class="chart" data-series="{data}" style="position: relative; height: {CHART_H}px; cursor: crosshair;">'
            f'<svg width="100%" height="{CHART_H}" viewBox="0 0 {CHART_W} {CHART_H}" preserveAspectRatio="none" aria-hidden="true">'
            f'<polygon points="{area}" fill="{color}" opacity="0.10"/>'
            f'<polyline points="{line}" fill="none" stroke="{color}" stroke-width="2" vector-effect="non-scaling-stroke"/></svg>'
            f'<div class="hl" style="display: none; position: absolute; top: 0; bottom: 0; width: 1px; background: #5a606b;"></div>'
            f'<div class="dot" style="display: none; position: absolute; width: 8px; height: 8px; margin: -4px 0 0 -4px; '
            f'border-radius: 50%; background: {color}; border: 2px solid #181b21; box-sizing: content-box;"></div>'
            f'<div class="tip num" style="display: none; position: absolute; top: 0; padding: 3px 8px; border-radius: 6px; '
            f'background: #2a2f38; border: 1px solid #3a404b; font-size: 12px; white-space: nowrap; pointer-events: none;"></div>'
            f'</div>')


def _index_card(name, ticker, kind, scale):
    """맨 위 큰 지수 카드 하나: 윗줄에 이름·값·변화, 아래에 최근 1개월 그래프."""
    value_text, change_text, color, dates, values = _quote_texts(ticker, kind, scale)
    chart_color = color if color != FLAT else MUTED
    chart = (_card_chart(dates, values, chart_color, kind) if values
             else f'<div style="height: {CHART_H}px;"></div>')
    return f'''  <div class="card" style="padding: 14px 18px 12px; display: flex; flex-direction: column; gap: 10px;">
    <div style="display: flex; align-items: baseline; gap: 8px; white-space: nowrap; min-width: 0;">
      <span style="font-size: 13px; color: #a3a9b3;">{html.escape(name)}</span>
      <span class="num" style="font-size: 20px; font-weight: 600;">{value_text}</span>
      <span class="num" style="font-size: 12px; color: {color}; margin-left: auto; min-width: 0; overflow: hidden; text-overflow: ellipsis;">{change_text}</span>
    </div>
    {chart}
  </div>'''


def _macro_values(source, code, kind):
    """거시지표 하나의 (최근 값, 이전 값, 기준 글자)를 돌려줍니다. 실패하면 None."""
    if source == "yahoo":
        values = fetch_price_history(code, period="5d")
        return (values[-1], values[-2], "실시간") if values else None

    rows = fetch_fred(code) if source == "fred" else fetch_ecos(code)
    if not rows:
        return None

    if kind == "yoy":   # 월별 물가지수 → 전년 같은 달 대비 상승률
        if len(rows) < 14:
            return None
        latest = (rows[-1][1] / rows[-13][1] - 1) * 100
        previous = (rows[-2][1] / rows[-14][1] - 1) * 100
        return latest, previous, rows[-1][0].strftime("%y.%m")

    # 금리처럼 가끔 바뀌는 값: 일별 자료면 '마지막으로 바뀐 날'과 '바뀌기 전 값'을 보여줍니다.
    last_date, latest = rows[-1]
    gaps = [(b[0] - a[0]).days for a, b in zip(rows[-6:], rows[-5:])]
    if gaps and max(gaps) <= 7:          # 일별 자료 (미국 기준금리, 한국 기준금리)
        for i in range(len(rows) - 1, 0, -1):
            if rows[i - 1][1] != latest:
                return latest, rows[i - 1][1], rows[i][0].strftime("%m/%d")
        return latest, latest, rows[0][0].strftime("%m/%d")
    return latest, rows[-2][1], last_date.strftime("%y.%m")   # 월별 자료 (실업률)


def _macro_row(name, source, code, kind, is_last):
    result = _macro_values(source, code, kind)
    border = "" if is_last else " border-bottom: 1px solid #20242b;"
    if result is None:
        latest_text, prev_text, when, color = "—", "—", "—", MUTED
    else:
        latest, prev, when = result
        color = _color(latest - prev)
        if kind in ("yoy", "rate"):
            latest_text, prev_text = f"{latest:.2f}%", f"{prev:.2f}%"
            if kind == "yoy":
                latest_text, prev_text = f"{latest:.1f}%", f"{prev:.1f}%"
        else:
            latest_text, prev_text = f"{latest:,.2f}", f"{prev:,.2f}"
    return (f'      <div style="display: grid; grid-template-columns: 1.6fr 0.9fr 0.9fr 0.8fr; gap: 8px; '
            f'align-items: center; height: 34px; font-size: 13px;{border}">'
            f'<span>{html.escape(name)}</span>'
            f'<span class="num" style="text-align: right; color: {color};">{latest_text}</span>'
            f'<span class="num" style="text-align: right; color: #a3a9b3;">{prev_text}</span>'
            f'<span class="num" style="text-align: right; color: #a3a9b3;">{when}</span></div>'), result is None


WATCH_GRID = "display: grid; grid-template-columns: 1.5fr 1.1fr 0.9fr 1fr; gap: 8px; align-items: center;"


def _watch_add_button(sheet_url):
    """'+ 종목 추가' 버튼. 시트 주소가 있으면 누를 때 구글 시트가 새 탭으로 열립니다."""
    style = ("height: 32px; padding: 0 12px; border-radius: 8px; border: 1px solid #2c313a; "
             "background: transparent; color: #ecebe6; font-size: 13px;")
    if not sheet_url:
        return f'<button style="{style}">+ 종목 추가</button>'
    return (f'<a href="{html.escape(sheet_url)}" target="_blank" rel="noopener" title="구글 시트에서 종목 추가·삭제" '
            f'style="{style} display: inline-flex; align-items: center; box-sizing: border-box; text-decoration: none;">'
            f'+ 종목 추가</a>')


def _watch_row(item, is_last):
    border = "" if is_last else " border-bottom: 1px solid #20242b;"
    quote = fetch_watch_quote(item["code"], item["market"])
    if quote is None:
        price_text, pct_text, color, dot = "—", "—", MUTED, ""
    else:
        last, prev = quote["last"], quote["prev"]
        pct = (last - prev) / prev * 100 if prev else 0
        color = _color(last - prev)
        sign = "+" if pct > 0 else (MINUS if pct < 0 else "")
        pct_text = f"{sign}{abs(pct):.2f}%"
        price_text = f"{last:,.0f}" if item["market"] == "KR" else f"${last:,.2f}"
        span = quote["high52"] - quote["low52"]
        pos = (last - quote["low52"]) / span * 100 if span else 50
        pos = max(0, min(100, pos))
        # 점이 막대 밖으로 나가지 않도록 (점 너비 10px) 위치를 살짝 보정합니다.
        dot = (f'<span title="52주 최저 {quote["low52"]:,.2f} · 최고 {quote["high52"]:,.2f}" '
               f'style="position: absolute; left: calc({pos:.0f}% - {pos / 10:.1f}px); top: -3px; '
               f'width: 10px; height: 10px; border-radius: 50%; background: #ecebe6;"></span>')
    return (f'      <div style="{WATCH_GRID} height: 50px; flex-shrink: 0;{border}">\n'
            f'        <div style="display: flex; flex-direction: column; min-width: 0;">'
            f'<span style="font-size: 14px; font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">'
            f'{html.escape(item["name"])}</span>'
            f'<span class="num" style="font-size: 11px; color: #a3a9b3;">{html.escape(item["code"])} · {item["market"]}</span></div>\n'
            f'        <span class="num" style="font-size: 14px; text-align: right;">{price_text}</span>\n'
            f'        <span class="num" style="font-size: 13px; text-align: right; color: {color};">{pct_text}</span>\n'
            f'        <div style="height: 4px; background: #2a2f38; border-radius: 2px; position: relative;">{dot}</div>\n'
            f'      </div>')


def build_watchlist():
    """관심종목 줄들과 '+ 종목 추가' 버튼, 시세를 못 받은 종목 이름 목록을 돌려줍니다."""
    items, sheet_url, error = load_watchlist()
    if error:
        msg = (f'      <div style="padding: 24px 4px; font-size: 13px; color: #a3a9b3; line-height: 1.6;">'
               f'관심종목을 불러오지 못했어요.<br><span style="color: #f07178;">{html.escape(error)}</span></div>')
        return msg, _watch_add_button(""), ["관심종목"]
    if not items:
        msg = ('      <div style="padding: 24px 4px; font-size: 13px; color: #a3a9b3;">'
               '구글 시트 "관심종목" 탭에 종목을 적어 주세요.</div>')
        return msg, _watch_add_button(sheet_url), []
    rows = [_watch_row(it, i == len(items) - 1) for i, it in enumerate(items)]
    failed = [it["name"] for it in items if fetch_watch_quote(it["code"], it["market"]) is None]
    return "\n".join(rows), _watch_add_button(sheet_url), failed


def market_status(now_kst):
    """상단 바의 장 상태 글자와 점 색. 공휴일은 따지지 않는 간단한 계산입니다."""
    if now_kst.weekday() < 5 and (9, 0) <= (now_kst.hour, now_kst.minute) < (15, 30):
        return "국내 장중", "#3fbf8f"
    now_ny = now_kst.astimezone(NEW_YORK)    # 미국 서머타임은 자동으로 반영됨
    if now_ny.weekday() < 5 and (9, 30) <= (now_ny.hour, now_ny.minute) < (16, 0):
        return "미국 장중", "#3fbf8f"
    return "장 마감", "#8d939d"


def build_dashboard_html(now_kst=None):
    """자료를 받아 목업 빈칸을 모두 채운 HTML 한 덩어리를 돌려줍니다."""
    now_kst = now_kst or datetime.now(KST)
    status_text, status_color = market_status(now_kst)

    cards = "\n".join(_index_card(*item) for item in INDEX_CARDS)
    failed_names = [item[0] for item in INDEX_CARDS if not fetch_price_history(item[1])]

    rows = []
    for i, item in enumerate(MACRO_ITEMS):
        row_html, failed = _macro_row(*item, is_last=(i == len(MACRO_ITEMS) - 1))
        rows.append(row_html)
        if failed:
            failed_names.append(item[0])

    watch_rows, watch_add, watch_failed = build_watchlist()
    failed_names += watch_failed

    heatmap_tabs, heatmap_html, heatmap_failed = build_heatmaps()
    failed_names += heatmap_failed

    if len(failed_names) > 3:      # 많으면 한 줄에 다 안 들어가서 개수만 표시
        failed_note = f" · 받아오지 못한 자료 {len(failed_names)}개 (인터넷 연결 또는 자료 제공처 확인)"
    elif failed_names:
        failed_note = f" · 받아오지 못한 자료: {', '.join(failed_names)}"
    else:
        failed_note = ""

    page = TEMPLATE_PATH.read_text(encoding="utf-8")
    for marker, value in {
        "{{STATUS_TEXT}}": status_text,
        "{{STATUS_COLOR}}": status_color,
        "{{UPDATED}}": now_kst.strftime("%H:%M:%S"),
        "{{INDEX_CARDS}}": cards,
        "{{MACRO_ROWS}}": "\n".join(rows),
        "{{WATCH_ROWS}}": watch_rows,
        "{{HEATMAP_TABS}}": heatmap_tabs,
        "{{HEATMAP}}": heatmap_html,
        "{{WATCH_ADD}}": watch_add,
        "{{FAILED_NOTE}}": html.escape(failed_note),
    }.items():
        page = page.replace(marker, value)
    return page
