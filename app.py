# -*- coding: utf-8 -*-
"""
주식 앱의 시작 파일. 실행: streamlit run app.py

지금은 0단계(환경 설정)라서 설정 확인 화면만 보여줍니다.
  - 인증키가 들어 있는지, 시세 자료를 받아올 수 있는지 점검합니다.
1단계부터 이 확인 화면 자리에 실제 대시보드가 들어갑니다.
(비밀번호 화면은 보유 종목이 들어가는 포트폴리오 단계에서 필요하면 추가합니다.)
"""
import streamlit as st
import yfinance as yf

from config import APP_ICON, APP_TITLE, REFRESH_PRICE_SEC, SECRET_ITEMS, TEST_TICKERS

# 브라우저 탭 제목·아이콘, 넓은 화면 사용. 반드시 다른 st. 명령보다 먼저 와야 합니다.
st.set_page_config(page_title=APP_TITLE, page_icon=APP_ICON, layout="wide")


def get_secret(name):
    """secrets.toml(또는 Streamlit Cloud의 Secrets)에서 값을 꺼냅니다. 없으면 빈 글자."""
    try:
        return str(st.secrets.get(name, "")).strip()
    except Exception:      # secrets.toml 파일 자체가 없을 때
        return ""


@st.cache_data(ttl=REFRESH_PRICE_SEC, show_spinner=False)
def fetch_last_price(ticker):
    """야후 파이낸스에서 최근 종가를 받아옵니다. 실패하면 None.
    @st.cache_data 덕분에 REFRESH_PRICE_SEC(5분) 동안은 다시 받지 않고 저장해 둔 값을 씁니다."""
    try:
        closes = yf.Ticker(ticker).history(period="5d")["Close"].dropna()
        return float(closes.iloc[-1]) if len(closes) else None
    except Exception:
        return None


def render_setup_check():
    """0단계 확인 화면."""
    st.title(f"{APP_ICON} {APP_TITLE}")
    st.caption("0단계 · 환경 설정 확인 화면입니다. 아래가 모두 ✅면 1단계로 넘어갈 수 있어요.")

    st.subheader("1. 비밀 정보(Secrets)")
    for name, label in SECRET_ITEMS.items():
        if get_secret(name):
            st.write(f"✅ {label} (`{name}`)")
        else:
            st.write(f"⬜ {label} (`{name}`) - 아직 비어 있음")

    st.subheader("2. 시세 자료 받아오기")
    columns = st.columns(len(TEST_TICKERS))
    for column, (ticker, label) in zip(columns, TEST_TICKERS.items()):
        price = fetch_last_price(ticker)
        column.metric(label, f"{price:,.2f}" if price is not None else "받아오지 못함")


render_setup_check()
