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
    "FRED_API_KEY": "FRED 인증키 (미국 지표 발표일)",
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

# 미국 시장 히트맵 - 시가총액 상위 종목을 업종별로 묶은 고정 목록입니다.
#   (업종 이름, [티커, ...]) 순서는 상관없습니다 (타일 크기·배치는 시가총액으로 자동 결정).
#   몇 달에 한 번 시가총액 순위가 크게 바뀌면 여기서 티커를 넣고 빼면 됩니다.
REFRESH_MARKETCAP_SEC = 24 * 60 * 60   # 타일 크기(시가총액)는 하루 1번만 새로 받음
HEATMAPS = {
    "S&P 500": [
        ("반도체", ["NVDA", "AVGO", "AMD", "QCOM", "TXN", "MU", "AMAT", "LRCX", "KLAC", "INTC"]),
        ("빅테크", ["MSFT", "AAPL", "GOOGL", "META", "AMZN"]),
        ("소프트웨어", ["ORCL", "CRM", "PLTR", "ADBE", "NOW", "IBM", "CSCO"]),
        ("소비", ["TSLA", "WMT", "COST", "HD", "MCD", "PG", "KO", "PEP"]),
        ("미디어·통신", ["NFLX", "TMUS", "DIS"]),
        ("금융", ["BRK-B", "JPM", "V", "MA", "BAC", "WFC", "GS", "MS", "AXP"]),
        ("헬스케어", ["LLY", "UNH", "JNJ", "ABBV", "MRK", "ABT", "TMO", "ISRG"]),
        ("산업·에너지", ["XOM", "CVX", "GE", "CAT", "RTX"]),
    ],
    "나스닥 100": [
        ("반도체", ["NVDA", "AVGO", "AMD", "QCOM", "TXN", "MU", "AMAT", "LRCX", "KLAC", "ADI", "INTC", "ASML"]),
        ("빅테크", ["MSFT", "AAPL", "GOOGL", "META", "AMZN"]),
        ("소프트웨어·인터넷", ["NFLX", "PLTR", "ADBE", "INTU", "CSCO", "PANW", "CRWD", "APP", "SHOP"]),
        ("소비", ["TSLA", "COST", "PEP", "BKNG", "SBUX"]),
        ("헬스케어", ["ISRG", "AMGN", "GILD", "VRTX", "REGN"]),
        ("통신·기타", ["TMUS", "CMCSA", "LIN", "HON"]),
    ],
}

# ---------------------------------------------------------------- 경제 일정
CALENDAR_DAYS = 14    # 오늘부터 며칠 뒤까지 보여줄지

# FRED 발표 일정에서 골라 보여줄 미국 지표: FRED의 영문 발표 이름 → (화면 이름, 중요도 1~3)
FRED_RELEASES = {
    "Consumer Price Index": ("소비자물가지수 (CPI)", 3),
    "Employment Situation": ("고용보고서 (비농업 고용)", 3),
    "Personal Income and Outlays": ("개인소비지출 (PCE)", 3),
    "Gross Domestic Product": ("국내총생산 (GDP)", 2),
    "Producer Price Index": ("생산자물가지수 (PPI)", 2),
    "Advance Monthly Sales for Retail and Food Services": ("소매판매", 2),
    "Job Openings and Labor Turnover Survey": ("구인건수 (JOLTS)", 1),
}

# FOMC 금리 결정일 (회의 둘째 날, 미국 날짜 - 한국 시간으로는 다음 날 새벽 3시경 발표)
#   연준이 매년 다음 해 일정을 미리 발표합니다. 연 1회 federalreserve.gov에서 확인해 추가하세요.
FOMC_DATES = [
    "2026-01-28", "2026-03-18", "2026-04-29", "2026-06-17",
    "2026-07-29", "2026-09-16", "2026-10-28", "2026-12-09",
    # 2027년은 연준의 잠정 일정 (확정되면 다시 확인)
    "2027-01-27", "2027-03-17", "2027-04-28", "2027-06-09",
    "2027-07-28", "2027-09-15", "2027-10-27", "2027-12-08",
]

# 한국은행 금융통화위원회 기준금리 결정일. 매년 말 한국은행이 다음 해 일정을 발표하면 추가하세요.
BOK_DATES = [
    "2026-01-15", "2026-02-26", "2026-04-10", "2026-05-28",
    "2026-07-16", "2026-08-27", "2026-10-22", "2026-11-26",
]
EARNINGS_IMPORTANCE = 2   # 관심종목 실적 발표의 중요도

# ---------------------------------------------------------------- 시장 위험 신호
# (화면 이름, 출처, 코드, 기준) - 기준은 render.py의 _risk_level에서 상태(정상/주의/위험)를 정할 때 씁니다.
#   "curve": 장단기 금리차(%p) / "hy": 하이일드 스프레드(%) / "drawdown": 52주 고점 대비 하락률(%)
RISK_ITEMS = [
    ("장단기 금리차 (10년−2년)", "fred", "T10Y2Y", "curve"),
    ("하이일드 채권 스프레드", "fred", "BAMLH0A0HYM2", "hy"),
    ("S&P 500 고점 대비", "yahoo", "^GSPC", "drawdown"),
    ("나스닥 100 고점 대비", "yahoo", "^NDX", "drawdown"),
    ("반도체(SOX) 고점 대비", "yahoo", "^SOX", "drawdown"),
]
