# -*- coding: utf-8 -*-
"""시흥시 지역균형발전 기본계획 — 전문가 AHP 조사 웹폼

6개 분야 · 16개 전략 · 42개 핵심과제
평가기준 K1~K4
"""

import json
import uuid

import streamlit as st

from criteria import CRIT, SCALE, SCALE_HELP, CR_THRESHOLD
from hierdata import (
    FIELDS,
    GENERAL_TYPES,
    RESPONDENT_TYPES,
    FLAT,
    FIELD_GOAL,
    STRAT,
    blocks,
    block_stats,
    pairs,
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
.block-container {
    max-width: 960px;
    padding-top: 2rem;
    padding-bottom: 4rem;
}

.ahp-card {
    border-left: 4px solid #1b365d;
    padding: 0.2rem 0 0.2rem 0.9rem;
    margin-bottom: 0.55rem;
}

.ahp-qno {
    font-size: 0.82rem;
    font-weight: 600;
    color: #6b7280;
    margin-bottom: 0.3rem;
}

.ahp-pair {
    font-size: 1.02rem;
    font-weight: 700;
    line-height: 1.55;
    color: #111827;
}

.ahp-sep {
    color: #9ca3af;
    font-weight: 400;
    padding: 0 0.7rem;
}

.ahp-ends {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 0.9rem;
    font-weight: 600;
    color: #374151;
    margin-top: 0.3rem;
    margin-bottom: 0.12rem;
}

.ahp-score-grid {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 0.82rem;
    font-weight: 600;
    color: #4b5563;
    padding-left: 0;
    padding-right: 0;
    margin-top: 0.12rem;
    margin-bottom: -0.20rem;
}

.ahp-score-grid span {
    width: 0;
    display: flex;
    justify-content: center;
    white-space: nowrap;
}

[data-testid="stSliderThumbValue"] {
    display: none !important;
}

[data-testid="stSliderTickBar"] {
    display: none !important;
}

[data-testid="stSlider"] {
    padding-left: 0 !important;
    padding-right: 0 !important;
    padding-top: 0 !important;
    padding-bottom: 0 !important;
    margin-top: 0 !important;
    margin-bottom: -0.45rem !important;
}

.ahp-pick {
    font-size: 0.9rem;
    font-weight: 400;
    color: #8a9199;
    line-height: 1.2;
    margin-top: 0 !important;
    margin-bottom: 0.05rem;
}

.ahp-pick b {
    color: #6b7280;
    font-weight: 600;
}

/* ─────────────────────────────────────────────
   일관성 재확인 목록 공통
───────────────────────────────────────────── */

.recheck-wrap {
    margin-left: 1rem;
    margin-top: 0.2rem;
    margin-bottom: 0.4rem;
}

.recheck-title {
    font-size: 1rem;
    font-weight: 700;
    margin-top: 0.10rem;
    margin-bottom: 0.08rem;
}

.recheck-list {
    font-size: 0.92rem;
    font-weight: 400;
    line-height: 1.35;
    margin-top: 0;
    margin-bottom: 0.10rem;
}

.recheck-item {
    font-size: inherit;
    font-weight: 400;
    line-height: inherit;
    margin: 0;
    padding: 0;
}

.recheck-item b {
    font-weight: 600;
}

/* ─────────────────────────────────────────────
   판단 방향 재확인 목록
───────────────────────────────────────────── */

.trans-wrap {
    margin-left: 1rem;
    margin-top: 0.2rem;
    margin-bottom: 0.4rem;
}

.trans-title {
    font-size: 1rem;
    font-weight: 700;
    margin-top: 0.10rem;
    margin-bottom: 0.08rem;
}

.trans-list {
    font-size: 0.92rem;
    font-weight: 400;
    line-height: 1.35;
    margin-top: 0;
    margin-bottom: 0.10rem;
}

.trans-item {
    font-size: inherit;
    font-weight: 400;
    line-height: inherit;
    margin: 0;
    padding: 0;
}

.trans-bullet {
    font-weight: 600;
    color: #6b7280;
}

[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 12px;
}

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

for key, value in DEFAULTS.items():
    st.session_state.setdefault(key, value)


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
                saved_crit[qn],
                crit_labels[i],
                crit_labels[j],
            )

    field = st.session_state.get("meta", {}).get("field", "")
    saved_hier = st.session_state.get("hier", {})

    if field and field not in GENERAL_TYPES:
        for code, _title, _guide, items, labels in blocks(field):
            saved_vals = saved_hier.get(code, {}).get("values", [])

            for qn, (i, j) in enumerate(pairs(len(items))):
                if qn < len(saved_vals):
                    st.session_state[f"h_{field}_{code}_{i}_{j}"] = _label(
                        saved_vals[qn],
                        labels[i],
                        labels[j],
                    )

    for code, value in st.session_state.get("ratings", {}).items():
        if value.get("feas") is not None:
            st.session_state[f"feas_{code}"] = int(value["feas"])

        if value.get("spill") is not None:
            st.session_state[f"spill_{code}"] = int(value["spill"])

    opinions = st.session_state.get("opinions", {})
    if opinions:
        st.session_state["op_missing"] = opinions.get("missing", "")
        st.session_state["op_constraint"] = opinions.get("constraint", "")
        st.session_state["op_method"] = opinions.get("method", "")


def ahp_question(key, left, right, qno, qtot, default_value=1):
    with st.container(border=True):
        st.markdown(
            f'<div class="ahp-card">'
            f'<div class="ahp-qno">문항 {qno} / {qtot}</div>'
            f'<div class="ahp-pair">{left}'
            f'<span class="ahp-sep">—</span>{right}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        st.markdown(
            f'<div class="ahp-ends">'
            f'<span>← {left}</span>'
            f'<span>{right} →</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

        st.markdown(
            '<div class="ahp-score-grid">'
            '<span>9</span><span>7</span><span>5</span><span>3</span>'
            '<span>1</span>'
            '<span>3</span><span>5</span><span>7</span><span>9</span>'
            '</div>',
            unsafe_allow_html=True,
        )

        slider_labels = [_label(v, left, right) for v in SCALE]
        default_label = _label(default_value, left, right)

        if key not in st.session_state:
            st.session_state[key] = default_label

        picked = st.select_slider(
            " ",
            options=slider_labels,
            key=key,
            label_visibility="collapsed",
        )

        value = SCALE[slider_labels.index(picked)]

        if value == 1:
            msg = f"{left}와 {right}가 <b>동등하게 중요</b> · 1점"
        elif value > 0:
            msg = (
                f"{left}가 {right}보다 <b>더 중요</b> · "
                f"{value}점 · {SCALE_HELP[abs(value)]}"
            )
        else:
            msg = (
                f"{right}가 {left}보다 <b>더 중요</b> · "
                f"{abs(value)}점 · {SCALE_HELP[abs(value)]}"
            )

        st.markdown(
            f'<div class="ahp-pick">↳ {msg}</div>',
            unsafe_allow_html=True,
        )

    return value


def show_block_diag(title, values, labels, extra_transitivity=False):
    r = core.block_result(values, labels)

    if len(labels) <= 2:
        r["transitivity"] = []
        return r

    if r["status"] == "적정":
        st.success("✓ 비교 응답의 일관성이 적정합니다.")

    elif r["status"] == "재검토":
        cr_text = f"{r['cr']:.3f}" if r.get("cr") is not None else "-"

        st.markdown(
            (
                '<div style="'
                'background-color:#fff9db;'
                'border-radius:8px;'
                'padding:0.75rem 1rem;'
                'margin-bottom:0.8rem;'
                'color:#9a6700;'
                '">'
                f'<div style="font-size:1rem;font-weight:700;'
                f'margin-bottom:0.20rem;">'
                f'{title} · 응답 일관성 확인'
                f'</div>'
                f'<div style="font-size:0.90rem;font-weight:700;'
                f'margin-bottom:0.15rem;">'
                f'비교 강도 재확인 권장 | CR {cr_text}'
                f'</div>'
                f'<div style="font-size:0.82rem;font-weight:400;'
                f'line-height:1.3;">'
                f'아래 비교에서 중요도의 차이가 의도한 판단인지 확인해 주세요.'
                f'</div>'
                '</div>'
            ),
            unsafe_allow_html=True,
        )

        if r.get("worst"):
            pair_list = pairs(len(labels))
            check_lines = []

            for rank, (a, b) in enumerate(r["worst"], 1):
                ia = labels.index(a)
                ib = labels.index(b)

                if ia > ib:
                    ia, ib = ib, ia
                    a, b = b, a

                pair_index = pair_list.index((ia, ib))
                value = values[pair_index]

                if value == 1:
                    result_text = "동등 · 1점"
                elif value > 0:
                    result_text = f"왼쪽 항목이 {abs(value)}점 중요"
                else:
                    result_text = f"오른쪽 항목이 {abs(value)}점 중요"

                check_lines.append(
                    f'<div class="recheck-item">'
                    f'• {a} ↔ {b} '
                    f'<b>({result_text})</b>'
                    f'</div>'
                )

            st.markdown(
                '<div class="recheck-wrap">'
                '<div class="recheck-title">우선 확인할 비교</div>'
                '<div class="recheck-list">'
                + ''.join(check_lines)
                + '</div>'
                '</div>',
                unsafe_allow_html=True,
            )

        st.caption(
            "※ 현재 응답이 본인의 판단을 정확히 반영한 것이라면 "
            "CR을 낮추기 위해 임의로 수정할 필요는 없습니다."
        )

    else:
        st.info(r.get("message", ""))

    if extra_transitivity and len(labels) >= 3:
        viol, total = core.transitivity_violations(values, labels)
        r["transitivity"] = [list(v) for v in viol]

        if viol:
            st.error(
                f"**판단 방향 재확인 필요 | {len(viol)}건**\n\n"
                "항목 간 중요도 판단의 방향이 서로 맞지 않습니다. "
                "아래 비교를 다시 확인해 주세요."
            )

            trans_lines = []

            for a, b, c in viol:
                trans_lines.append(
                    f'<div class="trans-item">'
                    f'<span class="trans-bullet">•</span> '
                    f'{a} &gt; {b}'
                    f'</div>'
                )

                trans_lines.append(
                    f'<div class="trans-item">'
                    f'<span class="trans-bullet">•</span> '
                    f'{b} &gt; {c}'
                    f'</div>'
                )

                trans_lines.append(
                    f'<div class="recheck-item" '
                    f'style="margin-bottom:0.45rem;">'
                    f'• <b>그런데 {a} ≤ {c}</b>'
                    f'</div>'
                )

            st.markdown(
                '<div class="recheck-wrap">'
                '<div class="recheck-title">판단 방향 재확인</div>'
                '<div class="recheck-list">'
                + ''.join(trans_lines)
                + '</div>'
                '</div>',
                unsafe_allow_html=True,
            )

            st.markdown(
                '<div style="'
                'color:#d32f2f;'
                'font-size:0.98rem;'
                'font-weight:700;'
                'margin-top:0.25rem;'
                'margin-left:1rem;'
                'margin-bottom:0.3rem;'
                '">'
                '⚠ 판단 방향의 모순을 수정해야 다음 단계로 진행할 수 있습니다.'
                '</div>',
                unsafe_allow_html=True,
            )
            
        else:
            st.success("✓ 중요도 판단 방향이 일관됩니다.")
    else:
        r.setdefault("transitivity", [])

    return r


st.title("시흥시 지역균형발전 기본계획")

st.caption(
    "우선순위사업 선정 전문가 AHP 조사 · "
    f"6개 분야 · 16개 전략 · {len(TASKS)}개 핵심과제 · 평가기준 4개"
)

st.progress(
    {
        1: 0.06,
        2: 0.30,
        3: 0.58,
        4: 0.80,
        5: 1.0,
    }.get(st.session_state.page, 0.0)
)


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
- **3. 실행가능성·파급효과 평가:** 핵심과제의 실행 가능성과 파급 효과를 **5점 척도**로 평가합니다.

**[쌍대비교 방법]** 제시된 두 항목 중 어느 항목이 더 중요한지 판단하고, 얼마나 더 중요한지를 선택해 주십시오.

**[일관성 검토]** 일관성비율(CR)이 0.10을 초과하면 화면에서 재검토 문항을 안내합니다.

**[응답 소요시간]** 약 **25~35분**
"""
        )

    c1, c2 = st.columns(2)

    with c1:
        name = st.text_input(
            "성명 *",
            value=st.session_state.meta.get("name", ""),
        )
        org = st.text_input(
            "소속 *",
            value=st.session_state.meta.get("org", ""),
        )

    with c2:
        prev = st.session_state.meta.get("field", RESPONDENT_TYPES[0])

        field = st.selectbox(
            "소관 분야 *",
            RESPONDENT_TYPES,
            index=RESPONDENT_TYPES.index(prev) if prev in RESPONDENT_TYPES else 0,
            help="해당하는 소관 분야를 선택해 주십시오.",
        )

        careers = [
            "5년 미만",
            "5~10년",
            "10~15년",
            "15~20년",
            "20년 이상",
        ]

        prev_career = st.session_state.meta.get("career", careers[0])

        career = st.selectbox(
            "관련 분야 경력",
            careers,
            index=careers.index(prev_career) if prev_career in careers else 0,
        )

    if field in GENERAL_TYPES:
        st.info(
            f"**{field}** 응답자는 평가기준의 상대적 중요도 평가에 참여합니다."
        )
    else:
        nb, nq = block_stats(field)

        flat_note = (
            " · 전략층을 두지 않는 평면화 분야"
            if field in FLAT
            else ""
        )

        st.info(
            f"**{field}** — 분야 목표 「{FIELD_GOAL[field]}」\n\n"
            f"쌍대비교 {nb}블록 {nq}문항{flat_note} · "
            f"5점 척도 {len(tasks_of(field))}개 핵심과제 평가"
        )

    with st.expander("이전 응답 이어서 하기"):
        st.markdown(
            "이전에 **응답 임시저장**으로 내려받은 파일을 선택해 주세요. "
            "임시저장 파일은 보통 컴퓨터의 **다운로드 폴더**에 있습니다."
        )

        uploaded = st.file_uploader(
            "다운로드 폴더에서 임시저장 파일 선택",
            type=["json"],
            accept_multiple_files=False,
        )

        if uploaded is not None and st.button(
            "이전 응답 불러오기",
            width="stretch",
        ):
            try:
                data = json.loads(uploaded.read().decode("utf-8"))

                for key in (
                    "meta",
                    "crit_vals",
                    "hier",
                    "ratings",
                    "opinions",
                    "response_id",
                ):
                    if key in data:
                        st.session_state[key] = data[key]

                _restore_widget_states()

                st.success(
                    "이전 응답을 불러왔습니다. "
                    "아래 '조사 시작' 버튼을 눌러 이어서 진행해 주세요."
                )
                st.rerun()

            except Exception as exc:
                st.error(f"응답 파일을 읽지 못했습니다 : {exc}")

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


elif st.session_state.page == 2:
    st.header(
        f"평가기준 간 상대적 중요도 ({len(CRIT_PAIRS)}문항)"
    )

    st.write(
        "지역균형발전 핵심과제의 우선순위를 판단할 때, "
        "**각 평가기준을 어느 정도 중요하게 고려해야 하는지** 평가해 주십시오."
    )

    with st.expander("평가기준 4개 보기", expanded=True):
        for code, name, question, _src in CRIT:
            st.markdown(f"**{code} {name}** — {question}")

    st.info(
        "평가방법 : 두 기준을 비교하여 **어느 기준이 더 중요한지**와 "
        "**그 중요도의 정도**를 선택해 주십시오. "
        "두 기준이 비슷하게 중요하면 **'동등(1)'**을 선택합니다.\n\n"
        "**척도 :** 1 동등 · 3 약간 더 중요 · 5 뚜렷하게 더 중요 · "
        "7 매우 더 중요 · 9 절대적으로 더 중요"
    )

    labels = [
        f"{code} {name}"
        for code, name, _q, _s in CRIT
    ]

    saved_vals = st.session_state.get("crit_vals", [])
    vals = []

    for qn, (i, j) in enumerate(CRIT_PAIRS, 1):
        default_val = (
            saved_vals[qn - 1]
            if qn - 1 < len(saved_vals)
            else 1
        )

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

    st.session_state.crit_vals = vals

    st.session_state.crit_diag = show_block_diag(
        "평가기준",
        vals,
        labels,
        extra_transitivity=True,
    )

    trans_viol = st.session_state.crit_diag.get("transitivity", [])

    st.write("")

    st.caption(
        "※ 일관성비율(CR)이 0.10을 초과한 경우에는 중요도 차이를 다시 확인해 주십시오."
    )

    st.write("")

    c1, c2 = st.columns(2)

    with c1:
        if st.button(
            "← 이전",
            width="stretch",
        ):
            go(1)

    with c2:
        next_page = 5 if is_general() else 3
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
                go(next_page)


elif st.session_state.page == 3:
    if is_general():
        go(5)

    field = rtype()
    nb, nq = block_stats(field)
    field_blocks = list(blocks(field))

    st.header(f"{field} 분야 전략·핵심과제 중요도")
    st.caption(f"{nb}개 비교블록 · {nq}문항")

    st.info(
        f"**분야 목표**  \n"
        f"{FIELD_GOAL[field]}"
    )

    with st.expander(
        f"{field} 분야 전략·핵심과제 전체 보기",
        expanded=True,
    ):
        st.caption(
            "평가에 앞서 해당 분야의 전략과 핵심과제 전체 구성을 확인해 주십시오."
        )

        if field not in FLAT:
            for strategy_no, (
                _strategy_code,
                strategy_name,
                task_codes,
            ) in enumerate(
                STRAT[field],
                1,
            ):
                st.markdown(
                    f"**전략 {strategy_no}. {strategy_name}**"
                )

                task_lines = [
                    f"- {TASKS[task_code][1]}"
                    for task_code in task_codes
                ]

                st.markdown("\n".join(task_lines))

                if strategy_no < len(STRAT[field]):
                    st.write("")

        else:
            st.markdown("**평가대상 핵심과제**")
            task_lines = []

            for _strategy_code, _strategy_name, task_codes in STRAT[field]:
                for task_code in task_codes:
                    task_lines.append(
                        f"- {TASKS[task_code][1]}"
                    )

            st.markdown("\n".join(task_lines))

    st.warning(
        "**평가방법**  \n\n"
        "제시된 두 항목 중 **균형발전 목표 달성에 더 중요한 항목**을 먼저 판단하고, "
        "그 중요도의 정도를 선택해 주십시오. "
        "두 항목이 비슷하게 중요하다고 판단되면 **동등(1)**을 선택해 주십시오.  \n\n"
        "※ 이 단계에서는 **상대적 중요도만 평가**합니다. "
        "실행 가능성과 파급·연계 효과는 다음 단계에서 별도로 평가합니다."
    )

    if field in FLAT:
        st.info(
            "이 분야는 전략 수와 핵심과제 수를 고려하여 "
            "전략 단계를 별도로 비교하지 않고 "
            "분야 내 핵심과제를 직접 비교합니다."
        )

    saved_hier = st.session_state.get("hier", {})
    hier = {}
    page3_trans_violations = []

    for block_no, (
        code,
        title,
        guide,
        items,
        labels,
    ) in enumerate(
        field_blocks,
        1,
    ):
        st.write("")

        if code == "STRAT":
            st.subheader(
                f"{block_no}. {field} 분야 전략 비교"
            )

        elif code == "FLAT":
            st.subheader(
                f"{block_no}. {field} 분야 핵심과제 비교"
            )

        else:
            strategy_no = None
            strategy_name = title.split(" — ")[0]

            for idx, (
                strategy_code,
                current_name,
                _task_codes,
            ) in enumerate(
                STRAT[field],
                1,
            ):
                if strategy_code == code:
                    strategy_no = idx
                    strategy_name = current_name
                    break

            st.subheader(
                f"{block_no}. [전략 {strategy_no}] {strategy_name}"
            )

        st.caption(guide)

        prs = pairs(len(items))

        saved_vals = saved_hier.get(
            code,
            {},
        ).get(
            "values",
            [],
        )

        vals = []

        for qn, (i, j) in enumerate(prs, 1):
            default_val = (
                saved_vals[qn - 1]
                if qn - 1 < len(saved_vals)
                else 1
            )

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

        diag = show_block_diag(
            title,
            vals,
            labels,
            extra_transitivity=True,
        )

        if diag.get("transitivity"):
            page3_trans_violations.append(
                {
                    "code": code,
                    "title": title,
                    "violations": diag["transitivity"],
                }
            )

        hier[code] = {
            "title": title,
            "items": items,
            "labels": labels,
            "values": vals,
            "diag": diag,
        }

    st.session_state.hier = hier

    st.write("")

    c1, c2 = st.columns(2)

    with c1:
        if st.button(
            "← 이전",
            width="stretch",
        ):
            go(2)

    with c2:
        if page3_trans_violations:
            st.button(
                "다음 : 실행가능성·파급효과 평가 →",
                type="primary",
                width="stretch",
                disabled=True,
            )
        else:
            if st.button(
                "다음 : 실행가능성·파급효과 평가 →",
                type="primary",
                width="stretch",
            ):
                go(4)


elif st.session_state.page == 4:
    if is_general():
        go(5)

    field = rtype()
    codes = tasks_of(field)

    st.header(
        f"{field} 핵심과제 실행가능성·파급효과 평가"
    )

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
    ratings = {}
    missing = []

    for code in codes:
        _field, name, description, _strategy_no, _task_no = TASKS[code]
        saved = saved_ratings.get(code, {})

        if (
            f"feas_{code}" not in st.session_state
            and saved.get("feas") is not None
        ):
            st.session_state[f"feas_{code}"] = int(saved["feas"])

        if (
            f"spill_{code}" not in st.session_state
            and saved.get("spill") is not None
        ):
            st.session_state[f"spill_{code}"] = int(saved["spill"])

        with st.container(border=True):
            st.markdown(f"**{name}**")
            st.caption(description)

            c1, c2 = st.columns(2)

            with c1:
                feas = st.radio(
                    "실행 가능성",
                    [1, 2, 3, 4, 5],
                    horizontal=True,
                    index=None,
                    key=f"feas_{code}",
                )

            with c2:
                spill = st.radio(
                    "파급·연계 효과",
                    [1, 2, 3, 4, 5],
                    horizontal=True,
                    index=None,
                    key=f"spill_{code}",
                )

        if feas is None or spill is None:
            missing.append(code)

        ratings[code] = {
            "name": name,
            "feas": feas,
            "spill": spill,
        }

    st.session_state.ratings = ratings

    done = [
        value
        for value in ratings.values()
        if (
            value["feas"] is not None
            and value["spill"] is not None
        )
    ]

    if done:
        average = (
            sum(
                value["feas"] + value["spill"]
                for value in done
            )
            / (2 * len(done))
        )

        if len(done) == len(codes) and average >= 4.5:
            st.warning(
                f"전체 평정 평균이 {average:.2f}로 높습니다. "
                "과제 간 차이가 충분히 반영되었는지 한 번 더 확인해 주십시오."
            )

    if missing:
        st.info(
            f"아직 응답하지 않은 과제 {len(missing)}개 : "
            f"{', '.join(missing)}"
        )

    c1, c2 = st.columns(2)

    with c1:
        if st.button(
            "← 이전",
            width="stretch",
        ):
            go(3)

    with c2:
        if st.button(
            "최종 검토 →",
            type="primary",
            width="stretch",
        ):
            if missing:
                st.error(
                    "모든 과제에 실행 가능성과 파급·연계 효과를 모두 응답해 주십시오."
                )
            else:
                go(5)


elif st.session_state.page == 5:
    meta = st.session_state.meta

    st.header("응답 검토 및 제출")

    st.write(
        f"**{meta.get('name', '')}** · "
        f"{meta.get('org', '')} · "
        f"{meta.get('field', '')} · "
        f"경력 {meta.get('career', '')}"
    )

    criteria_diag = st.session_state.crit_diag or {}

    rows = [
        {
            "평가영역": "평가기준 중요도",
            "항목수": criteria_diag.get("n", "-"),
            "CR": (
                "-"
                if criteria_diag.get("cr") is None
                else f"{criteria_diag['cr']:.3f}"
            ),
            "판정": criteria_diag.get("status", "-"),
        }
    ]

    for code, block in st.session_state.hier.items():
        diag = block["diag"]

        rows.append(
            {
                "평가영역": block["title"],
                "항목수": diag.get("n", len(block["items"])),
                "CR": (
                    "-"
                    if diag.get("cr") is None
                    else f"{diag['cr']:.3f}"
                ),
                "판정": diag.get("status", "해당없음"),
            }
        )

    st.dataframe(
        rows,
        width="stretch",
        hide_index=True,
    )

    criteria_viol = criteria_diag.get("transitivity", []) or []

    hierarchy_viol_count = sum(
        len(block["diag"].get("transitivity", []) or [])
        for block in st.session_state.hier.values()
    )

    bad = [
        row
        for row in rows
        if row["판정"] == "재검토"
    ]

    if bad:
        st.warning(
            f"CR이 {CR_THRESHOLD:.2f}를 초과한 비교블록이 {len(bad)}개 있습니다. "
            "제출은 가능하지만 이전 단계에서 응답을 다시 확인하는 것을 권합니다."
        )

    if criteria_viol or hierarchy_viol_count:
        st.error(
            "판단 방향이 서로 맞지 않는 응답이 남아 있습니다. "
            "이전 단계에서 해당 비교를 다시 확인해 주십시오."
        )

    if not bad and not criteria_viol and hierarchy_viol_count == 0:
        st.success(
            "일관성 검정이 가능한 모든 비교블록이 기준을 충족했습니다."
        )

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
        "missing": op1,
        "constraint": op2,
        "method": op3,
    }

    pairwise_long = []

    for (i, j), value in zip(
        CRIT_PAIRS,
        st.session_state.crit_vals,
    ):
        pairwise_long.append(
            {
                "part": "criteria",
                "block": "CRIT",
                "left": CRIT[i][0],
                "right": CRIT[j][0],
                "value": value,
            }
        )

    for code, block in st.session_state.hier.items():
        for (i, j), value in zip(
            pairs(len(block["items"])),
            block["values"],
        ):
            pairwise_long.append(
                {
                    "part": "hierarchy",
                    "block": code,
                    "left": block["items"][i],
                    "right": block["items"][j],
                    "value": value,
                }
            )

    payload = {
        "responseId": st.session_state.response_id,
        "schema": "siheung-ahp-2026-09",
        "meta": meta,
        "criteria": {
            "pairs": [
                [CRIT[i][0], CRIT[j][0]]
                for i, j in CRIT_PAIRS
            ],
            "values": st.session_state.crit_vals,
            "weights": criteria_diag.get("weights"),
        },
        "hierarchy": {
            code: {
                "items": block["items"],
                "values": block["values"],
                "weights": block["diag"].get("weights"),
            }
            for code, block in st.session_state.hier.items()
        },
        "ratings": st.session_state.ratings,
        "pairwiseLong": pairwise_long,
        "opinions": st.session_state.opinions,
        "diagnostics": {
            "criteriaCR": criteria_diag.get("cr"),
            "criteriaStatus": criteria_diag.get("status"),
            "transitivity": criteria_viol,
            "blockCR": {
                code: block["diag"].get("cr")
                for code, block in st.session_state.hier.items()
            },
            "hierarchyTransitivity": {
                code: block["diag"].get("transitivity", [])
                for code, block in st.session_state.hier.items()
            },
        },
        "submittedAt": storage.now_kst(),
    }

    json_text = json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
    )

    if st.session_state.submitted:
        st.success(st.session_state.submit_msg)
        st.caption(
            f"접수번호 {st.session_state.response_id} · "
            "응답이 제출되었습니다. 감사합니다."
        )

    else:
        c1, c2 = st.columns([1, 2])

        with c1:
            if st.button(
                "← 응답 수정",
                width="stretch",
            ):
                go(2 if is_general() else 4)

        with c2:
            if st.button(
                "최종 제출",
                type="primary",
                width="stretch",
                disabled=bool(
                    criteria_viol
                    or hierarchy_viol_count
                ),
            ):
                ok, message = storage.save(payload)

                st.session_state.submitted = ok
                st.session_state.submit_msg = message

                if ok:
                    st.rerun()
                else:
                    st.error(
                        f"온라인 접수에 실패했습니다 — {message}"
                    )

                    st.info(
                        "아래 '응답 파일 내려받기'를 눌러 저장한 뒤 담당자에게 보내 주십시오. "
                        "응답은 유실되지 않습니다."
                    )

    st.download_button(
        "응답 파일 내려받기",
        data=json_text.encode("utf-8"),
        file_name=(
            f"AHP_{meta.get('field', '')}_"
            f"{st.session_state.response_id}.json"
        ),
        mime="application/json",
        width="stretch",
    )


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

        answered = sum(
            len(block.get("values", []))
            for block in st.session_state.hier.values()
        )

        st.write(
            f"전략·핵심과제 중요도 "
            f"{answered}/{nq}문항"
        )

        done = sum(
            1
            for value in st.session_state.ratings.values()
            if (
                value.get("feas") is not None
                and value.get("spill") is not None
            )
        )

        st.write(
            f"실행가능성·파급효과 평가 "
            f"{done}/{len(tasks_of(rtype()))}과제"
        )

    st.divider()

    temp_hier = {
        code: {
            key: value
            for key, value in block.items()
            if key != "diag"
        }
        for code, block in st.session_state.hier.items()
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
            temp_data,
            ensure_ascii=False,
            indent=2,
        ).encode("utf-8"),
        file_name=(
            f"시흥시_AHP_임시저장_"
            f"{st.session_state.response_id}.json"
        ),
        mime="application/json",
        width="stretch",
    )

    st.caption(
        "설문을 중단해야 하는 경우 현재 응답을 저장해 두었다가, "
        "다음 접속 시 첫 화면의 '이전 응답 이어서 하기'에서 불러올 수 있습니다."
    )

    st.divider()

    st.caption(
        "문의 : 시흥시정연구원 김주영 연구위원\n\n"
        "031-317-0141"
    )
