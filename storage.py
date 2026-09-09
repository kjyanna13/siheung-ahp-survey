# -*- coding: utf-8 -*-
"""응답 저장 — Google Apps Script 웹앱으로 전송"""

from datetime import datetime, timezone, timedelta

import requests
import streamlit as st


KST = timezone(timedelta(hours=9))


def now_kst():
    return datetime.now(KST).isoformat(timespec="seconds")


def is_configured():
    try:
        return bool(st.secrets["apps_script"]["url"])
    except Exception:
        return False


def save(payload):
    """
    Google Apps Script 웹앱으로 응답을 전송합니다.
    반환값: (성공여부, 메시지)
    """

    try:
        url = st.secrets["apps_script"]["url"]

    except Exception:
        return (
            False,
            "Streamlit Secrets에 apps_script.url이 설정되어 있지 않습니다.",
        )

    try:
        response = requests.post(
            url,
            json=payload,
            timeout=30,
        )

    except Exception as e:
        return (
            False,
            f"응답 전송 실패 : {e}",
        )

    if response.status_code != 200:
        return (
            False,
            f"웹앱 응답 오류 : HTTP {response.status_code}",
        )

    try:
        result = response.json()

    except Exception:
        return (
            False,
            "웹앱 응답을 해석하지 못했습니다.",
        )

    if result.get("ok"):
        return (
            True,
            result.get(
                "message",
                "응답이 정상적으로 접수되었습니다.",
            ),
        )

    return (
        False,
        result.get(
            "message",
            "응답 저장 중 오류가 발생했습니다.",
        ),
    )
