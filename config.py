# -*- coding: utf-8 -*-
"""
주식 앱 설정값 모음.
숫자나 목록을 바꾸고 싶을 때 다른 파일을 뒤지지 않고 이 파일만 고치면 되도록 모아 둡니다.
"""

APP_TITLE = "주식 대시보드"
APP_ICON = "📈"

# 새로고침 주기(초). 무료 자료 제공처의 사용 한도를 넘지 않도록 자료 종류별로 다르게 둡니다.
REFRESH_PRICE_SEC = 5 * 60        # 지수·주가: 5분마다
REFRESH_MACRO_SEC = 24 * 60 * 60  # 금리·물가 같은 거시지표: 하루 1번

# secrets.toml(또는 Streamlit Cloud의 Secrets)에 들어 있어야 하는 항목: 이름 → 설명
SECRET_ITEMS = {
    "ECOS_API_KEY": "한국은행 ECOS 인증키",
    "DATA_GO_KR_API_KEY": "공공데이터포털 인증키",
}

# 0단계 연결 확인에 쓰는 지수 (야후 파이낸스 기호 → 화면에 보일 이름)
TEST_TICKERS = {
    "^GSPC": "S&P 500",
    "^KS11": "코스피",
    "KRW=X": "원/달러 환율",
}
