# -*- coding: utf-8 -*-
"""시흥시 지역균형발전 기본계획 — 전문가 AHP 조사 웹폼

6개 분야 · 16개 전략 · 42개 핵심과제 (2026-09-08 보고서 기준)
평가기준 K1~K4 (2026-09-07 제3차 개정)

배포 : https://siheung-ahp-survey.streamlit.app/
실행 : python -m streamlit run app.py
"""
import json
import uuid

import streamlit as st

from criteria import CRIT, SCALE, SCALE_HELP, CR_THRESHOLD
from hierdata import (FIELDS, GENERAL_TYPES, RESPONDENT_TYPES, FLAT,
                      FIELD_GOAL, STRAT, blocks, block_stats, pairs)
from taskdata import TASKS, tasks_of
import ahpcore as core
import storage

# ─────────────────────────────────────────────────────────────
st.set_page_config(page_title="시흥시 지역균형발전 전문가 AHP 조사",
                   page_icon="📊", layout="centered")

TOTAL_BLOCKS = sum(block_stats(f)[0] for f in FIELDS)
TOTAL_HIER_Q = sum(block_stats(f)[1] for f in FIELDS)
CRIT_PAIRS = pairs(len(CRIT))

st.markdown("""
<style>
html, body, [class*="st-"], [class*="css"],
.ahp-card, .ahp-qno, .ahp-pair, .ahp-ends, .ahp-pick, .ahp-score-grid {
  font-family: "Malgun Gothic", "맑은 고딕", "Apple SD Gothic Neo",
               "Noto Sans KR", "Nanum Gothic", sans-serif;
}
.block-container {max-width: 960px; padding-top: 2rem; padding-bottom: 4rem;}
.ahp-card {border:1px solid #e5e7eb; border-left:4px solid #1b365d; border-radius:10px;
           padding:.85rem 1.05rem .7rem; margin:1.1rem 0 .5rem; background:#fafbfc;}
.ahp-qno {font-size:.82rem; font-weight:700; color:#6b7280; letter-spacing:.02em;}
.ahp-pair {font-size:1.02rem; font-weight:700; line-height:1.6; color:#111827;}
.ahp-score-grid {display:grid; grid-template-columns:repeat(9,1fr); text-align:center;
                 font-size:.84rem; font-weight:700; color:#374151;
                 padding:0; margin:.45rem 0 -.5rem;}
.ahp-sep {color:#9ca3af; font-weight:400; padding:0 .7rem;}
.ahp-ends {display:flex; justify-content:space-between; font-size:.9rem;
           font-weight:700; color:#1b365d; margin-bottom:.15rem;}
.ahp-pick {font-size:.95rem; color:#1f2937; margin-top:.55rem; padding-left:.1rem;}
/* 눈금 위에 겹쳐 뜨는 기본 라벨과 양끝 라벨을 감춘다.
   선택 결과는 슬라이더 아래 문장으로 따로 보여 준다. */
[data-testid="stSliderThumbValue"] {display:none !important;}
[data-testid="stSliderTickBar"] {display:none !important;}
[data-testid="stSlider"] {padding-top:.1rem;}
</style>
""", unsafe_allow_html=True)


# ── 세션 ──────────────────────────────────────────────────────
DEFAULTS = {
    "page": 1,
    "meta": {},
    "response_id": uuid.uuid4().hex[:12],
    "crit_vals": [],
    "crit_diag": {},
    "hier": {},          # 블록코드 -> {"values": [...], "labels": [...], "items": [...]}
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


# ── 문항 위젯 ─────────────────────────────────────────────────
def _label(v, left, right):
    if v == 1:
        return "동등 1"
    return f"{left} {v}" if v > 0 else f"{right} {abs(v)}"


def ahp_question(key, left, right, qno, qtot):
    st.markdown(
        f'<div class="ahp-card"><div class="ahp-qno">문항 {qno} / {qtot}</div>'
        f'<div class="ahp-pair">{left}'
        f'<span class="ahp-sep">—</span>{right}</div></div>',
        unsafe_allow_html=True)
    st.markdown(
        f'<div class="ahp-ends"><span>← {left}</span><span>{right} →</span></div>'
        '<div class="ahp-score-grid">'
        '<span>9</span><span>7</span><span>5</span><span>3</span>'
        '<span>1</span><span>3</span><span>5</span><span>7</span><span>9</span></div>',
        unsafe_allow_html=True)

    labels = [_label(v, left, right) for v in SCALE]
    picked = st.select_slider(" ", options=labels, value="동등 1",
                              key=key, label_visibility="collapsed")
    v = SCALE[labels.index(picked)]
    if v == 1:
        msg = f"<b>{left}</b>와 <b>{right}</b>가 <b>동등하게 중요</b> (1)"
    elif v > 0:
        msg = (f"<b>{left}</b>가 <b>{right}</b>보다 <b>더 중요</b> "
               f"— {v}점 · {SCALE_HELP[abs(v)]}")
    else:
        msg = (f"<b>{right}</b>가 <b>{left}</b>보다 <b>더 중요</b> "
               f"— {abs(v)}점 · {SCALE_HELP[abs(v)]}")
    st.markdown(f'<div class="ahp-pick">↳ {msg}</div>', unsafe_allow_html=True)
    return v


def show_block_diag(title, values, labels, extra_transitivity=False):
    r = core.block_result(values, labels)
    st.markdown(f"**{title} · 일관성 점검**")
    if r["status"] == "적정":
        st.success(r["message"])
    elif r["status"] == "재검토":
        st.warning(r["message"])
        if r["worst"]:
            st.caption("전체 판단구조와 어긋나는 정도가 큰 비교입니다. "
                       "틀렸다는 뜻은 아니며, 먼저 다시 볼 문항입니다.")
            for i, (a, b) in enumerate(r["worst"], 1):
                st.write(f"{i}. {a} ↔ {b}")
    else:
        st.info(r["message"])
        if r["extreme"]:
            st.warning("두 항목 모두 척도 양극단(9)으로 응답하셨습니다. "
                       "의도한 판단인지 확인해 주십시오.")

    if extra_transitivity:
        viol, tot = core.transitivity_violations(values, labels)
        r["transitivity"] = [list(v) for v in viol]
        if viol:
            st.warning(f"전이성 검사 : 삼각형 {tot}개 중 {len(viol)}건 위반")
            for a, b, c in viol:
                st.write(f"· **{a}** > **{b}**, **{b}** > **{c}** 인데 "
                         f"**{a}** ≤ **{c}** 로 응답되었습니다.")
        else:
            st.success(f"전이성 검사 : 삼각형 {tot}개 모두 통과")
    return r


# ── 헤더 ──────────────────────────────────────────────────────
st.title("시흥시 지역균형발전 기본계획")
st.caption("우선순위사업 선정 전문가 AHP 조사 · "
           f"6개 분야 · 16개 전략 · {len(TASKS)}개 핵심과제 · 평가기준 4개")
st.progress({1: 0.06, 2: 0.30, 3: 0.58, 4: 0.80, 5: 1.0}[st.session_state.page])


# ═════════════════════════ 1. 응답자 정보 ═════════════════════
if st.session_state.page == 1:
    st.header("Ⅰ. 응답자 정보")
    st.write("본 조사는 「시흥시 균형발전 기본계획」의 42개 핵심과제 가운데 "
             "계획기간 중 우선 추진할 13개를 선정하기 위한 근거를 얻는 조사입니다.")

    with st.container(border=True):
        st.markdown("**응답 안내**")
        st.markdown(
         f"""
- **1. 평가기준 중요도**: 평가기준 간 상대적 중요도를 **쌍대비교({len(CRIT_PAIRS)}문항) **로 평가합니다.
- **2. 전략·핵심과제 중요도**: 소관 분야의 전략 및 핵심과제 간 상대적 중요도를 **쌍대비교**로 평가합니다.
- **3. 핵심과제 평가**: 각 핵심과제의 **실행 가능성**과 **파급·연계 효과**를 **5점 척도**로 평가합니다.
"""
    )

    c1, c2 = st.columns(2)
    with c1:
        name = st.text_input("성명 또는 전문가 ID *",
                             value=st.session_state.meta.get("name", ""))
        org = st.text_input("소속", value=st.session_state.meta.get("org", ""))
    with c2:
        prev = st.session_state.meta.get("field", RESPONDENT_TYPES[0])
        field = st.selectbox(
            "소관 분야 *", RESPONDENT_TYPES,
            index=RESPONDENT_TYPES.index(prev) if prev in RESPONDENT_TYPES else 0,
            help="분야 전문가는 해당 분야를, 균형발전 일반·공무원은 아래 두 항목을 선택하십시오.")
        careers = ["5년 미만", "5~10년", "10~15년", "15~20년", "20년 이상"]
        pc = st.session_state.meta.get("career", careers[0])
        career = st.selectbox("관련 분야 경력", careers,
                              index=careers.index(pc) if pc in careers else 0)
    siheung = st.radio("시흥시 관련 업무·연구 경험", ["있음", "없음"], horizontal=True)

    if field in GENERAL_TYPES:
        st.info(f"**{field}** 은 조사계획에 따라 **Ⅱ부(평가기준)만** 응답하십니다. "
                "Ⅲ·Ⅳ부는 분야 전문가가 소관 분야에 대해서만 응답합니다.")
    else:
        nb, nq = block_stats(field)
        flat = " · 전략층을 두지 않는 평면화 분야" if field in FLAT else ""
        st.info(f"**{field}** — 분야 목표 「{FIELD_GOAL[field]}」\n\n"
                f"Ⅲ부 {nb}블록 {nq}문항{flat} · Ⅳ부 {len(tasks_of(field))}개 과제 평정")

    with st.expander("진행하던 응답 이어서 하기 (JSON 불러오기)"):
        up = st.file_uploader("이전에 내려받은 진행상황 파일", type="json",
                              label_visibility="collapsed")
        if up is not None and st.button("불러오기", width="stretch"):
            try:
                data = json.loads(up.read().decode("utf-8"))
                for k in ("meta", "crit_vals", "hier", "ratings",
                          "opinions", "response_id"):
                    if k in data:
                        st.session_state[k] = data[k]
                st.success("불러왔습니다. 아래 버튼으로 이어서 진행하십시오.")
            except Exception as e:
                st.error(f"파일을 읽지 못했습니다 : {e}")

    if st.button("조사 시작", type="primary", width="stretch"):
        if not name.strip():
            st.error("성명 또는 전문가 ID를 입력해 주십시오.")
        else:
            st.session_state.meta = {
                "name": name.strip(), "org": org.strip(), "field": field,
                "career": career, "siheung": siheung,
            }
            go(2)


# ═════════════════════════ 2. 평가기준 ════════════════════════
elif st.session_state.page == 2:
    st.header(f"Ⅱ. 평가기준 간 상대적 중요도 ({len(CRIT_PAIRS)}문항)")
    st.write("우선순위 핵심과제를 선정할 때 **어느 기준을 더 비중 있게 보아야 하는지** 여쭙습니다.")

    with st.expander("평가기준 4개", expanded=True):
        for code, nm, qq, src in CRIT:
            st.markdown(f"**{code} {nm}** — {qq}  \n<small>점수 출처 : {src}</small>",
                        unsafe_allow_html=True)
        st.caption("구 「격차기여 유형」은 제4장 사업 분류값의 파생이라 진단이 두 번 "
                   "반영되는 이중 계산이므로 평가기준에서 제외했습니다. "
                   "결과표에는 병기하되 점수 산정에는 쓰지 않습니다.")

    st.info("척도 : 1 동등 · 3 약간 더 중요 · 5 뚜렷하게 더 중요 · "
            "7 매우 더 중요 · 9 절대적으로 더 중요")

    labels = [f"{c} {n}" for c, n, _q, _s in CRIT]
    vals = []
    for qn, (i, j) in enumerate(CRIT_PAIRS, 1):
        vals.append(ahp_question(f"crit_{i}_{j}", labels[i], labels[j],
                                 qn, len(CRIT_PAIRS)))
        st.divider()

    st.session_state.crit_vals = vals
    st.session_state.crit_diag = show_block_diag(
        "평가기준", vals, labels, extra_transitivity=True)
    st.caption("※ 비교항목이 4개인 블록은 자유도가 낮아 CR이 관대해집니다. "
               "그래서 전이성 검사를 함께 실시하며, 두 결과를 모두 보고서에 병기합니다.")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("← 이전", width="stretch"):
            go(1)
    with c2:
        nxt = 5 if is_general() else 3
        label = "최종 검토 →" if is_general() else "다음 : 분야별 중요도 →"
        if st.button(label, type="primary", width="stretch"):
            go(nxt)


# ═════════════════════════ 3. 계층 AHP ════════════════════════
elif st.session_state.page == 3:
    if is_general():
        go(5)
    field = rtype()
    nb, nq = block_stats(field)
    st.header(f"Ⅲ. {field} 전략·핵심과제의 정책적 중요도 (K1)")
    st.caption(f"{nb}개 블록 · {nq}문항 · 분야 목표 「{FIELD_GOAL[field]}」")
    if field in FLAT:
        st.info("이 분야는 전략 수와 과제 수가 적어 전략층을 두지 않고 "
                "분야 내 과제를 한 블록에서 비교합니다.")

    hier = {}
    for bi, (code, title, guide, items, labels) in enumerate(blocks(field), 1):
        st.subheader(f"Ⅲ-{bi}. {title}")
        st.caption(guide)
        prs = pairs(len(items))
        vals = [ahp_question(f"h_{field}_{code}_{i}_{j}", labels[i], labels[j],
                             qn, len(prs))
                for qn, (i, j) in enumerate(prs, 1)]
        diag = show_block_diag(title, vals, labels)
        hier[code] = {"title": title, "items": items, "labels": labels,
                      "values": vals, "diag": diag}
        st.divider()

    st.session_state.hier = hier

    c1, c2 = st.columns(2)
    with c1:
        if st.button("← 이전", width="stretch"):
            go(2)
    with c2:
        if st.button("다음 : 과제 평정 →", type="primary", width="stretch"):
            go(4)


# ═════════════════════════ 4. 평정 ════════════════════════════
elif st.session_state.page == 4:
    if is_general():
        go(5)
    field = rtype()
    codes = tasks_of(field)
    st.header(f"Ⅳ. {field} 핵심과제 평정 (K3 · K4)")
    st.write("각 과제의 **실행 가능성**과 **파급·연계 효과**를 5점으로 평가해 주십시오.")

    with st.container(border=True):
        st.markdown(
            "- **K3 실행 가능성** — 예산·인력·부지·제도 여건상 계획기간(5년) 내 착수가 가능한가  \n"
            "  5 = 즉시 착수 가능 · 1 = 여건 확보에 장기간 필요\n"
            "- **K4 파급·연계 효과** — 성과가 다른 분야 또는 다른 생활권으로 확산되는가  \n"
            "  5 = 확산효과 매우 큼 · 1 = 해당 사업에 국한")
    st.caption("모든 과제에 4점 이상을 주시면 과제 간 변별이 되지 않습니다. "
               "상대적인 차이를 표시해 주십시오.")

    ratings, missing = {}, []
    for c in codes:
        _f, nm, desc, _s, _t = TASKS[c]
        with st.container(border=True):
            st.markdown(f"**{c}　{nm}**")
            st.caption(desc)
            c1, c2 = st.columns(2)
            with c1:
                feas = st.radio("K3 실행 가능성", [1, 2, 3, 4, 5],
                                horizontal=True, index=None, key=f"feas_{c}")
            with c2:
                spill = st.radio("K4 파급·연계 효과", [1, 2, 3, 4, 5],
                                 horizontal=True, index=None, key=f"spill_{c}")
        if feas is None or spill is None:
            missing.append(c)
        ratings[c] = {"name": nm, "feas": feas, "spill": spill}

    st.session_state.ratings = ratings

    done = [v for v in ratings.values() if v["feas"] and v["spill"]]
    if done:
        avg = sum(v["feas"] + v["spill"] for v in done) / (2 * len(done))
        if len(done) == len(codes) and avg >= 4.5:
            st.warning(f"평정 평균이 {avg:.2f}로 높습니다. 과제 간 변별이 어려워질 수 있으니 "
                       "상대적 차이를 다시 살펴봐 주십시오.")

    if missing:
        st.info(f"아직 응답하지 않은 과제 {len(missing)}개 : {', '.join(missing)}")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("← 이전", width="stretch"):
            go(3)
    with c2:
        if st.button("최종 검토 →", type="primary", width="stretch"):
            if missing:
                st.error("모든 과제에 두 기준 모두 응답해 주십시오.")
            else:
                go(5)


# ═════════════════════════ 5. 검토·제출 ═══════════════════════
elif st.session_state.page == 5:
    meta = st.session_state.meta
    st.header("Ⅴ. 응답 검토 및 제출")
    st.write(f"**{meta.get('name','')}** · {meta.get('org','') or '소속 미기재'} · "
             f"{meta.get('field','')} · 경력 {meta.get('career','')}")

    cd = st.session_state.crit_diag or {}
    rows = [{"평가영역": "Ⅱ부 평가기준 (K1~K4)",
             "항목수": cd.get("n", "-"),
             "CR": "-" if cd.get("cr") is None else f"{cd['cr']:.3f}",
             "판정": cd.get("status", "-")}]
    for code, b in st.session_state.hier.items():
        d = b["diag"]
        rows.append({"평가영역": f"Ⅲ부 {b['title']}",
                     "항목수": d["n"],
                     "CR": "-" if d["cr"] is None else f"{d['cr']:.3f}",
                     "판정": d["status"]})
    st.dataframe(rows, width="stretch", hide_index=True)

    viol = cd.get("transitivity", []) or []
    bad = [r for r in rows if r["판정"] == "재검토"]
    if bad:
        st.warning(f"CR이 {CR_THRESHOLD:.2f}를 넘은 블록이 {len(bad)}개 있습니다. "
                   "제출은 가능하지만, 이전 단계로 돌아가 확인하시기를 권합니다.")
    if viol:
        st.warning(f"Ⅱ부 전이성 위반 {len(viol)}건이 있습니다. "
                   "CR 통과 여부와 무관하게 보고서에 「재검토」로 표시됩니다.")
    if not bad and not viol:
        st.success("일관성 검정이 가능한 모든 블록이 기준을 충족했습니다.")

    st.subheader("자유 의견")
    op1 = st.text_area(f"1. {len(TASKS)}개 핵심과제 외에 우선순위에 포함되어야 한다고 "
                       "보시는 과제가 있습니까?", key="op_missing")
    op2 = st.text_area("2. 특정 과제의 실행에 큰 제약이 있다면, 그 과제와 제약 요인을 "
                       "적어 주십시오.", key="op_constraint")
    op3 = st.text_area("3. 평가기준·분석방법에 대한 의견이 있으면 적어 주십시오.",
                       key="op_method")
    st.session_state.opinions = {"missing": op1, "constraint": op2, "method": op3}

    # ── payload ──
    pw_long = []
    labels = [f"{c} {n}" for c, n, _q, _s in CRIT]
    for (i, j), v in zip(CRIT_PAIRS, st.session_state.crit_vals):
        pw_long.append({"part": "II", "block": "CRIT",
                        "left": CRIT[i][0], "right": CRIT[j][0], "value": v})
    for code, b in st.session_state.hier.items():
        for (i, j), v in zip(pairs(len(b["items"])), b["values"]):
            pw_long.append({"part": "III", "block": code,
                            "left": b["items"][i], "right": b["items"][j], "value": v})

    payload = {
        "responseId": st.session_state.response_id,
        "schema": "siheung-ahp-2026-09",
        "meta": meta,
        "criteria": {"pairs": [[CRIT[i][0], CRIT[j][0]] for i, j in CRIT_PAIRS],
                     "values": st.session_state.crit_vals,
                     "weights": cd.get("weights")},
        "hierarchy": {c: {"items": b["items"], "values": b["values"],
                          "weights": b["diag"]["weights"]}
                      for c, b in st.session_state.hier.items()},
        "ratings": st.session_state.ratings,
        "pairwiseLong": pw_long,
        "opinions": st.session_state.opinions,
        "diagnostics": {
            "criteriaCR": cd.get("cr"),
            "criteriaStatus": cd.get("status"),
            "transitivity": viol,
            "blockCR": {c: b["diag"]["cr"] for c, b in st.session_state.hier.items()},
        },
        "submittedAt": storage.now_kst(),
    }
    jtxt = json.dumps(payload, ensure_ascii=False, indent=2)

    st.divider()
    if st.session_state.submitted:
        st.success(st.session_state.submit_msg)
        st.caption(f"접수번호 {st.session_state.response_id} · "
                   "이 창을 닫으셔도 됩니다. 감사합니다.")
    else:
        c1, c2 = st.columns([1, 2])
        with c1:
            if st.button("← 응답 수정", width="stretch"):
                go(5 if is_general() else 4)
        with c2:
            if st.button("최종 제출", type="primary", width="stretch"):
                ok, msg = storage.save(payload)
                st.session_state.submitted = ok
                st.session_state.submit_msg = msg
                if ok:
                    st.rerun()
                else:
                    st.error(f"온라인 접수에 실패했습니다 — {msg}")
                    st.info("아래 **응답 파일 내려받기**를 눌러 저장하신 뒤 "
                            "담당자에게 보내 주십시오. 응답은 유실되지 않습니다.")

    st.download_button("응답 파일 내려받기 (JSON)",
                       data=jtxt.encode("utf-8"),
                       file_name=f"AHP_{meta.get('field','')}_"
                                 f"{st.session_state.response_id}.json",
                       mime="application/json", width="stretch")


# ── 사이드바 : 진행 저장 ──────────────────────────────────────
with st.sidebar:
    st.markdown("### 진행 상황")
    st.caption(f"접수번호 {st.session_state.response_id}")
    if rtype():
        st.write(f"**{rtype()}**")
    st.write(f"Ⅱ부 {len(st.session_state.crit_vals)}/{len(CRIT_PAIRS)}문항")
    if not is_general() and rtype():
        nb, nq = block_stats(rtype())
        ans = sum(len(b["values"]) for b in st.session_state.hier.values())
        st.write(f"Ⅲ부 {ans}/{nq}문항")
        done = sum(1 for v in st.session_state.ratings.values()
                   if v.get("feas") and v.get("spill"))
        st.write(f"Ⅳ부 {done}/{len(tasks_of(rtype()))}과제")
    st.divider()
    st.download_button(
        "진행 상황 내려받기",
        data=json.dumps({
            "meta": st.session_state.meta,
            "response_id": st.session_state.response_id,
            "crit_vals": st.session_state.crit_vals,
            "hier": {c: {k: v for k, v in b.items() if k != "diag"}
                     for c, b in st.session_state.hier.items()},
            "ratings": st.session_state.ratings,
            "opinions": st.session_state.opinions,
        }, ensure_ascii=False, indent=2).encode("utf-8"),
        file_name=f"AHP_진행상황_{st.session_state.response_id}.json",
        mime="application/json", width="stretch")
    st.caption("중간에 그만두셔야 하면 내려받아 두셨다가, "
               "첫 화면에서 불러오기로 이어서 하실 수 있습니다.")
    st.divider()
    st.caption("문의 : 시흥시정연구원 ○○○ 연구원\n\n031-○○○-○○○○")
