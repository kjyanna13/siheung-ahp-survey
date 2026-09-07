# -*- coding: utf-8 -*-
"""
시흥시 지역균형발전 기본계획 - 전문가 AHP 조사 웹폼
로컬 테스트용 Streamlit 앱

실행:
    python -m streamlit run app.py

주의:
- 로컬 실행 시 제출 결과는 responses/ 폴더에 JSON으로 저장됩니다.
- Streamlit Community Cloud에 배포할 때는 로컬 파일 저장을 영구 저장소로 쓰면 안 됩니다.
  실제 배포 전에는 Google Sheets / Supabase 등 외부 저장소 연결을 권장합니다.
"""

import json
import math
import os
from datetime import datetime
from pathlib import Path

import numpy as np
import streamlit as st

from hierdata import FIELDS, blocks, pairs
from taskdata import TASKS


# -----------------------------------------------------------------------------
# 기본 설정
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="시흥시 지역균형발전 전문가 AHP 조사",
    page_icon="📊",
    layout="centered",
)

CRIT = [
    ("K1", "정책적 중요도", "균형발전 목표 달성에 대한 기여"),
    ("K2", "주민 체감·수요", "통장 수요조사에서 나타난 현장 시급성"),
    ("K3", "격차 완화 기여도", "생활권 간·지역 간 격차 완화에 대한 기여 정도"),
    ("K4", "실행 가능성", "재원·권한·기간과 소관 부서의 수용 가능성"),
    ("K5", "파급·연계 효과", "다른 분야·생활권으로의 확산과 사업 간 연계"),
]

RI = {1: 0.00, 2: 0.00, 3: 0.58, 4: 0.90, 5: 1.12,
      6: 1.24, 7: 1.32, 8: 1.41, 9: 1.45, 10: 1.49}

# 화면은 1·3·5·7·9만 보여주고 내부에는 signed integer로 저장
SCALE = [-9, -7, -5, -3, 1, 3, 5, 7, 9]


# 화면 가독성 개선
st.markdown("""
<style>
.block-container {max-width: 980px; padding-top: 2rem; padding-bottom: 4rem;}
h1 {font-size: 2.15rem !important;}
h2 {font-size: 1.55rem !important;}
h3 {font-size: 1.2rem !important;}
div[data-testid="stCaptionContainer"] {font-size: .92rem;}
.ahp-question {
 border: 1px solid #e5e7eb; border-radius: 12px;
 padding: 1rem 1.1rem .6rem; margin: .8rem 0 .5rem;
 background: #fafafa;
}
.ahp-qno {font-size:.9rem; font-weight:700; margin-bottom:.35rem;}
.ahp-pair {font-size:1.05rem; font-weight:650; line-height:1.55;}
.ahp-guide {font-size:.84rem; color:#6b7280; margin-top:.3rem;}
</style>
""", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# AHP 계산 함수
# -----------------------------------------------------------------------------
def matrix_from_signed(values, n):
    """signed AHP 값(-9..-3, 1, 3..9)을 reciprocal matrix로 변환"""
    A = np.ones((n, n), dtype=float)
    for (i, j), v in zip(pairs(n), values):
        r = float(abs(v))
        A[i, j] = r if v >= 0 else 1.0 / r
        A[j, i] = 1.0 / A[i, j]
    return A


def priority(A):
    """주고유벡터와 CR 산출. n<=2는 CR 검정 불가(None)."""
    vals, vecs = np.linalg.eig(A)
    k = int(np.argmax(vals.real))
    lmax = float(vals[k].real)
    w = np.abs(vecs[:, k].real)
    w = w / w.sum()
    n = A.shape[0]
    ci = (lmax - n) / (n - 1) if n > 1 else 0.0
    cr = ci / RI[n] if n > 2 and RI.get(n, 0) > 0 else None
    return w, cr


def inconsistency_scores(A, w, labels):
    """전체 가중치 관계와 가장 괴리가 큰 쌍을 재검토 후보로 제시."""
    out = []
    n = len(labels)
    for i, j in pairs(n):
        observed = A[i, j]
        expected = w[i] / w[j]
        score = abs(math.log(observed) - math.log(expected))
        out.append((score, labels[i], labels[j]))
    return sorted(out, key=lambda x: x[0], reverse=True)


def cr_status(cr):
    if cr is None:
        return "검정 제외", "비교항목이 2개인 경우 CR 검정 대상이 아닙니다."
    if cr <= 0.10:
        return "적정", f"CR = {cr:.3f} · 일관성 기준을 충족합니다."
    return "재검토", f"CR = {cr:.3f} · 일부 판단의 재검토를 권고합니다."


def label_for_value(v, left, right):
    if v == 1:
        return "동등 1"
    if v > 0:
        return f"{left} {v}"
    return f"{right} {abs(v)}"


def ahp_question(key, left, right, help_text=None):
    """한 개의 쌍대비교 입력. signed integer 반환."""
    labels = [label_for_value(v, left, right) for v in SCALE]
    # 가운데(동등 1)를 초기값으로 둠
    selected = st.select_slider(
        f"{left} ↔ {right}",
        options=labels,
        value="동등 1",
        key=key,
        help=help_text,
    )
    return SCALE[labels.index(selected)]


def show_cr_box(title, values, labels):
    """블록의 CR 및 재검토 후보 표시. (weights, cr) 반환"""
    A = matrix_from_signed(values, len(labels))
    w, cr = priority(A)
    status, message = cr_status(cr)

    st.markdown(f"**{title} · 일관성 점검**")
    if status == "적정":
        st.success(message)
    elif status == "재검토":
        st.warning(message)
        bad = inconsistency_scores(A, w, labels)[:3]
        if bad:
            st.caption("전체 판단구조와의 괴리가 큰 비교항목입니다. 반드시 틀렸다는 의미는 아니며 우선 재검토할 문항입니다.")
            for idx, (_score, a, b) in enumerate(bad, 1):
                st.write(f"{idx}. {a} ↔ {b}")
    else:
        st.info(message)
    return w, cr


# -----------------------------------------------------------------------------
# 세션 상태 초기화
# -----------------------------------------------------------------------------
if "page" not in st.session_state:
    st.session_state.page = 1
if "meta" not in st.session_state:
    st.session_state.meta = {}
if "criteria_values" not in st.session_state:
    st.session_state.criteria_values = []
if "hier_values" not in st.session_state:
    st.session_state.hier_values = []
if "block_cr" not in st.session_state:
    st.session_state.block_cr = {}
if "ratings" not in st.session_state:
    st.session_state.ratings = {}


def go(page):
    st.session_state.page = page
    st.rerun()


# -----------------------------------------------------------------------------
# 공통 헤더
# -----------------------------------------------------------------------------
st.title("시흥시 지역균형발전 기본계획")
st.subheader("전문가 AHP 조사")
st.caption("AHP 쌍대비교 → 일관성(CR) 확인 → 분야별 과제 비교 → 실행가능성·파급효과 평정")

progress = {1: 0.05, 2: 0.28, 3: 0.55, 4: 0.78, 5: 1.0}[st.session_state.page]
st.progress(progress)


# -----------------------------------------------------------------------------
# PAGE 1. 응답자 정보
# -----------------------------------------------------------------------------
if st.session_state.page == 1:
    st.header("1. 응답자 정보")
    st.write("본 조사는 지역균형발전 핵심과제의 우선순위 도출을 위한 전문가 조사입니다.")

    c1, c2 = st.columns(2)
    with c1:
        name = st.text_input("전문가 ID 또는 성명", value=st.session_state.meta.get("name", ""))
        org = st.text_input("소속", value=st.session_state.meta.get("org", ""))
    with c2:
        default_field = st.session_state.meta.get("field", FIELDS[0])
        field = st.selectbox("전문분야", FIELDS, index=FIELDS.index(default_field))
        careers = ["5년 미만", "5~10년 미만", "10~15년 미만", "15~20년 미만", "20년 이상"]
        old_career = st.session_state.meta.get("career", careers[0])
        career = st.selectbox("관련 분야 경력", careers, index=careers.index(old_career))

    st.info("전문분야를 기준으로 다음 단계에서 해당 분야의 전략·핵심과제만 제시됩니다.")

    if st.button("조사 시작", type="primary", use_container_width=True):
        if not name.strip():
            st.error("전문가 ID 또는 성명을 입력해 주세요.")
        else:
            st.session_state.meta = {
                "name": name.strip(),
                "org": org.strip(),
                "field": field,
                "career": career,
                "group": "",
            }
            go(2)


# -----------------------------------------------------------------------------
# PAGE 2. K1~K5 평가기준 쌍대비교
# -----------------------------------------------------------------------------
elif st.session_state.page == 2:
    st.header("2. 사업 우선순위 평가기준의 중요도")
    st.write("두 기준을 비교하여 **어느 기준이 더 중요하며, 그 정도가 어느 수준인지** 선택해 주십시오.")
    st.info("선택 기준: 1=동등 · 3=약간 중요 · 5=중요 · 7=매우 중요 · 9=절대적으로 중요")

    with st.expander("평가기준 설명", expanded=True):
        for code, name, desc in CRIT:
            st.markdown(f"**{code} {name}** · {desc}")

    vals = []
    crit_pairs = pairs(len(CRIT))
    for qn, (i, j) in enumerate(crit_pairs, 1):
        left = f"{CRIT[i][0]} {CRIT[i][1]}"
        right = f"{CRIT[j][0]} {CRIT[j][1]}"
        st.markdown(
            f"""<div class="ahp-question">
            <div class="ahp-qno">문항 {qn} / {len(crit_pairs)}</div>
            <div class="ahp-pair">{left} ↔ {right}</div>
            <div class="ahp-guide">가운데는 동등(1)입니다. 더 중요하다고 판단하는 기준 쪽으로 이동해 주십시오.</div>
            </div>""",
            unsafe_allow_html=True,
        )
        vals.append(ahp_question(f"crit_{i}_{j}", left, right))

    labels = [f"{c} {n}" for c, n, _ in CRIT]
    w, cr = show_cr_box("평가기준", vals, labels)
    st.session_state.criteria_values = vals
    st.session_state.criteria_cr = cr
    st.session_state.criteria_weights = [float(x) for x in w]

    c1, c2 = st.columns(2)
    with c1:
        if st.button("← 이전", use_container_width=True):
            go(1)
    with c2:
        if st.button("다음 →", type="primary", use_container_width=True):
            go(3)


# -----------------------------------------------------------------------------
# PAGE 3. 분야별 계층 AHP
# -----------------------------------------------------------------------------
elif st.session_state.page == 3:
    field = st.session_state.meta["field"]
    st.header(f"3. {field} 분야 전략·핵심과제 중요도")
    st.write("각 비교블록별로 두 항목의 상대적 중요도를 판단해 주십시오.")

    all_vals = []
    block_cr = {}
    for bidx, (code, title, items, raw_labels) in enumerate(blocks(field), 1):
        st.subheader(f"3-{bidx}. {title}")
        # 전략 블록은 전략명, 과제 블록은 공식 과제명 표시
        if code == "STRAT":
            labels = raw_labels
        else:
            labels = [TASKS[t][1] for t in items]

        block_vals = []
        for qn, (i, j) in enumerate(pairs(len(items)), 1):
            left = labels[i]
            right = labels[j]
            block_vals.append(
                ahp_question(f"hier_{field}_{code}_{i}_{j}", left, right)
            )
        _, cr = show_cr_box(title, block_vals, labels)
        block_cr[code] = cr
        all_vals.extend(block_vals)
        st.divider()

    st.session_state.hier_values = all_vals
    st.session_state.block_cr = block_cr

    c1, c2 = st.columns(2)
    with c1:
        if st.button("← 이전", use_container_width=True):
            go(2)
    with c2:
        if st.button("다음 →", type="primary", use_container_width=True):
            go(4)


# -----------------------------------------------------------------------------
# PAGE 4. 과제별 평정
# -----------------------------------------------------------------------------
elif st.session_state.page == 4:
    field = st.session_state.meta["field"]
    st.header(f"4. {field} 분야 핵심과제 평정")
    st.write("각 핵심과제의 실행 가능성과 파급·연계 효과를 5점 척도로 평가해 주십시오.")
    st.caption("1=매우 낮음, 2=낮음, 3=보통, 4=높음, 5=매우 높음")

    task_codes = [t for _c, _n, ts in __import__('hierdata').STRAT[field] for t in ts]
    ratings = {}
    for t in task_codes:
        name = TASKS[t][1]
        with st.container(border=True):
            st.markdown(f"**{name}**")
            c1, c2 = st.columns(2)
            with c1:
                feas = st.radio(
                    "실행 가능성",
                    [1, 2, 3, 4, 5],
                    horizontal=True,
                    key=f"feas_{t}",
                )
            with c2:
                spill = st.radio(
                    "파급·연계 효과",
                    [1, 2, 3, 4, 5],
                    horizontal=True,
                    key=f"spill_{t}",
                )
            ratings[t] = {"feas": int(feas), "spill": int(spill)}

    st.session_state.ratings = ratings

    c1, c2 = st.columns(2)
    with c1:
        if st.button("← 이전", use_container_width=True):
            go(3)
    with c2:
        if st.button("최종 검토 →", type="primary", use_container_width=True):
            go(5)


# -----------------------------------------------------------------------------
# PAGE 5. 검토 및 제출
# -----------------------------------------------------------------------------
elif st.session_state.page == 5:
    st.header("5. 응답 최종 검토 및 제출")
    meta = st.session_state.meta
    st.write(f"**응답자:** {meta['name']}  ·  **분야:** {meta['field']}  ·  **경력:** {meta['career']}")

    rows = []
    ccr = st.session_state.get("criteria_cr")
    rows.append({
        "평가영역": "평가기준(K1~K5)",
        "CR": "-" if ccr is None else f"{ccr:.3f}",
        "판정": cr_status(ccr)[0],
    })
    for code, cr in st.session_state.block_cr.items():
        rows.append({
            "평가영역": code,
            "CR": "-" if cr is None else f"{cr:.3f}",
            "판정": cr_status(cr)[0],
        })
    st.dataframe(rows, use_container_width=True, hide_index=True)

    bad = [r for r in rows if r["판정"] == "재검토"]
    if bad:
        st.warning("CR이 0.10을 초과한 비교블록이 있습니다. 제출은 가능하지만, 이전 단계로 돌아가 응답을 다시 확인하는 것을 권고합니다.")
    else:
        st.success("CR 검정이 가능한 모든 비교블록이 기준을 충족했습니다.")

    submitted_at = datetime.now().astimezone().isoformat(timespec="seconds")
    payload = {
        "meta": meta,
        "pairwise": st.session_state.criteria_values,
        "hierarchy": st.session_state.hier_values,
        "ratings": st.session_state.ratings,
        "diagnostics": {
            "criteriaCR": ccr,
            "blockCR": st.session_state.block_cr,
        },
        "submittedAt": submitted_at,
    }
    json_text = json.dumps(payload, ensure_ascii=False, indent=2)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("← 응답 수정", use_container_width=True):
            go(4)
    with c2:
        if st.button("최종 제출", type="primary", use_container_width=True):
            outdir = Path("responses")
            outdir.mkdir(exist_ok=True)
            safe_name = "".join(ch for ch in meta["name"] if ch.isalnum() or ch in "-_ ").strip().replace(" ", "_") or "expert"
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = outdir / f"{safe_name}_{meta['field']}_{ts}.json"
            path.write_text(json_text, encoding="utf-8")
            st.session_state.saved_path = str(path)
            st.success(f"응답이 저장되었습니다. ({path})")

    st.download_button(
        "응답 JSON 내려받기",
        data=json_text.encode("utf-8"),
        file_name=f"AHP_{meta['name']}_{meta['field']}.json",
        mime="application/json",
        use_container_width=True,
    )

    st.caption("현재 버전은 로컬 테스트용입니다. 실제 인터넷 배포 전에는 응답을 Google Sheets 또는 데이터베이스에 영구 저장하도록 연결하는 것을 권장합니다.")
