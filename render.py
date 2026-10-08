# -*- coding: utf-8 -*-
"""
목업 HTML(templates/dashboard.html)의 빈칸({{이름}})을 실제 숫자로 채우는 담당.

목업에서 숫자가 들어가던 자리는 {{INDEX_CARDS}}, {{MACRO_ROWS}} 같은 표시로 바꿔 두었고,
여기서 목업과 똑같은 모양의 HTML 조각을 만들어 그 자리에 끼워 넣습니다.
"""
import html
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from config import INDEX_CARDS, MACRO_ITEMS
from data import fetch_ecos, fetch_fred, fetch_price_history

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


def _sparkline(values, color):
    """값 목록을 카드 오른쪽 작은 선 그래프(가로 84 × 세로 32)로 바꿉니다."""
    lo, hi = min(values), max(values)
    span = (hi - lo) or 1
    step = 84 / (len(values) - 1)
    # 위아래 4px씩 여백을 두고, 값이 클수록 위쪽(y가 작은 쪽)에 찍힙니다.
    points = " ".join(f"{i * step:.1f},{28 - (v - lo) / span * 24:.1f}" for i, v in enumerate(values))
    # 변화 글자가 길면 그래프가 조금 좁아지도록(최소 40px) 해서 글자가 두 줄로 꺾이지 않게 합니다.
    return (f'<svg width="84" height="32" viewBox="0 0 84 32" preserveAspectRatio="none" '
            f'style="flex: 0 1 84px; min-width: 40px;" aria-hidden="true">'
            f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="2"/></svg>')


def _index_card(name, ticker, kind):
    values = fetch_price_history(ticker)
    if not values:
        value_text, change_text, color, spark = "—", "자료 없음", MUTED, ""
    else:
        last, prev = values[-1], values[-2]
        diff = last - prev
        color = _color(diff)
        arrow = "▲" if diff > 0 else ("▼" if diff < 0 else "")
        if kind == "yield":   # 금리는 %, 변화는 %p
            value_text = f"{last:.2f}%"
            change_text = f"{arrow} {abs(diff):.2f}%p"
        else:
            pct = diff / prev * 100 if prev else 0
            sign = "+" if pct > 0 else (MINUS if pct < 0 else "")
            value_text = f"{last:,.2f}"
            diff_text = f"{abs(diff):,.2f}" if abs(diff) < 100 else f"{abs(diff):,.1f}"  # 목업처럼 114.6
            change_text = f"{arrow} {diff_text} {sign}{abs(pct):.2f}%"
        spark = _sparkline(values, color if color != FLAT else MUTED)
    return f'''  <div class="card" style="padding: 14px 16px; display: flex; flex-direction: column; gap: 6px;">
    <span style="font-size: 13px; color: #a3a9b3;">{html.escape(name)}</span>
    <div style="display: flex; align-items: flex-end; justify-content: space-between; gap: 8px;">
      <div style="display: flex; flex-direction: column; gap: 2px;"><span class="num" style="font-size: 22px; font-weight: 600;">{value_text}</span><span class="num" style="font-size: 13px; color: {color}; white-space: nowrap;">{change_text.strip()}</span></div>
      {spark}
    </div>
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
    failed_names = [name for name, ticker, _ in INDEX_CARDS if not fetch_price_history(ticker)]

    rows = []
    for i, item in enumerate(MACRO_ITEMS):
        row_html, failed = _macro_row(*item, is_last=(i == len(MACRO_ITEMS) - 1))
        rows.append(row_html)
        if failed:
            failed_names.append(item[0])

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
        "{{FAILED_NOTE}}": html.escape(failed_note),
    }.items():
        page = page.replace(marker, value)
    return page
