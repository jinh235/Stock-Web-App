# -*- coding: utf-8 -*-
"""
구글 시트 "주식앱" 연결 담당 (읽기 위주).

관심종목처럼 직접 관리하는 목록은 구글 시트에서 고치고, 앱은 읽기만 합니다.
(주식 앱은 공개 앱이라, 앱 화면에서 고칠 수 있게 하면 다른 사람도 바꿀 수 있기 때문)

인증은 가계부 앱과 같은 서비스 계정을 씁니다.
  - secrets의 GOOGLE_CREDENTIALS : 가계부 앱 secrets에 있는 값을 그대로 복사
  - 시트 "주식앱"을 서비스 계정 이메일에 '편집자'로 공유해야 합니다
"""
import json

import gspread
import streamlit as st
from google.oauth2.service_account import Credentials

from config import (REFRESH_PRICE_SEC, SCOPE, SHEET_NAME, WATCHLIST_HEADERS,
                    WATCHLIST_SEED, WATCHLIST_TAB)


@st.cache_resource(show_spinner=False)
def _get_doc():
    """구글 인증 후 "주식앱" 시트 파일을 엽니다. 한 번 열면 앱이 켜져 있는 동안 재사용합니다."""
    creds_dict = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPE)
    return gspread.authorize(creds).open(SHEET_NAME)


def _get_watchlist_ws(doc):
    """관심종목 탭을 가져옵니다. 없으면 만들고 예시 8종목을 채워 둡니다 (처음 한 번만)."""
    try:
        return doc.worksheet(WATCHLIST_TAB)
    except gspread.WorksheetNotFound:
        ws = doc.add_worksheet(title=WATCHLIST_TAB, rows=100, cols=len(WATCHLIST_HEADERS))
        # 코드 앞자리 0이 사라지지 않도록(005930) RAW로 글자 그대로 저장합니다.
        ws.update([WATCHLIST_HEADERS] + WATCHLIST_SEED, value_input_option="RAW")
        return ws


@st.cache_data(ttl=REFRESH_PRICE_SEC, show_spinner=False)
def load_watchlist():
    """관심종목 목록을 읽습니다.
    반환값: (목록, 시트 주소, 오류 설명)
      - 목록: [{"name": 종목명, "code": 코드, "market": "KR"/"US"}, ...]
      - 실패하면 목록은 빈 칸, 오류 설명에 이유가 들어갑니다."""
    try:
        doc = _get_doc()
        ws = _get_watchlist_ws(doc)
        rows = ws.get_all_values()[1:]          # 첫 줄(제목)은 빼고
    except KeyError:
        return [], "", "secrets에 GOOGLE_CREDENTIALS가 없습니다"
    except gspread.SpreadsheetNotFound:
        return [], "", f'"{SHEET_NAME}" 시트를 찾지 못했습니다 (이름·공유 확인)'
    except Exception as e:                       # 인터넷 끊김, 구글 일시 오류 등
        return [], "", f"구글 시트 연결 실패: {e}"

    items = []
    for row in rows:
        row = (row + ["", "", ""])[:3]
        name, code, market = (c.strip() for c in row)
        if not code:
            continue
        market = market.upper() or ("KR" if code.isdigit() else "US")
        if market == "KR" and code.isdigit():
            code = code.zfill(6)                  # 5930 처럼 0이 빠져 있어도 005930으로
        items.append({"name": name or code, "code": code, "market": market})
    return items, doc.url, ""
