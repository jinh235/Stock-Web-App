# -*- coding: utf-8 -*-
"""
주식 앱의 시작 파일. 실행: python -m streamlit run stock.py

파일 역할
  - stock.py  : 시작 파일. 화면 설정과 5분 자동 갱신만 담당
  - config.py : 지수·지표 목록, 새로고침 주기 같은 설정값
  - data.py   : 자료 받아오기 (야후 파이낸스, FRED, 한국은행 ECOS)
  - render.py : 목업 HTML(templates/dashboard.html)의 빈칸을 실제 숫자로 채우기
  - sheets.py : 구글 시트 "주식앱" 읽기 (관심종목 목록)
  - heatmap.py: 미국 시장 히트맵(트리맵) 그리기

1단계: 지수 카드 6개 + 거시경제 지표 카드를 실제 자료로 채움.
2단계: 관심종목 카드 (목록은 구글 시트에서 관리, 앱은 읽기만).
3단계: 미국 시장 히트맵 (S&P 500 / 나스닥 100 전환).
4단계: 다가오는 경제 일정 (FOMC·금통위는 config.py, 미국 지표는 FRED, 실적 발표는 관심종목).
5단계: 시장 위험 신호 (포트폴리오는 토스 앱에서 보므로 만들지 않고 이 카드로 대체).
"""
import streamlit as st

from config import APP_ICON, APP_TITLE, REFRESH_PRICE_SEC
from render import build_dashboard_html

# 브라우저 탭 제목·아이콘, 넓은 화면 사용. 반드시 다른 st. 명령보다 먼저 와야 합니다.
st.set_page_config(page_title=APP_TITLE, page_icon=APP_ICON, layout="wide")

# Streamlit 기본 여백과 상단 메뉴줄을 줄여서 목업 화면이 꽉 차 보이게 합니다.
st.markdown("""
<style>
.block-container {padding: 0.5rem 0.5rem 0 0.5rem; max-width: 100%;}
header[data-testid="stHeader"] {display: none;}
</style>
""", unsafe_allow_html=True)


@st.fragment(run_every=REFRESH_PRICE_SEC)
def show_dashboard():
    """대시보드를 그립니다. @st.fragment(run_every=...) 덕분에 이 부분만 5분마다 다시 그려집니다."""
    with st.spinner("시세를 불러오는 중..."):
        page = build_dashboard_html()
    if hasattr(st, "iframe"):
        # 새 방식(Streamlit 최신 버전): 높이를 내용에 맞춰 자동으로 정합니다.
        st.iframe(page, height="content")
    else:
        # 예전 버전용: 목업 높이(1140px)만큼 자리를 잡아 줍니다.
        import streamlit.components.v1 as components
        components.html(page, height=1150, scrolling=False)


show_dashboard()
