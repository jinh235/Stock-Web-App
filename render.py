# -*- coding: utf-8 -*-
"""
목업 HTML(templates/dashboard.html)의 빈칸({{이름}})을 실제 숫자로 채우는 담당.

목업에서 숫자가 들어가던 자리는 {{INDEX_CARDS}}, {{MACRO_ROWS}} 같은 표시로 바꿔 두었고,
여기서 목업과 똑같은 모양의 HTML 조각을 만들어 그 자리에 끼워 넣습니다.
"""
import html
import json
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from config import (BOK_DATES, CALENDAR_DAYS, EARNINGS_IMPORTANCE, FOMC_DATES, FRED_RELEASES,
                    INDEX_CARDS, MACRO_ITEMS, RISK_ITEMS)
from data import (fetch_earnings_date, fetch_ecos, fetch_fred, fetch_fred_release_dates, fetch_price_history,
                  fetch_price_series, fetch_watch_quote)
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
    marks = _extreme_marks(dates, values, pts, color, kind)
    return (f'<div class="chart" data-series="{data}" style="position: relative; height: {CHART_H}px; cursor: crosshair;">'
            f'<svg width="100%" height="{CHART_H}" viewBox="0 0 {CHART_W} {CHART_H}" preserveAspectRatio="none" aria-hidden="true">'
            f'<polygon points="{area}" fill="{color}" opacity="0.10"/>'
            f'<polyline points="{line}" fill="none" stroke="{color}" stroke-width="2" vector-effect="non-scaling-stroke"/></svg>'
            f'{marks}'
            f'<div class="hl" style="display: none; position: absolute; top: 0; bottom: 0; width: 1px; background: #5a606b;"></div>'
            f'<div class="dot" style="display: none; position: absolute; width: 8px; height: 8px; margin: -4px 0 0 -4px; '
            f'border-radius: 50%; background: {color}; border: 2px solid #181b21; box-sizing: content-box;"></div>'
            f'<div class="tip num" style="display: none; position: absolute; top: 0; padding: 3px 8px; border-radius: 6px; '
            f'background: #2a2f38; border: 1px solid #3a404b; font-size: 12px; white-space: nowrap; pointer-events: none;"></div>'
            f'</div>')


def _fmt_value(v, kind):
    """카드 값 표시 형식 (금리 %, 달러 정수, 나머지 소수 둘째 자리)."""
    if kind == "yield":
        return f"{v:.2f}%"
    if kind == "usd":
        return f"${v:,.0f}"
    return f"{v:,.2f}"


def _extreme_marks(dates, values, pts, color, kind):
    """그래프에서 1개월 최고점·최저점에 짧은 가로 막대를 긋고 옆에 값과 날짜를 적습니다."""
    out = []
    i_hi = max(range(len(values)), key=lambda i: values[i])
    i_lo = min(range(len(values)), key=lambda i: values[i])
    for i in (i_hi, i_lo):
        x_pct = pts[i][0] / CHART_W * 100
        y = pts[i][1]
        # 점이 왼쪽 절반에 있으면 글자를 오른쪽에, 오른쪽 절반이면 왼쪽에 붙여 카드 밖으로 나가지 않게 합니다.
        if x_pct < 50:
            pos = f"left: calc({x_pct:.2f}% + 9px);"
        else:
            pos = f"right: calc({100 - x_pct:.2f}% + 9px);"
        top = max(0, min(CHART_H - 14, y - 7))
        # 최고·최저 위치에 짧은 가로 막대
        out.append(f'<div style="position: absolute; left: {x_pct:.2f}%; top: {y:.1f}px; width: 12px; height: 2px; '
                   f'margin: -1px 0 0 -6px; background: #ecebe6; border-radius: 1px; pointer-events: none;"></div>')
        out.append(f'<div class="num" style="position: absolute; {pos} top: {top:.1f}px; font-size: 10.5px; '
                   f'color: #cfd3da; white-space: nowrap; pointer-events: none; text-shadow: 0 0 3px #181b21, 0 0 3px #181b21;">'
                   f'{_fmt_value(values[i], kind)} <span style="color: #8d939d;">{dates[i]}</span></div>')
    return "".join(out)


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


WEEKDAYS = "월화수목금토일"


def _calendar_events(today):
    """오늘부터 CALENDAR_DAYS일 뒤까지의 일정: [(날짜, 나라, 이름, 중요도), ...] 와 안내 문구."""
    end = today + timedelta(days=CALENDAR_DAYS)
    events, note = [], ""

    def add(day_text, country, name, importance):
        d = date.fromisoformat(day_text)
        if today <= d <= end:
            events.append((d, country, name, importance))

    for d in FOMC_DATES:
        add(d, "US", "FOMC 금리 결정", 3)
    for d in BOK_DATES:
        add(d, "KR", "한국은행 기준금리 결정", 2)

    releases, error = fetch_fred_release_dates(today.isoformat(), end.isoformat())
    if releases is None:
        note = f"{error} · "        # 키가 없거나 실패하면 미국 지표 발표일만 빠지고, 이유를 머리글에 표시
    else:
        seen = set()
        for day_text, name in releases:
            if name in FRED_RELEASES and (day_text, name) not in seen:
                seen.add((day_text, name))
                label, importance = FRED_RELEASES[name]
                add(day_text, "US", label, importance)

    items, _, _ = load_watchlist()
    for it in items:
        day_text = fetch_earnings_date(it["code"], it["market"])
        if day_text:
            add(day_text, it["market"], f'{it["name"]} 실적 발표', EARNINGS_IMPORTANCE)

    events.sort(key=lambda e: (e[0], -e[3]))
    return events, note


def build_calendar(today=None):
    """경제 일정 줄들과 머리글 안내 문구를 돌려줍니다."""
    today = today or datetime.now(KST).date()
    events, note = _calendar_events(today)
    if not events:
        return ('      <div style="padding: 24px 4px; font-size: 13px; color: #a3a9b3;">'
                f'앞으로 {CALENDAR_DAYS}일 안에 등록된 일정이 없어요.</div>'), note
    rows = []
    for i, (d, country, name, importance) in enumerate(events):
        border = "" if i == len(events) - 1 else " border-bottom: 1px solid #20242b;"
        is_today = d == today
        day_color = "#ecebe6" if is_today else "#a3a9b3"
        day_text = "오늘" if is_today else f"{d:%m/%d} {WEEKDAYS[d.weekday()]}"
        dots = "●" * importance + f'<span style="color: #3a3f48;">{"●" * (3 - importance)}</span>'
        rows.append(
            f'      <div style="display: flex; align-items: center; gap: 14px; height: 44px; flex-shrink: 0;{border}">'
            f'<span class="num" style="width: 64px; font-size: 12px; color: {day_color};">{day_text}</span>'
            f'<span style="font-size: 11px; padding: 2px 6px; border-radius: 4px; background: #262a32; color: #cfd3da;">{country}</span>'
            f'<span style="flex-grow: 1; font-size: 13px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{html.escape(name)}</span>'
            f'<span style="font-size: 12px; color: #d9a441; letter-spacing: 2px;">{dots}</span></div>')
    return "\n".join(rows), note


# 상태별 글자색·배경색
RISK_STYLES = {"정상": ("#3fbf8f", "#173a2f"), "주의": ("#d9a441", "#3a3122"), "위험": ("#f07178", "#3d2328")}
RISK_HELP = {
    "curve": "10년 국채금리 − 2년 국채금리. 0 아래(역전)는 경기침체 신호로 자주 쓰이며, 역전이 풀리는 시점도 주의 구간으로 봅니다.",
    "hy": "신용등급 낮은 회사채의 추가 금리. 시장이 불안해지면 급등합니다 (보통 5% 이상이면 위험 구간).",
    "drawdown": "최근 1년 최고 종가 대비 현재 위치. −10%는 조정, −20%는 약세장으로 흔히 부릅니다.",
}


def _risk_level(kind, value):
    """지표 종류와 값으로 상태(정상/주의/위험)를 정합니다. 기준은 흔히 쓰이는 대략적인 구간입니다."""
    if kind == "curve":
        return "위험" if value < 0 else ("주의" if value < 0.5 else "정상")
    if kind == "hy":
        return "위험" if value >= 5 else ("주의" if value >= 3.5 else "정상")
    return "위험" if value <= -20 else ("주의" if value <= -10 else "정상")   # drawdown


def _risk_values(source, code, kind):
    """(현재 값, 비교 글자)를 돌려줍니다. 실패하면 None."""
    if kind == "drawdown":
        series = fetch_price_series(code, period="1y")
        if not series:
            return None
        dates, values = series
        i_hi = max(range(len(values)), key=lambda i: values[i])
        return (values[-1] / values[i_hi] - 1) * 100, f"고점 {dates[i_hi]}"
    rows = fetch_fred(code)
    if not rows:
        return None
    latest_date, latest = rows[-1]
    month_ago = [v for d, v in rows if (latest_date - d).days >= 30]
    compare = f"1개월 전 {month_ago[-1]:.2f}" if month_ago else ""
    return latest, compare


def build_risk_card():
    """시장 위험 신호 카드 전체 HTML과, 받아오지 못한 지표 이름 목록."""
    rows, failed = [], []
    for i, (name, source, code, kind) in enumerate(RISK_ITEMS):
        border = "" if i == len(RISK_ITEMS) - 1 else " border-bottom: 1px solid #20242b;"
        result = _risk_values(source, code, kind)
        if result is None:
            failed.append(name)
            value_text, compare, badge = "—", "", ""
        else:
            value, compare = result
            level = _risk_level(kind, value)
            fg, bg = RISK_STYLES[level]
            if kind == "drawdown":
                value_text = "고점" if value > -0.05 else f"{MINUS}{abs(value):.1f}%"
            elif kind == "curve":
                value_text = f"{MINUS if value < 0 else ''}{abs(value):.2f}%p"
            else:
                value_text = f"{value:.2f}%"
            badge = (f'<span style="font-size: 11px; padding: 2px 8px; border-radius: 4px; background: {bg}; '
                     f'color: {fg}; font-weight: 600;">{level}</span>')
        rows.append(
            f'      <div title="{html.escape(RISK_HELP[kind])}" style="display: grid; grid-template-columns: 1.7fr 0.9fr 1.1fr 0.6fr; '
            f'gap: 8px; align-items: center; height: 44px; font-size: 13px; cursor: help;{border}">'
            f'<span style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{html.escape(name)}</span>'
            f'<span class="num" style="text-align: right; font-weight: 600;">{value_text}</span>'
            f'<span class="num" style="text-align: right; font-size: 11px; color: #8d939d;">{html.escape(compare)}</span>'
            f'<span style="text-align: right;">{badge}</span></div>')
    card = ('  <div class="card" style="padding: 18px 20px; display: flex; flex-direction: column; gap: 10px;">\n'
            '    <div style="display: flex; align-items: center; justify-content: space-between;">\n'
            '      <h2 style="margin: 0; font-size: 17px; font-weight: 600;">시장 위험 신호</h2>\n'
            '      <span style="font-size: 11px; color: #a3a9b3;">항목에 마우스를 올리면 설명</span>\n'
            '    </div>\n'
            '    <div style="display: flex; flex-direction: column;">\n' + "\n".join(rows) + '\n    </div>\n  </div>')
    return card, failed


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

    cal_rows, cal_note = build_calendar(now_kst.date())
    risk_card, risk_failed = build_risk_card()
    failed_names += risk_failed
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
        "{{CAL_ROWS}}": cal_rows,
        "{{RISK_CARD}}": risk_card,
        "{{CAL_NOTE}}": cal_note,
        "{{HEATMAP}}": heatmap_html,
        "{{WATCH_ADD}}": watch_add,
        "{{FAILED_NOTE}}": html.escape(failed_note),
    }.items():
        page = page.replace(marker, value)
    return page
