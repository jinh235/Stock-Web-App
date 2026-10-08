# -*- coding: utf-8 -*-
"""
자료 받아오기 담당 (야후 파이낸스, FRED, 한국은행 ECOS).

모든 함수는 실패해도 앱이 멈추지 않도록 None을 돌려줍니다.
화면 쪽(render.py)에서는 None이면 "—"로 표시합니다.

@st.cache_data(ttl=초) : 같은 요청은 그 시간 동안 다시 받지 않고 저장해 둔 값을 씁니다.
  → 5분마다 화면이 새로 그려져도 거시지표는 하루 1번만 실제로 받아옵니다.
"""
import io
from datetime import date, timedelta

import pandas as pd
import requests
import streamlit as st
import yfinance as yf

from config import REFRESH_MACRO_SEC, REFRESH_PRICE_SEC, SPARK_PERIOD

TIMEOUT = 15  # 자료 제공처가 응답이 없을 때 최대 기다리는 시간(초)


def get_secret(name):
    """secrets.toml(또는 Streamlit Cloud의 Secrets)에서 값을 꺼냅니다. 없으면 빈 글자."""
    try:
        return str(st.secrets.get(name, "")).strip()
    except Exception:      # secrets.toml 파일 자체가 없을 때
        return ""


# ---------------------------------------------------------------- 야후 파이낸스
@st.cache_data(ttl=REFRESH_PRICE_SEC, show_spinner=False)
def fetch_price_history(ticker, period=SPARK_PERIOD):
    """최근 기간의 일별 종가 목록(오래된 것 → 최신)을 돌려줍니다. 실패하면 None.
    장중에는 마지막 값이 '오늘 현재가'입니다."""
    try:
        closes = yf.Ticker(ticker).history(period=period, interval="1d")["Close"].dropna()
        values = [float(v) for v in closes]
        return values if len(values) >= 2 else None
    except Exception:
        return None


# ---------------------------------------------------------------- FRED (미국)
@st.cache_data(ttl=REFRESH_MACRO_SEC, show_spinner=False)
def fetch_fred(series_id, years=3):
    """FRED 통계 하나를 [(날짜, 값), ...] (오래된 것 → 최신)으로 돌려줍니다. 실패하면 None.
    인증키 없이 받을 수 있는 CSV 주소를 씁니다."""
    start = (date.today() - timedelta(days=365 * years)).isoformat()
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}&cosd={start}"
    try:
        res = requests.get(url, timeout=TIMEOUT)
        res.raise_for_status()
        df = pd.read_csv(io.StringIO(res.text))
        df.columns = ["date", "value"]                       # 1열 날짜, 2열 값
        df["value"] = pd.to_numeric(df["value"], errors="coerce")   # 빈 값(".")은 버림
        df = df.dropna()
        rows = [(pd.Timestamp(d).date(), float(v)) for d, v in zip(df["date"], df["value"])]
        return rows or None
    except Exception:
        return None


# ---------------------------------------------------------------- 한국은행 ECOS
@st.cache_data(ttl=REFRESH_MACRO_SEC, show_spinner=False)
def fetch_ecos(code, years=3):
    """ECOS 통계 하나를 [(날짜, 값), ...] (오래된 것 → 최신)으로 돌려줍니다. 실패하면 None.
    code는 "통계코드/항목코드" 형식입니다. 예: "722Y001/0101000" (한국은행 기준금리, 일별)"""
    key = get_secret("ECOS_API_KEY")
    if not key:
        return None
    stat, item = code.split("/")
    start = (date.today() - timedelta(days=365 * years)).strftime("%Y%m%d")
    end = date.today().strftime("%Y%m%d")
    url = (f"https://ecos.bok.or.kr/api/StatisticSearch/{key}/json/kr/1/2000/"
           f"{stat}/D/{start}/{end}/{item}")
    try:
        res = requests.get(url, timeout=TIMEOUT)
        res.raise_for_status()
        rows = res.json().get("StatisticSearch", {}).get("row", [])
        out = [(pd.Timestamp(r["TIME"]).date(), float(r["DATA_VALUE"])) for r in rows if r.get("DATA_VALUE")]
        return out or None
    except Exception:
        return None


@st.cache_data(ttl=REFRESH_PRICE_SEC, show_spinner=False)
def fetch_watch_quote(code, market):
    """관심종목 한 개의 시세. 반환값: {"last", "prev", "low52", "high52"} 또는 None.
    한국 종목은 야후 기호가 005930.KS(코스피) / 005930.KQ(코스닥)라서 둘 다 시도합니다."""
    tickers = [f"{code}.KS", f"{code}.KQ"] if market == "KR" else [code]
    for ticker in tickers:
        try:
            df = yf.Ticker(ticker).history(period="1y", interval="1d").dropna(subset=["Close"])
        except Exception:
            continue
        if len(df) >= 2:
            return {
                "last": float(df["Close"].iloc[-1]),
                "prev": float(df["Close"].iloc[-2]),
                "low52": float(df["Low"].min()),     # 최근 1년(52주) 중 가장 낮았던 값
                "high52": float(df["High"].max()),   # 최근 1년(52주) 중 가장 높았던 값
            }
    return None
