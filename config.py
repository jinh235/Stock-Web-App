# -*- coding: utf-8 -*-
"""
주식 앱 설정값 모음.
숫자나 목록을 바꾸고 싶을 때 다른 파일을 뒤지지 않고 이 파일만 고치면 되도록 모아 둡니다.
"""

APP_TITLE = "마켓 보드"
APP_ICON = "📈"

# 새로고침 주기(초). 무료 자료 제공처의 사용 한도를 넘지 않도록 자료 종류별로 다르게 둡니다.
REFRESH_PRICE_SEC = 5 * 60        # 지수·주가: 5분마다
REFRESH_MACRO_SEC = 24 * 60 * 60  # 금리·물가 같은 거시지표: 하루 1번

# secrets.toml(또는 Streamlit Cloud의 Secrets)에 들어 있어야 하는 항목: 이름 → 설명
SECRET_ITEMS = {
    "ECOS_API_KEY": "한국은행 ECOS 인증키",
    "DATA_GO_KR_API_KEY": "공공데이터포털 인증키",
}

# 맨 위 큰 지수 카드 8개 (4개씩 두 줄, 왼쪽 위부터 순서대로)
#   (화면 이름, 야후 파이낸스 기호, 종류, 곱할 값)
#   종류 - "index": 지수·환율(소수 둘째 자리) / "yield": 금리(%, 변화는 %p) / "usd": 달러 가격(정수, $ 표시)
#   곱할 값 - 보통 1. 엔화는 1엔 기준 값이 와서 100을 곱해 '원/100엔'으로 표시
INDEX_CARDS = [
    ("코스피", "^KS11", "index", 1),
    ("S&P 500", "^GSPC", "index", 1),
    ("나스닥", "^IXIC", "index", 1),
    ("나스닥 100", "^NDX", "index", 1),
    ("원/달러 환율", "KRW=X", "index", 1),
    ("원/100엔 환율", "JPYKRW=X", "index", 100),
    ("비트코인", "BTC-USD", "usd", 1),
    ("미 국채 10년물", "^TNX", "yield", 1),
]
SPARK_PERIOD = "1mo"   # 카드 안 작은 선 그래프 기간: 최근 1개월

# 거시경제 지표 카드 (위에서부터 순서대로)
#   (화면 이름, 출처, 코드, 종류)
#   출처 - "fred": 미국 연준 통계(FRED) / "ecos": 한국은행 / "yahoo": 야후 파이낸스
#   종류 - "yoy": 전년 같은 달 대비 상승률(%) / "rate": 금리·비율(%) / "level": 숫자 그대로
MACRO_ITEMS = [
    ("미국 CPI (전년비)", "fred", "CPIAUCSL", "yoy"),
    ("미국 기준금리", "fred", "DFEDTARU", "rate"),
    ("한국 기준금리", "ecos", "722Y001/0101000", "rate"),
    ("미국 실업률", "fred", "UNRATE", "rate"),
    ("달러 인덱스", "yahoo", "DX-Y.NYB", "level"),
    ("VIX 공포지수", "yahoo", "^VIX", "level"),
    ("WTI 유가 ($)", "yahoo", "CL=F", "level"),
]

# 구글 시트 (관심종목 등 직접 관리하는 목록) - 가계부 앱과 같은 서비스 계정을 씁니다.
SHEET_NAME = "주식앱"              # 구글 드라이브의 시트 파일 이름 (정확히 같아야 함)
WATCHLIST_TAB = "관심종목"          # 그 파일 안의 탭 이름
WATCHLIST_HEADERS = ["종목명", "코드", "시장"]
SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
# 관심종목 탭을 처음 만들 때 채워 넣는 예시 (목업과 같은 8종목). 이후에는 시트에서 직접 고치세요.
WATCHLIST_SEED = [
    ["삼성전자", "005930", "KR"],
    ["SK하이닉스", "000660", "KR"],
    ["현대차", "005380", "KR"],
    ["NAVER", "035420", "KR"],
    ["Apple", "AAPL", "US"],
    ["NVIDIA", "NVDA", "US"],
    ["Microsoft", "MSFT", "US"],
    ["Tesla", "TSLA", "US"],
]
