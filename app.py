# -*- coding: utf-8 -*-
"""시흥시 지역균형발전 기본계획 — 전문가 AHP 조사 웹폼

6개 분야 · 16개 전략 · 42개 핵심과제 (2026-09-08 최종 보고서 기준)
평가기준 K1~K4
"""
import json
import uuid
import streamlit as st

from criteria import CRIT, SCALE, SCALE_HELP, CR_THRESHOLD
from hierdata import (
    FIELDS, GENERAL_TYPES, RESPONDENT_TYPES, FLAT,
    FIELD_GOAL, STRAT, blocks, block_stats, pairs,
)
from taskdata import TASKS, tasks_of
import ahpcore as core
import storage

st.set_page_config(
    page_title="시흥시 지역균형발전 전문가 AHP 조사",
    page_icon="📊",
    layout="centered",
)

CRIT_PAIRS = pairs(len(CRIT))

st.markdown(
    """
<style>

/* ─────────────────────────────────────────────
   전체 화면
───────────────────────────────────────────── */

.block-container {
    max-width: 960px;
    padding-top: 2rem;
    padding-bottom: 4rem;
}


/* ─────────────────────────────────────────────
   AHP 문항 카드
───────────────────────────────────────────── */

.ahp-card {
    border-left: 4px solid #1b365d;
    padding: 0.2rem 0 0.2rem 0.9rem;
    margin-bottom: 0.7rem;
}


/* 문항 번호 */

.ahp-qno {
    font-size: 0.82rem;
    font-weight: 600;
    color: #6b7280;
    margin-bottom: 0.35rem;
}


/* 비교하는 두 항목 */

.ahp-pair {
    font-size: 1.02rem;
    font-weight: 700;
    line-height: 1.6;
    color: #111827;
}


/* 두 항목 사이 구분선 */

.ahp-sep {
    color: #9ca3af;
    font-weight: 400;
    padding: 0 0.7rem;
}


/* ─────────────────────────────────────────────
   슬라이더 좌우 항목
───────────────────────────────────────────── */

.ahp-ends {
    display: flex;
    justify-content: space-between;
    align-items: center;

    font-size: 0.9rem;
    font-weight: 600;
    color: #374151;

    margin-top: 0.4rem;
    margin-bottom: 0.25rem;
}


/* ─────────────────────────────────────────────
   9 · 7 · 5 · 3 · 1 · 3 · 5 · 7 · 9
───────────────────────────────────────────── */

.ahp-score-grid {
    display: grid;
    grid-template-columns: repeat(9, 1fr);
    text-align: center;

    font-size: 0.82rem;
    font-weight: 600;
    color: #4b5563;

    padding-left: 0.75rem;
    padding-right: 0.75rem;

    margin-top: 0.35rem;
    margin-bottom: -0.4rem;
}

/* ─────────────────────────────────────────────
   Streamlit 슬라이더
───────────────────────────────────────────── */

[data-testid="stSliderThumbValue"] {
    display: none !important;
}

[data-testid="stSliderTickBar"] {
    display: none !important;
}

[data-testid="stSlider"] {
    padding-left: 0.75rem;
    padding-right: 0.75rem;
    padding-top: 0.05rem;
    padding-bottom: 0 !important;
    margin-bottom: -0.35rem !important;
}

.ahp-pick {
    font-size: 0.9rem;
    font-weight: 400;
    color: #8a9199;
    line-height: 1.4;
    margin-top: 0 !important;
    margin-bottom: 0.05rem;
}

.ahp-pick b {
    color: #6b7280;
    font-weight: 600;
}

/* ─────────────────────────────────────────────
   선택 결과
───────────────────────────────────────────── */

.ahp-pick {
    font-size: 0.9rem;
    font-weight: 400;

    color: #8a9199;

    line-height: 1.6;

    margin-top: 0.75rem;
    margin-bottom: 0.15rem;
}


/* 선택 결과의 굵은 글씨도 회색 */

.ahp-pick b {
    color: #6b7280;
    font-weight: 600;
}


/* ─────────────────────────────────────────────
   Streamlit 테두리 컨테이너
   한 문항 전체를 하나의 블록으로 표시
───────────────────────────────────────────── */

[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 12px;
}


/* ─────────────────────────────────────────────
   모바일 화면
───────────────────────────────────────────── */

@media (max-width: 700px) {

    .block-container {
        padding-left: 1rem;
        padding-right: 1rem;
    }

    .ahp-pair {
        font-size: 0.95rem;
    }

    .ahp-ends {
        font-size: 0.8rem;
    }

    .ahp-score-grid {
        font-size: 0.76rem;
    }

    .ahp-pick {
        font-size: 0.84rem;
    }
}

</style>
""",
    unsafe_allow_html=True,
)

DEFAULTS = {
    "page": 1,
    "meta": {},
    "response_id": uuid.uuid4().hex[:12],
    "crit_vals": [],
    "crit_diag": {},
    "hier": {},
    "ratings": {},
    "opinions": {},
    "submitted": False,
    "submit_msg": "",
}
for k, v in DEFAULTS.items():
    st.session_state.setdefault(k, v)

def go(page):
    st.session_state.page = page
    st.rerun()

def rtype():
    return st.session_state.meta.get("field", "")

def is_general():
    return rtype() in GENERAL_TYPES

def _label(v, left, right):
    if v == 1:
        return "동등 1"
    return f"{left} {v}" if v > 0 else f"{right} {abs(v)}"

def _restore_widget_states():
    crit_labels = [f"{c} {n}" for c, n, _q, _s in CRIT]
    saved_crit = st.session_state.get("crit_vals", [])
    for qn, (i, j) in enumerate(CRIT_PAIRS):
        if qn < len(saved_crit):
            st.session_state[f"crit_{i}_{j}"] = _label(
                saved_crit[qn], crit_labels[i], crit_labels[j]
            )

    field = st.session_state.get("meta", {}).get("field", "")
    saved_hier = st.session_state.get("hier", {})
    if field and field not in GENERAL_TYPES:
        for code, _title, _guide, items, labels in blocks(field):
            vals = saved_hier.get(code, {}).get("values", [])
            for qn, (i, j) in enumerate(pairs(len(items))):
                if qn < len(vals):
                    st.session_state[f"h_{field}_{code}_{i}_{j}"] = _label(
                        vals[qn], labels[i], labels[j]
                    )

    for c, v in st.session_state.get("ratings", {}).items():
        if v.get("feas") is not None:
            st.session_state[f"feas_{c}"] = int(v["feas"])
        if v.get("spill") is not None:
            st.session_state[f"spill_{c}"] = int(v["spill"])

    opinions = st.session_state.get("opinions", {})
    if opinions:
        st.session_state["op_missing"] = opinions.get("missing", "")
        st.session_state["op_constraint"] = opinions.get("constraint", "")
        st.session_state["op_method"] = opinions.get("method", "")

def ahp_question(
    key,
    left,
    right,
    qno,
    qtot,
    default_value=1,
):

    with st.container(border=True):

        # ── 문항 번호 + 비교 항목 ──────────────────────────
        st.markdown(
            f'<div class="ahp-card">'
            f'<div class="ahp-qno">'
            f'문항 {qno} / {qtot}'
            f'</div>'
            f'<div class="ahp-pair">'
            f'{left}'
            f'<span class="ahp-sep">—</span>'
            f'{right}'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # ── 좌우 비교 기준 ─────────────────────────────────
        st.markdown(
            f'<div class="ahp-ends">'
            f'<span>← {left}</span>'
            f'<span>{right} →</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # ── 척도 숫자 ──────────────────────────────────────
        st.markdown(
            '<div class="ahp-score-grid">'
            '<span>9</span>'
            '<span>7</span>'
            '<span>5</span>'
            '<span>3</span>'
            '<span>1</span>'
            '<span>3</span>'
            '<span>5</span>'
            '<span>7</span>'
            '<span>9</span>'
            '</div>',
            unsafe_allow_html=True,
        )

        # ── 슬라이더 선택지 ────────────────────────────────
        labels = [
            _label(v, left, right)
            for v in SCALE
        ]

        default_label = _label(
            default_value,
            left,
            right,
        )

        if key not in st.session_state:
            st.session_state[key] = default_label

        picked = st.select_slider(
            " ",
            options=labels,
            key=key,
            label_visibility="collapsed",
        )

        v = SCALE[
            labels.index(picked)
        ]

        # ── 선택 결과 ──────────────────────────────────────
        if v == 1:
            msg = (
                f"{left}와 {right}가 "
                f"<b>동등하게 중요</b> · 1점"
            )

        elif v > 0:
            msg = (
                f"{left}가 {right}보다 "
                f"<b>더 중요</b> · "
                f"{v}점 · {SCALE_HELP[abs(v)]}"
            )

        else:
            msg = (
                f"{right}가 {left}보다 "
                f"<b>더 중요</b> · "
                f"{abs(v)}점 · {SCALE_HELP[abs(v)]}"
            )

        st.markdown(
            f'<div class="ahp-pick">'
            f'↳ {msg}'
            f'</div>',
            unsafe_allow_html=True,
        )

    return v

def show_block_diag(title, values, labels, extra_transitivity=False):

    # 비교항목이 2개인 경우 일관성 검사를 표시하지 않음
    if len(labels) <= 2:
        return {
            "n": len(labels),
            "status": "해당없음",
            "cr": None,
            "weights": None,
            "worst": [],
            "extreme": False,
            "transitivity": [],
        }

    r = core.block_result(values, labels)

    # ── 1. 일관성비율(CR) 확인 ──────────────────────────────
    if r["status"] == "적정":
        st.success(
            "✓ 비교 응답의 일관성이 적정합니다."
        )

    elif r["status"] == "재검토":
        cr_text = (
            f"{r['cr']:.3f}"
            if r.get("cr") is not None
            else "-"
        )

        st.warning(
            f"**{title} · 응답 일관성 확인**\n\n"
            f"**비교 강도 재확인 권장 | CR {cr_text}**\n\n"
            "아래 비교에서 중요도의 차이(3·5·7·9)가 "
            "의도한 판단인지 확인해 주세요."
        )

        if r.get("worst"):
            st.markdown("**우선 확인할 비교**")

            pair_list = pairs(
                len(labels)
            )

            for rank, (a, b) in enumerate(
                r["worst"],
                1,
            ):
                ia = labels.index(a)
                ib = labels.index(b)

                if ia > ib:
                    ia, ib = ib, ia
                    a, b = b, a

                pair_index = pair_list.index(
                    (ia, ib)
                )

                value = values[pair_index]

                if value == 1:
                    result_text = "동등 · 1점"

                elif value > 0:
                    result_text = (
                        f"왼쪽 항목이 {abs(value)}점 중요"
                    )

                else:
                    result_text = (
                        f"오른쪽 항목이 {abs(value)}점 중요"
                    )

                st.markdown(
                    f"{rank}. {a} ↔ {b} "
                    f"**({result_text})**"
                )

        st.caption(
            "※ 현재 응답이 본인의 판단을 정확히 반영한 것이라면 "
            "CR을 낮추기 위해 억지로 수정할 필요는 없습니다."
        )
    else:
        st.info(
            r["message"]
        )

    # ── 2. 판단 방향(전이성) 확인 ───────────────────────────
    if extra_transitivity and len(labels) >= 3:
        viol, tot = core.transitivity_violations(
            values,
            labels,
        )

        r["transitivity"] = [
            list(v)
            for v in viol
        ]

        st.write("")

        if viol:
            st.error(
                f"**판단 방향 재확인 필요 | {len(viol)}건**\n\n"
                "항목 간 중요도 판단의 방향이 서로 맞지 않습니다. "
                "아래 비교를 다시 확인해 주세요."
            )

            for idx, (a, b, c) in enumerate(viol, 1):
                st.markdown(
                    f"#### {idx}. {a} · {b} · {c}"
                )

                st.markdown(
                    f"- **{a} > {b}**\n"
                    f"- **{b} > {c}**\n"
                    f"- 그런데 **{a} ≤ {c}**"
                )

                st.info(
                    f"→ 「{a} ↔ {b}」, "
                    f"「{b} ↔ {c}」, "
                    f"「{a} ↔ {c}」를 다시 확인해 주세요."
                )

                st.write("")

            st.warning(
                "판단 방향의 모순을 수정하면 "
                "다음 단계로 진행할 수 있습니다."
            )

        else:
            st.success(
                "✓ 중요도 판단 방향이 일관됩니다."
            )

    return r


st.title("시흥시 지역균형발전 기본계획")
st.caption(
    "우선순위사업 선정 전문가 AHP 조사 · "
    f"6개 분야 · 16개 전략 · {len(TASKS)}개 핵심과제 · 평가기준 4개"
)
st.progress({1:0.06, 2:0.30, 3:0.58, 4:0.80, 5:1.0}.get(st.session_state.page, 0.0))

# 1. 응답자 정보
if st.session_state.page == 1:
    st.header("응답자 정보")
    st.write(
        "본 조사는 「시흥시 균형발전 기본계획」의 42개 핵심과제 가운데 "
        "계획기간 중 우선 추진할 13개 과제를 선정하기 위한 근거를 마련하는 조사입니다."
    )

    with st.container(border=True):
        st.markdown("**응답 안내**")
        st.markdown(
            f"""
- **1. 평가기준 중요도:** 평가기준의 상대적 중요도를 **쌍대비교** 방식으로 평가합니다. *(총 {len(CRIT_PAIRS)}문항)*
- **2. 전략·핵심과제 중요도:** 분야별 전략 및 핵심과제의 상대적 중요도를 **쌍대비교** 방식으로 평가합니다.
- **3. 실행가능성·파급효과 평가:** 핵심과제의 실행 가능성과 파급 효과를 **5점 척도**로 평가합니다. \n\n
 **[쌍대비교 방법]** 제시된 두 항목 중 어느 항목이 더 중요한지 먼저 판단하고, 얼마나 더 중요한지를 선택해 주십시오. \n\n
 **[일관성 검토]** 비율(CR)이 0.10을 초과하면 화면에서 **재검토 문항**으로 안내하오니 재선택해 주십시오. \n\n
 **[응답 소요시간]** 약 **25~35분** 예상
"""
        )

    c1, c2 = st.columns(2)
    with c1:
        name = st.text_input("성명 *", value=st.session_state.meta.get("name", ""))
        org = st.text_input("소속 *", value=st.session_state.meta.get("org", ""))

    with c2:
        prev = st.session_state.meta.get("field", RESPONDENT_TYPES[0])
        field = st.selectbox(
            "소관 분야 *",
            RESPONDENT_TYPES,
            index=RESPONDENT_TYPES.index(prev) if prev in RESPONDENT_TYPES else 0,
            help="해당하는 소관 분야를 선택해 주십시오.",
        )
        careers = ["5년 미만", "5~10년", "10~15년", "15~20년", "20년 이상"]
        pc = st.session_state.meta.get("career", careers[0])
        career = st.selectbox(
            "관련 분야 경력",
            careers,
            index=careers.index(pc) if pc in careers else 0,
        )

    if field in GENERAL_TYPES:
        st.info(f"**{field}** 응답자는 평가기준의 상대적 중요도 평가에 참여합니다.")
    else:
        nb, nq = block_stats(field)
        flat = " · 전략층을 두지 않는 평면화 분야" if field in FLAT else ""
        st.info(
            f"**{field}** — 분야 목표 「{FIELD_GOAL[field]}」\n\n"
            f"쌍대비교 {nb}블록 {nq}문항{flat} · "
            f"5점 척도 {len(tasks_of(field))}개 핵심과제 평가"
        )

# ── 이전 응답 이어서 하기 ─────────────────────────────
    with st.expander("이전 응답 이어서 하기"):
        st.markdown(
            "이전에 **응답 임시저장**으로 내려받은 파일을 선택해 주세요. "
            "임시저장 파일은 보통 컴퓨터의 **다운로드 폴더**에 있습니다."
        )

        up = st.file_uploader(
            "다운로드 폴더에서 임시저장 파일 선택",
            type=["json"],
            accept_multiple_files=False,
        )

        if up is not None and st.button(
            "이전 응답 불러오기",
            width="stretch",
        ):
            try:
                data = json.loads(up.read().decode("utf-8"))

                for k in (
                    "meta",
                    "crit_vals",
                    "hier",
                    "ratings",
                    "opinions",
                    "response_id",
                ):
                    if k in data:
                        st.session_state[k] = data[k]

                _restore_widget_states()

                st.success(
                    "이전 응답을 불러왔습니다. "
                    "아래 '조사 시작' 버튼을 눌러 이어서 진행해 주세요."
                )
                st.rerun()

            except Exception as e:
                st.error(f"응답 파일을 읽지 못했습니다 : {e}")

    # ── 조사 시작 ──────────────────────────────────────────
    if st.button(
        "조사 시작",
        type="primary",
        width="stretch",
    ):
        if not name.strip():
            st.error("성명을 입력해 주십시오.")

        elif not org.strip():
            st.error("소속을 입력해 주십시오.")

        else:
            old_field = st.session_state.meta.get("field", "")

            # 소관 분야가 변경된 경우 이전 분야 응답 초기화
            if old_field and old_field != field:
                st.session_state.hier = {}
                st.session_state.ratings = {}

                for key in list(st.session_state.keys()):
                    if (
                        key.startswith("h_")
                        or key.startswith("feas_")
                        or key.startswith("spill_")
                    ):
                        del st.session_state[key]

            st.session_state.meta = {
                "name": name.strip(),
                "org": org.strip(),
                "field": field,
                "career": career,
            }

            go(2)



# 2. 평가기준 중요도
elif st.session_state.page == 2:
    st.header(f"평가기준 간 상대적 중요도 ({len(CRIT_PAIRS)}문항)")
    st.write(
        "지역균형발전 핵심과제의 우선순위를 판단할 때, "
        "**각 평가기준을 어느 정도 중요하게 고려해야 하는지** 평가해 주십시오."
    )

    with st.expander("평가기준 4개 보기", expanded=True):
        for code, nm, qq, _src in CRIT:
            st.markdown(f"**{code} {nm}** — {qq}")

    st.info(
        "평가방법 : 두 기준을 비교하여 **어느 기준이 더 중요한지**와 "
        "**그 중요도의 정도**를 선택해 주십시오. "
        "두 기준이 비슷하게 중요하면 **'동등(1)'**을 선택합니다.\n\n"
        "**척도 :** 1 동등 · 3 약간 더 중요 · 5 뚜렷하게 더 중요 · "
        "7 매우 더 중요 · 9 절대적으로 더 중요"
    )

    labels = [f"{c} {n}" for c, n, _q, _s in CRIT]
    saved_vals = st.session_state.get("crit_vals", [])
    vals = []

    for qn, (i, j) in enumerate(CRIT_PAIRS, 1):
        default_val = saved_vals[qn-1] if qn-1 < len(saved_vals) else 1
        vals.append(
            ahp_question(
                f"crit_{i}_{j}",
                labels[i],
                labels[j],
                qn,
                len(CRIT_PAIRS),
                default_value=default_val,
            )
        )

        
    # ── 현재 응답 저장 ──────────────────────────────────────
    st.session_state.crit_vals = vals

    # ── 응답 일관성 확인 ────────────────────────────────────
    st.session_state.crit_diag = show_block_diag(
        "평가기준",
        vals,
        labels,
        extra_transitivity=True,
    )

    trans_viol = st.session_state.crit_diag.get(
        "transitivity",
        [],
    )

    st.write("")

    st.caption(
        "※ 일관성비율(CR)이 0.10을 초과한 경우에는 "
        "중요도 차이의 재확인을 권장합니다. "
        "판단 방향이 서로 맞지 않는 경우에는 해당 비교를 수정해야 "
        "다음 단계로 진행할 수 있습니다."
    )

    st.write("")

    # ── 이전 / 다음 버튼 ────────────────────────────────────
    c1, c2 = st.columns(2)

    with c1:
        if st.button(
            "← 이전",
            width="stretch",
        ):
            go(1)

    with c2:
        nxt = 5 if is_general() else 3

        next_label = (
            "최종 검토 →"
            if is_general()
            else "다음 : 전략·핵심과제 중요도 →"
        )

        if trans_viol:
            st.button(
                next_label,
                type="primary",
                width="stretch",
                disabled=True,
            )

        else:
            if st.button(
                next_label,
                type="primary",
                width="stretch",
            ):
                go(nxt)

# 3. 전략·핵심과제 중요도
elif st.session_state.page == 3:
    if is_general():
        go(5)

    field = rtype()
    nb, nq = block_stats(field)
    field_blocks = list(blocks(field))

    # ── 제목 ──────────────────────────────────────────────
    st.header(f"{field} 분야 전략·핵심과제 중요도")

    st.caption(
        f"{nb}개 비교블록 · {nq}문항"
    )

    # ── 분야 목표 ─────────────────────────────────────────
    st.info(
        f"**분야 목표**  \n"
        f"{FIELD_GOAL[field]}"
    )

    # ── 평가대상 전체 구조 ────────────────────────────────
    with st.expander(
        f"{field} 분야 전략·핵심과제 전체 보기",
        expanded=True,
    ):
        st.caption(
            "평가에 앞서 해당 분야의 전략과 핵심과제 전체 구성을 확인해 주십시오."
        )

        # 일반 계층형 분야
        if field not in FLAT:
            for si, (strat_code, strat_name, task_codes) in enumerate(
                STRAT[field],
                1,
            ):
                st.markdown(
                    f"**전략 {si}. {strat_name}**"
                )

                task_lines = []

                for task_code in task_codes:
                    task_name = TASKS[task_code][1]
                    task_lines.append(
                        f"- {task_name}"
                    )

                st.markdown(
                    "\n".join(task_lines)
                )

                if si < len(STRAT[field]):
                    st.write("")

        # 평면화 분야
        else:
            st.markdown(
                "**평가대상 핵심과제**"
            )

            task_lines = []

            for strat_code, strat_name, task_codes in STRAT[field]:
                for task_code in task_codes:
                    task_name = TASKS[task_code][1]

                    task_lines.append(
                        f"- {task_name}"
                    )

            st.markdown(
                "\n".join(task_lines)
            )
    # ── 평가방법 ──────────────────────────────────────────
    st.warning(
        "**평가방법**  \n\n"
        "제시된 두 항목 중 **균형발전 목표 달성에 더 중요한 항목**을 먼저 판단하고, "
        "그 중요도의 정도를 선택해 주십시오. "
        "두 항목이 비슷하게 중요하다고 판단되면 **동등(1)**을 선택해 주십시오.  \n\n"
        "※ 이 단계에서는 **상대적 중요도만 평가**합니다. "
        "실행 가능성과 파급·연계 효과는 다음 단계에서 별도로 평가합니다."
    )

    # ── 평면화 분야 안내 ───────────────────────────────────
    if field in FLAT:
        st.info(
            "이 분야는 전략 수와 핵심과제 수를 고려하여 "
            "전략 단계를 별도로 비교하지 않고 "
            "분야 내 핵심과제를 직접 비교합니다."
        )

    # ── 기존 응답 불러오기 ────────────────────────────────
    saved_hier = st.session_state.get(
        "hier",
        {},
    )

    hier = {}

    # ── 실제 쌍대비교 ─────────────────────────────────────
    for bi, (code, title, guide, items, labels) in enumerate(
        field_blocks,
        1,
    ):
        st.write("")

        if code == "STRAT":
            st.subheader(
                f"{bi}. {field} 분야 전략 비교"
            )

        elif code == "FLAT":
            st.subheader(
                f"{bi}. {field} 분야 핵심과제 비교"
            )

        else:
            # 해당 전략의 순번과 전략명 찾기
            strategy_no = None
            strategy_name = title.split(" — ")[0]

            for si, (strat_code, strat_name, task_codes) in enumerate(
                STRAT[field],
                1,
            ):
                if strat_code == code:
                    strategy_no = si
                    strategy_name = strat_name
                    break

            st.subheader(
                f"{bi}. [전략 {strategy_no}] {strategy_name}"
            )

        st.caption(
            guide
        )

        prs = pairs(
            len(items)
        )
        
        saved_vals = saved_hier.get(
            code,
            {},
        ).get(
            "values",
            [],
        )

        vals = []

        for qn, (i, j) in enumerate(
            prs,
            1,
        ):
            default_val = (
                saved_vals[qn - 1]
                if qn - 1 < len(saved_vals)
                else 1
            )

            # 전략 간 비교일 때 전략 번호 표시
            if code == "STRAT":
                left_display = f"전략 {i + 1} {labels[i]}"
                right_display = f"전략 {j + 1} {labels[j]}"
            else:
                left_display = labels[i]
                right_display = labels[j]

            vals.append(
                ahp_question(
                    f"h_{field}_{code}_{i}_{j}",
                    left_display,
                    right_display,
                    qn,
                    len(prs),
                    default_value=default_val,
                )
            )
        # ── 일관성 확인 ───────────────────────────────────
        diag = show_block_diag(
            title,
            vals,
            labels,
        )

        hier[code] = {
            "title": title,
            "items": items,
            "labels": labels,
            "values": vals,
            "diag": diag,
        }

    # ── 응답 저장 ─────────────────────────────────────────
    st.session_state.hier = hier

    # ── 이전 / 다음 ───────────────────────────────────────
    st.write("")

    c1, c2 = st.columns(2)

    with c1:
        if st.button(
            "← 이전",
            width="stretch",
        ):
            go(2)

    with c2:
        if st.button(
            "다음 : 실행가능성·파급효과 평가 →",
            type="primary",
            width="stretch",
        ):
            go(4)

# 4. 실행가능성·파급효과 평가
elif st.session_state.page == 4:
    if is_general():
        go(5)

    field = rtype()
    codes = tasks_of(field)
    st.header(f"{field} 핵심과제 실행가능성·파급효과 평가")
    st.write(
        "각 핵심과제의 **실행 가능성**과 **파급·연계 효과**를 "
        "각각 5점 척도로 평가해 주십시오."
    )

    with st.container(border=True):
        st.markdown(
            """
- **실행 가능성** — 예산·인력·부지·제도 여건을 고려할 때 계획기간(5년) 내 착수 가능한 정도  
  1 매우 낮음 · 2 낮음 · 3 보통 · 4 높음 · 5 매우 높음
- **파급·연계 효과** — 사업 성과가 다른 분야 또는 다른 생활권으로 확산되는 정도  
  1 매우 낮음 · 2 낮음 · 3 보통 · 4 높음 · 5 매우 높음
"""
        )

    saved_ratings = st.session_state.get("ratings", {})
    ratings, missing = {}, []

    for c in codes:
        _f, nm, desc, _s, _t = TASKS[c]
        saved = saved_ratings.get(c, {})

        if f"feas_{c}" not in st.session_state and saved.get("feas") is not None:
            st.session_state[f"feas_{c}"] = int(saved["feas"])
        if f"spill_{c}" not in st.session_state and saved.get("spill") is not None:
            st.session_state[f"spill_{c}"] = int(saved["spill"])

        with st.container(border=True):
            st.markdown(f"**{c}　{nm}**")
            st.caption(desc)
            c1, c2 = st.columns(2)
            with c1:
                feas = st.radio(
                    "실행 가능성",
                    [1,2,3,4,5],
                    horizontal=True,
                    index=None,
                    key=f"feas_{c}",
                )
            with c2:
                spill = st.radio(
                    "파급·연계 효과",
                    [1,2,3,4,5],
                    horizontal=True,
                    index=None,
                    key=f"spill_{c}",
                )

        if feas is None or spill is None:
            missing.append(c)
        ratings[c] = {"name": nm, "feas": feas, "spill": spill}

    st.session_state.ratings = ratings

    done = [
        v for v in ratings.values()
        if v["feas"] is not None and v["spill"] is not None
    ]
    if done:
        avg = sum(v["feas"] + v["spill"] for v in done) / (2 * len(done))
        if len(done) == len(codes) and avg >= 4.5:
            st.warning(
                f"전체 평정 평균이 {avg:.2f}로 높습니다. "
                "과제 간 차이가 충분히 반영되었는지 한 번 더 확인해 주십시오."
            )

    if missing:
        st.info(f"아직 응답하지 않은 과제 {len(missing)}개 : {', '.join(missing)}")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("← 이전", width="stretch"):
            go(3)
    with c2:
        if st.button("최종 검토 →", type="primary", width="stretch"):
            if missing:
                st.error("모든 과제에 실행 가능성과 파급·연계 효과를 모두 응답해 주십시오.")
            else:
                go(5)

# 5. 검토 및 제출
elif st.session_state.page == 5:
    meta = st.session_state.meta
    st.header("응답 검토 및 제출")
    st.write(
        f"**{meta.get('name','')}** · {meta.get('org','')} · "
        f"{meta.get('field','')} · 경력 {meta.get('career','')}"
    )

    cd = st.session_state.crit_diag or {}
    rows = [{
        "평가영역": "평가기준 중요도",
        "항목수": cd.get("n", "-"),
        "CR": "-" if cd.get("cr") is None else f"{cd['cr']:.3f}",
        "판정": cd.get("status", "-"),
    }]

    for code, b in st.session_state.hier.items():
        d = b["diag"]

        rows.append({
            "평가영역": b["title"],
            "항목수": d.get("n", len(b["items"])),
            "CR": "-" if d.get("cr") is None else f"{d['cr']:.3f}",
            "판정": d.get("status", "해당없음"),
        })

    st.dataframe(rows, width="stretch", hide_index=True)

    viol = cd.get("transitivity", []) or []
    bad = [r for r in rows if r["판정"] == "재검토"]

    if bad:
        st.warning(
            f"CR이 {CR_THRESHOLD:.2f}를 초과한 비교블록이 {len(bad)}개 있습니다. "
            "제출은 가능하지만 이전 단계에서 응답을 다시 확인하는 것을 권합니다."
        )
    if viol:
        st.warning(
            f"평가기준 비교에서 전이성 위반 {len(viol)}건이 있습니다. "
            "응답 방향을 한 번 더 확인해 주십시오."
        )
    if not bad and not viol:
        st.success("일관성 검정이 가능한 모든 비교블록이 기준을 충족했습니다.")

    st.subheader("자유 의견")
    op1 = st.text_area(
        f"1. {len(TASKS)}개 핵심과제 외에 우선순위에 포함되어야 한다고 보시는 과제가 있습니까?",
        key="op_missing",
    )
    op2 = st.text_area(
        "2. 특정 과제의 실행에 큰 제약이 있다면, 그 과제와 제약 요인을 적어 주십시오.",
        key="op_constraint",
    )
    op3 = st.text_area(
        "3. 평가기준·분석방법에 대한 의견이 있으면 적어 주십시오.",
        key="op_method",
    )
    st.session_state.opinions = {
        "missing": op1, "constraint": op2, "method": op3
    }

    pw_long = []
    for (i, j), v in zip(CRIT_PAIRS, st.session_state.crit_vals):
        pw_long.append({
            "part":"criteria", "block":"CRIT",
            "left":CRIT[i][0], "right":CRIT[j][0], "value":v,
        })

    for code, b in st.session_state.hier.items():
        for (i, j), v in zip(pairs(len(b["items"])), b["values"]):
            pw_long.append({
                "part":"hierarchy", "block":code,
                "left":b["items"][i], "right":b["items"][j], "value":v,
            })

    payload = {
        "responseId": st.session_state.response_id,
        "schema": "siheung-ahp-2026-09",
        "meta": meta,
        "criteria": {
            "pairs": [[CRIT[i][0], CRIT[j][0]] for i,j in CRIT_PAIRS],
            "values": st.session_state.crit_vals,
            "weights": cd.get("weights"),
        },
        "hierarchy": {
            c: {
                "items":b["items"],
                "values":b["values"],
                "weights": b["diag"].get("weights"),
            }
            for c,b in st.session_state.hier.items()
        },
        "ratings": st.session_state.ratings,
        "pairwiseLong": pw_long,
        "opinions": st.session_state.opinions,
        "diagnostics": {
            "criteriaCR": cd.get("cr"),
            "criteriaStatus": cd.get("status"),
            "transitivity": viol,
            "blockCR": {
                c:b["diag"]["cr"] for c,b in st.session_state.hier.items()
            },
        },
        "submittedAt": storage.now_kst(),
    }
    jtxt = json.dumps(payload, ensure_ascii=False, indent=2)


    
    if st.session_state.submitted:
        st.success(st.session_state.submit_msg)
        st.caption(
            f"접수번호 {st.session_state.response_id} · 응답이 제출되었습니다. 감사합니다."
        )
    else:
        c1, c2 = st.columns([1,2])
        with c1:
            if st.button("← 응답 수정", width="stretch"):
                go(2 if is_general() else 4)
        with c2:
            if st.button("최종 제출", type="primary", width="stretch"):
                ok, msg = storage.save(payload)
                st.session_state.submitted = ok
                st.session_state.submit_msg = msg
                if ok:
                    st.rerun()
                else:
                    st.error(f"온라인 접수에 실패했습니다 — {msg}")
                    st.info(
                        "아래 '응답 파일 내려받기'를 눌러 저장한 뒤 담당자에게 보내 주십시오. "
                        "응답은 유실되지 않습니다."
                    )

    st.download_button(
        "응답 파일 내려받기",
        data=jtxt.encode("utf-8"),
        file_name=f"AHP_{meta.get('field','')}_{st.session_state.response_id}.json",
        mime="application/json",
        width="stretch",
    )

# 사이드바
with st.sidebar:
    st.markdown("### 진행 상황")
    st.caption(f"접수번호 {st.session_state.response_id}")

    if rtype():
        st.write(f"**소관 분야:** {rtype()}")

    st.write(
        f"평가기준 중요도 "
        f"{len(st.session_state.crit_vals)}/{len(CRIT_PAIRS)}문항"
    )

    if not is_general() and rtype():
        _nb, nq = block_stats(rtype())
        ans = sum(
            len(b.get("values", []))
            for b in st.session_state.hier.values()
        )
        st.write(f"전략·핵심과제 중요도 {ans}/{nq}문항")

        done = sum(
            1 for v in st.session_state.ratings.values()
            if v.get("feas") is not None and v.get("spill") is not None
        )
        st.write(
            f"실행가능성·파급효과 평가 "
            f"{done}/{len(tasks_of(rtype()))}과제"
        )



    temp_hier = {
        c: {k:v for k,v in b.items() if k != "diag"}
        for c,b in st.session_state.hier.items()
    }
    temp_data = {
        "meta": st.session_state.meta,
        "response_id": st.session_state.response_id,
        "crit_vals": st.session_state.crit_vals,
        "hier": temp_hier,
        "ratings": st.session_state.ratings,
        "opinions": st.session_state.opinions,
    }

    st.download_button(
        "응답 임시저장",
        data=json.dumps(
            temp_data, ensure_ascii=False, indent=2
        ).encode("utf-8"),
        file_name=f"시흥시_AHP_임시저장_{st.session_state.response_id}.json",
        mime="application/json",
        width="stretch",
    )
    st.caption(
        "설문을 중단해야 하는 경우 현재 응답을 저장해 두었다가, "
        "다음 접속 시 첫 화면의 '이전 응답 이어서 하기'에서 불러올 수 있습니다."
    )


    st.caption(
        "문의 : 시흥시정연구원 김주영 연구위원\n\n"
        "031-317-0141"
    )
