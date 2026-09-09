# -*- coding: utf-8 -*-
"""응답 저장 — Google Sheets 우선, 실패하면 JSON 내려받기로 대체

Streamlit Community Cloud는 앱이 재시작되면 로컬 파일이 사라지므로
responses/ 폴더에 쓰는 방식은 실전에서 응답을 잃는다. 시트에 바로 적는다.

설정 (.streamlit/secrets.toml)
    [gcp_service_account]
    type = "service_account"
    project_id = "..."
    private_key = "-----BEGIN PRIVATE KEY-----\\n...\\n-----END PRIVATE KEY-----\\n"
    client_email = "...@....iam.gserviceaccount.com"
    ...

    [sheets]
    spreadsheet_id = "1AbC...."

서비스 계정 이메일을 해당 스프레드시트에 **편집자**로 공유해야 한다.
"""
import json
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))

SHEET_RESPONSES = "responses"
SHEET_PAIRWISE = "pairwise"
SHEET_RATINGS = "ratings"

HEAD_RESPONSES = [
    "제출시각", "응답ID", "성명/ID", "소속", "응답자유형", "경력", "시흥경험",
    "기준CR", "기준판정", "전이성위반", "블록CR", "재검토블록수",
    "의견1_누락과제", "의견2_실행제약", "의견3_방법론", "payload",
]
HEAD_PAIRWISE = ["제출시각", "응답ID", "응답자유형", "부", "블록", "왼쪽", "오른쪽", "값"]
HEAD_RATINGS = ["제출시각", "응답ID", "응답자유형", "과제코드", "과제명", "실행가능성", "파급효과"]


def now_kst():
    return datetime.now(KST).isoformat(timespec="seconds")


def _client():
    """gspread 클라이언트. 준비가 안 되어 있으면 (None, 사유)."""
    try:
        import streamlit as st
    except Exception as e:                       # pragma: no cover
        return None, f"streamlit 미탑재 ({e})"
    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except Exception:
        return None, "gspread·google-auth 패키지가 설치되어 있지 않습니다."

    try:
        sa = st.secrets["gcp_service_account"]
        sid = st.secrets["sheets"]["spreadsheet_id"]
    except Exception:
        return None, "secrets에 gcp_service_account 또는 sheets.spreadsheet_id가 없습니다."

    try:
        creds = Credentials.from_service_account_info(
            dict(sa),
            scopes=["https://www.googleapis.com/auth/spreadsheets"],
        )
        gc = gspread.authorize(creds)
        return gc.open_by_key(sid), None
    except Exception as e:
        return None, f"스프레드시트 연결 실패 : {e}"


def _tab(book, title, header):
    try:
        ws = book.worksheet(title)
    except Exception:
        ws = book.add_worksheet(title=title, rows=1000, cols=max(len(header), 20))
        ws.append_row(header, value_input_option="RAW")
        return ws
    if not ws.get_all_values():
        ws.append_row(header, value_input_option="RAW")
    return ws


def is_configured():
    book, _err = _client()
    return book is not None


def save(payload):
    """(성공여부, 메시지)"""
    book, err = _client()
    if book is None:
        return False, err

    meta = payload["meta"]
    diag = payload["diagnostics"]
    ts = payload["submittedAt"]
    rid = payload["responseId"]
    rtype = meta.get("field", "")

    blockcr = diag.get("blockCR", {}) or {}
    bad = sum(1 for v in blockcr.values() if v is not None and v > 0.10)

    row = [
        ts, rid, meta.get("name", ""), meta.get("org", ""), rtype,
        meta.get("career", ""), meta.get("siheung", ""),
        "" if diag.get("criteriaCR") is None else round(diag["criteriaCR"], 4),
        diag.get("criteriaStatus", ""),
        len(diag.get("transitivity", []) or []),
        json.dumps({k: (None if v is None else round(v, 4))
                    for k, v in blockcr.items()}, ensure_ascii=False),
        bad,
        payload.get("opinions", {}).get("missing", ""),
        payload.get("opinions", {}).get("constraint", ""),
        payload.get("opinions", {}).get("method", ""),
        json.dumps(payload, ensure_ascii=False),
    ]

    try:
        _tab(book, SHEET_RESPONSES, HEAD_RESPONSES).append_row(
            row, value_input_option="RAW")

        pw = [[ts, rid, rtype, r["part"], r["block"], r["left"], r["right"], r["value"]]
              for r in payload.get("pairwiseLong", [])]
        if pw:
            _tab(book, SHEET_PAIRWISE, HEAD_PAIRWISE).append_rows(
                pw, value_input_option="RAW")

        rt = [[ts, rid, rtype, c, v["name"], v["feas"], v["spill"]]
              for c, v in payload.get("ratings", {}).items()]
        if rt:
            _tab(book, SHEET_RATINGS, HEAD_RATINGS).append_rows(
                rt, value_input_option="RAW")
    except Exception as e:
        return False, f"시트 기록 실패 : {e}"

    return True, "응답이 정상적으로 접수되었습니다."
