# -*- coding: utf-8 -*-
"""
시흥시 지역균형발전 우선순위사업 선정 — 전문가 AHP 종합 분석 (결합안)
==========================================================================
구조
  1층  분야 간 배분   : 진단 원표(6분야×9생활권)의 ◎·○·△로 분야별 선정 쿼터를 정한다.
                        AHP를 쓰지 않는다 — 제3장이 이미 확정한 판단이다.
  2층  분야 내 순위   : 다섯 기준의 가중합
        K1 정책적 중요도  = 분야 내 계층 AHP (전략 가중치 × 과제 국지 가중치)   ← hier.py
        K2 주민 체감·수요 = 통장 수요조사 과제점수
        K3 격차기여 유형  = 217건 마스터의 Ⅰ/Ⅱ/Ⅲ 구성
        K4 실행 가능성    = 전문가 평정 5단계
        K5 파급·연계 효과 = 전문가 평정 5단계
        기준 가중치는 전문가 쌍대비교 10쌍 → 고유벡터 → 기하평균 종합(AIJ)
  3층  최종 선정      : 분야별 쿼터만큼 분야 내 상위를 뽑는다.

  ※ 진단(C1)을 2층 기준에서 뺀 이유 : 1층 쿼터 산정에 이미 쓰였다. 다시 쓰면 이중 계산이다.

사용법
    python3 ahp.py                     # 모의데이터로 전 과정 시연
    python3 ahp.py --demo 0            # 실제 응답 파일 사용
        pairwise.csv   기준 쌍대비교 (expert, P1~P10)
        hierarchy.csv  분야 내 계층 AHP (expert, field, H1~Hn)
        ratings.csv    과제 평정 (expert, task, feas, spill)
        survey_scores.csv  통장 수요조사 결과 (task, score 0~100)  ※ 없으면 K2 결측 처리
"""
import argparse, csv, os
import numpy as np
from taskdata import TASKS
from hierdata import STRAT, FIELDS, quota, field_diag_counts, QUOTA_DRAFT
import hier

# ─────────────────────────────── 기준 정의
CRIT = [
    ('K1', '정책적 중요도',   '균형발전 목표 달성에 대한 기여 — 분야 내 계층 AHP로 산출'),
    ('K2', '주민 체감·수요',  '통장 수요조사에서 현장이 얼마나 급하다고 판단했는가'),
    ('K3', '격차기여 유형',   '격차해소형(Ⅰ)인가, 기반유지(Ⅱ)·성장거점(Ⅲ)인가'),
    ('K4', '실행 가능성',     '재원·권한·기간·부서 수용성'),
    ('K5', '파급·연계 효과',  '다른 분야·생활권으로의 확산과 사업 간 연계'),
]
CODES = [c[0] for c in CRIT]
N = len(CODES)
PAIRS = [(i, j) for i in range(N) for j in range(i + 1, N)]      # 10쌍

RI = {1: 0.0, 2: 0.0, 3: 0.58, 4: 0.90, 5: 1.12, 6: 1.24,
      7: 1.32, 8: 1.41, 9: 1.45, 10: 1.49}
RATING = {5: 1.00, 4: 0.70, 3: 0.45, 2: 0.25, 1: 0.10}
TSCORE = np.array([1.0, 0.5, 0.3])                               # Ⅰ, Ⅱ, Ⅲ
FIELD_OF = {t: f for f in FIELDS for _c, _n, ts in STRAT[f] for t in ts}


# ─────────────────────────────── AHP 기본 연산
def matrix_from_answers(ans):
    A = np.ones((N, N))
    for (i, j), v in zip(PAIRS, ans):
        r = float(abs(v)) if abs(v) >= 1 else 1.0
        A[i, j] = r if v >= 0 else 1.0 / r
        A[j, i] = 1.0 / A[i, j]
    return A


def priority(A):
    w, v = np.linalg.eig(A)
    k = int(np.argmax(w.real))
    lmax = w[k].real
    p = np.abs(v[:, k].real)
    p = p / p.sum()
    n = A.shape[0]
    CI = (lmax - n) / (n - 1) if n > 1 else 0.0
    CR = CI / RI[n] if RI.get(n, 0) > 0 else 0.0
    return lmax, p, CI, CR


def aij(mats):
    return np.exp(np.log(np.stack(mats)).mean(axis=0))


def aip(weights):
    g = np.exp(np.log(np.stack(weights)).mean(axis=0))
    return g / g.sum()


def aip_stratified(ws, fields):
    """분야 층화 AIP.
       ① 분야 안에서 개인 우선도 벡터를 기하평균 → 분야별 w_f
       ② 분야 간 단순 기하평균 → 최종 w
       분야별 응답자 수가 어긋나도 여섯 분야가 동등한 발언권을 갖는다.
       Forman & Peniwati(1998) : 참여자가 각자 다른 이해·전문영역을 대표하면 AIP."""
    by = {}
    for w, f in zip(ws, fields):
        by.setdefault(f or '(미기재)', []).append(w)
    per = {f: aip(v) for f, v in by.items()}
    if len(per) <= 1:
        return aip(ws), per
    return aip(list(per.values())), per


# ─────────────────────────────── 과제별 기준점수
def score_k3():
    out = {}
    for c, (_f, _o, t) in TASKS.items():
        t = np.array(t, dtype=float)
        out[c] = float((t * TSCORE).sum() / t.sum()) if t.sum() else None
    return out


def score_from_ratings(rows, key):
    acc = {}
    for r in rows:
        v = str(r.get(key, '')).strip()
        if not v:
            continue
        acc.setdefault(r['task'], []).append(RATING[int(v)])
    return {c: float(np.exp(np.mean(np.log(v)))) for c, v in acc.items()}


def normalize01(d, by_field=False):
    """0~1 최소최대 정규화. by_field=True면 분야 안에서만 정규화한다."""
    if not by_field:
        v = [x for x in d.values() if x is not None]
        if not v:
            return d
        lo, hi = min(v), max(v)
        if hi - lo < 1e-12:
            return {k: (0.5 if x is not None else None) for k, x in d.items()}
        return {k: ((x - lo) / (hi - lo) if x is not None else None) for k, x in d.items()}
    out = {}
    for f in FIELDS:
        codes = [t for _c, _n, ts in STRAT[f] for t in ts]
        v = [d[c] for c in codes if d.get(c) is not None]
        if not v:
            out.update({c: None for c in codes})
            continue
        lo, hi = min(v), max(v)
        for c in codes:
            x = d.get(c)
            out[c] = None if x is None else (0.5 if hi - lo < 1e-12 else (x - lo) / (hi - lo))
    return out


# ─────────────────────────────── 최종점수 (결측 재정규화)
def final_scores(w, S):
    out = {}
    for c in TASKS:
        num, den, used = 0.0, 0.0, []
        for k, code in enumerate(CODES):
            s = S[code].get(c)
            if s is None:
                continue
            num += w[k] * s
            den += w[k]
            used.append(code)
        out[c] = (num / den if den > 0 else None, used)
    return out


def select_by_quota(scores, q):
    """분야별 쿼터만큼 분야 내 상위를 뽑는다"""
    picked = []
    for f in FIELDS:
        codes = [t for _c, _n, ts in STRAT[f] for t in ts if scores.get(t) is not None]
        codes.sort(key=lambda c: -scores[c])
        picked += codes[:q[f]]
    return picked


# ─────────────────────────────── 민감도
def sensitivity(w, S, q, sims=20000, conc=40.0, seed=1):
    rng = np.random.default_rng(seed)
    base = {c: final_scores(w, S)[c][0] for c in TASKS}
    base_pick = set(select_by_quota(base, q))
    cnt = {c: 0 for c in TASKS}
    stay = 0.0
    for _ in range(sims):
        wr = rng.dirichlet(conc * np.array(w))
        sc = {c: v[0] for c, v in final_scores(wr, S).items()}
        pick = set(select_by_quota(sc, q))
        for c in pick:
            cnt[c] += 1
        stay += len(pick & base_pick) / max(1, len(base_pick))
    return {c: cnt[c] / sims for c in TASKS}, stay / sims, base_pick


# ─────────────────────────────── 모의데이터
def make_demo(seed=42, n_expert=20):
    rng = np.random.default_rng(seed)
    truth = np.array([0.30, 0.24, 0.16, 0.17, 0.13])
    pair, rat = [], []
    scale = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9], dtype=float)
    for e in range(n_expert):
        noise = 0.35 if e % 7 else 1.6
        ans = []
        for i, j in PAIRS:
            r = (truth[i] / truth[j]) * np.exp(rng.normal(0, noise))
            r = min(max(r, 1 / 9), 9)
            v = scale[np.argmin(abs(scale - r))] if r >= 1 else -scale[np.argmin(abs(scale - 1 / r))]
            ans.append(int(v))
        pair.append({'expert': f'E{e+1:02d}', 'field': FIELDS[e % len(FIELDS)], 'ans': ans})
        for c in TASKS:
            rat.append({'expert': f'E{e+1:02d}', 'task': c,
                        'feas': int(rng.integers(2, 6)), 'spill': int(rng.integers(1, 6))})
    return pair, rat


def read_pairwise(path):
    out = []
    with open(path, encoding='utf-8-sig') as f:
        for r in csv.DictReader(f):
            if not (r.get('expert') or '').strip():
                continue
            try:
                out.append({'expert': r['expert'].strip(),
                            'field': (r.get('field') or '').strip(),
                            'ans': [int(r[f'P{k+1}']) for k in range(len(PAIRS))]})
            except (ValueError, KeyError, TypeError):
                continue
    return out


def read_ratings(path):
    with open(path, encoding='utf-8-sig') as f:
        return [dict(r) for r in csv.DictReader(f) if (r.get('task') or '').strip()]


# ─────────────────────────────── 실행
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--demo', type=int, default=1)
    ap.add_argument('--pairwise', default='pairwise.csv')
    ap.add_argument('--hierarchy', default='hierarchy.csv')
    ap.add_argument('--ratings', default='ratings.csv')
    ap.add_argument('--survey', default='survey_scores.csv')
    ap.add_argument('--total', type=int, default=13, help='우선순위사업 총 개수')
    ap.add_argument('--quota', choices=['min1', 'weighted', 'circle', 'draft'], default='min1')
    ap.add_argument('--norm', choices=['minmax', 'raw'], default='minmax')
    a = ap.parse_args()

    if a.demo:
        pair, rat = make_demo()
        hrows = hier.make_demo(per_field=6)
        print('※ 모의데이터로 실행 중 (기준 조사 20명 / 분야별 6명). 실제 응답은 --demo 0')
    else:
        pair, rat = read_pairwise(a.pairwise), read_ratings(a.ratings)
        hrows = hier.read_hier(a.hierarchy) if os.path.exists(a.hierarchy) else []

    # ── 1층 : 분야 간 배분
    print('\n' + '=' * 78)
    print('1층. 분야 간 배분 — 진단 원표 기준 (AHP 아님)')
    print('=' * 78)
    q = dict(QUOTA_DRAFT) if a.quota == 'draft' else quota(a.total, a.quota)
    cnt = field_diag_counts()
    print(f"  {'분야':<10}{'◎':>4}{'○△':>5}{'가중점수':>9}{'쿼터':>7}{'제5장 잠정안':>13}")
    for f in FIELDS:
        d = '' if q[f] == QUOTA_DRAFT[f] else '   ←差'
        print(f"  {f:<10}{cnt[f]['◎']:>4}{cnt[f]['○△']:>5}{cnt[f]['score']:>9}"
              f"{q[f]:>7}{QUOTA_DRAFT[f]:>12}{d}")
    print(f"  {'계':<10}{sum(c['◎'] for c in cnt.values()):>4}"
          f"{sum(c['○△'] for c in cnt.values()):>5}"
          f"{sum(c['score'] for c in cnt.values()):>9}{sum(q.values()):>7}"
          f"{sum(QUOTA_DRAFT.values()):>12}")

    # ── 2층-A : 분야 내 계층 AHP → K1
    print()
    task_w, hrep = hier.analyze(hrows) if hrows else ({}, {})

    # ── 2층-B : 기준 가중치
    print('\n' + '=' * 78)
    print('2층. 선정 기준의 가중치 — 개인별 일관성 검정')
    print('=' * 78)
    kept, mats, ws, kept_fields = [], [], [], []
    for p in pair:
        A = matrix_from_answers(p['ans'])
        lmax, w, CI, CR = priority(A)
        ok = CR <= 0.10
        if ok:
            kept.append(p['expert']); mats.append(A); ws.append(w)
            kept_fields.append(p.get('field', ''))
        print(f"  {p['expert']}  λmax={lmax:6.3f}  CI={CI:6.3f}  CR={CR:6.3f}  {'채택' if ok else '제외'}")
    if not kept:
        print('\n  ⚠ 채택된 응답이 없습니다. 종료.')
        return
    print(f"\n  응답 {len(pair)}명 → 채택 {len(kept)}명 (제외 {len(pair)-len(kept)}명, "
          f"제외율 {(len(pair)-len(kept))/len(pair)*100:.0f}%)")
    if len(kept) < 8:
        print('  ⚠ 채택 8명 미만 — 기준 수를 줄이거나 재조사가 필요합니다.')

    Ag = aij(mats)
    _, w_aij, _CIg, CRg = priority(Ag)
    w_aip = aip(ws)
    w_str, per_field_w = aip_stratified(ws, kept_fields)
    W = np.stack(ws)
    print(f"\n  {'기준':<20}{'AIP(층화)':>11}{'AIP(단순)':>11}{'AIJ':>9}"
          f"{'개인 최소':>10}{'최대':>8}{'변동계수':>10}")
    for k, (code, name, _d) in enumerate(CRIT):
        cv = W[:, k].std() / W[:, k].mean()
        print(f"  {code} {name:<16}{w_str[k]:>11.3f}{w_aip[k]:>11.3f}{w_aij[k]:>9.3f}"
              f"{W[:,k].min():>10.3f}{W[:,k].max():>8.3f}{cv:>10.2f}")
    print(f"\n  집단 행렬 CR(AIJ 대조) = {CRg:.3f}")
    print(f"  최대 격차 |AIP(층화) − AIJ| = {np.abs(w_str - w_aij).max():.3f}")
    if len(per_field_w) > 1:
        print(f"\n  [분야별 기준 가중치]  {'분야':<12}" + ''.join(f'{c:>8}' for c in CODES))
        for f, wf in per_field_w.items():
            print(f"  {'':<21}{f:<12}" + ''.join(f'{x:>8.3f}' for x in wf))
    # 채택값 : AIP(층화). 전문가가 각자 분야를 대표하므로 개인 우선도를 종합한다.
    w = w_str

    # ── 과제별 기준점수
    nz = (lambda d, **kw: normalize01(d, **kw)) if a.norm == 'minmax' else (lambda d, **kw: d)
    S = {}
    S['K1'] = nz({c: task_w.get(c) for c in TASKS}, by_field=True)
    S['K3'] = nz(score_k3())
    S['K4'] = nz(score_from_ratings(rat, 'feas'))
    S['K5'] = nz(score_from_ratings(rat, 'spill'))
    if os.path.exists(a.survey):
        raw = {}
        with open(a.survey, encoding='utf-8-sig') as f:
            for r in csv.DictReader(f):
                if (r.get('score') or '').strip():
                    raw[r['task']] = float(r['score']) / 100.0
        S['K2'] = {c: raw.get(c) for c in TASKS}
        print(f"\n  통장 수요조사 반영 : {sum(v is not None for v in S['K2'].values())}개 과제")
    else:
        S['K2'] = {c: None for c in TASKS}
        print(f"\n  ※ {a.survey} 없음 → K2를 전 과제 결측 처리하고 나머지 기준의 가중치를 재정규화")

    print('\n  [기준별 변별력]')
    print(f"    {'기준':<20}{'고유값 수':>10}{'범위':>18}{'최빈값 과제 수':>14}")
    for code, name, _d in CRIT:
        v = [x for x in S[code].values() if x is not None]
        if not v:
            print(f"    {code} {name:<16}{'—':>10}{'전 과제 결측':>18}{'—':>14}")
            continue
        vals = [round(x, 4) for x in v]
        uniq = sorted(set(vals))
        mode = max(uniq, key=vals.count)
        print(f"    {code} {name:<16}{len(uniq):>10}{f'{min(v):.3f}~{max(v):.3f}':>18}{vals.count(mode):>12}개")

    # ── 3층 : 최종 선정
    res = final_scores(w, S)
    sc = {c: v[0] for c, v in res.items()}
    picked = select_by_quota(sc, q)
    prob, stay, base_pick = sensitivity(w, S, q)

    print('\n' + '=' * 78)
    print(f'3층. 최종 선정 — 분야별 쿼터 적용 (계 {len(picked)}개)')
    print('=' * 78)
    for f in FIELDS:
        codes = [t for _c, _n, ts in STRAT[f] for t in ts if sc.get(t) is not None]
        codes.sort(key=lambda c: -sc[c])
        print(f"\n  [{f}]  쿼터 {q[f]}개 / 과제 {len(codes)}개")
        for i, c in enumerate(codes[:q[f]] + codes[q[f]:q[f] + 2]):
            mark = '★' if i < q[f] else '  '
            j = '안정' if prob[c] >= 0.9 else ('경계' if prob[c] >= 0.6 else '불안정')
            print(f"    {mark}{i+1:<2}{c:<7}{TASKS[c][1][:36]:<38}"
                  f"{sc[c]:>7.3f}   진입확률 {prob[c]:.2f} {j}")

    print('\n' + '=' * 78)
    print('민감도 — 가중치 Dirichlet 교란 20,000회')
    print('=' * 78)
    print(f"  선정 {len(base_pick)}개가 유지되는 평균 비율 : {stay:.3f}")
    unstable = [c for c in picked if prob[c] < 0.6]
    print(f"  불안정(진입확률 0.6 미만) 선정 과제 : "
          f"{', '.join(unstable) if unstable else '없음'}")

    # ── 저장
    with open('ahp_result.csv', 'w', encoding='utf-8-sig', newline='') as f:
        wc = csv.writer(f)
        wc.writerow(['분야', '분야내순위', '선정', '코드', '핵심과제', '최종점수'] +
                    [f'{c} {n}' for c, n, _ in CRIT] + ['적용기준수', '진입확률'])
        for fld in FIELDS:
            codes = [t for _c, _n, ts in STRAT[fld] for t in ts if sc.get(t) is not None]
            codes.sort(key=lambda c: -sc[c])
            for i, c in enumerate(codes):
                wc.writerow([fld, i + 1, '★' if c in picked else '', c, TASKS[c][1],
                             round(sc[c], 4)] +
                            [('' if S[k].get(c) is None else round(S[k][c], 4)) for k in CODES] +
                            [len(res[c][1]), round(prob[c], 4)])
    with open('ahp_weights.csv', 'w', encoding='utf-8-sig', newline='') as f:
        wc = csv.writer(f)
        wc.writerow(['기준', '명칭', 'AIJ', 'AIP', '개인최소', '개인최대', '변동계수'])
        for k, (code, name, _d) in enumerate(CRIT):
            wc.writerow([code, name, round(w_aij[k], 4), round(w_aip[k], 4),
                         round(W[:, k].min(), 4), round(W[:, k].max(), 4),
                         round(W[:, k].std() / W[:, k].mean(), 3)])
    if task_w:
        with open('ahp_hierarchy.csv', 'w', encoding='utf-8-sig', newline='') as f:
            wc = csv.writer(f)
            wc.writerow(['분야', '전략', '전략가중치', '코드', '핵심과제', '국지가중치', '전역가중치'])
            for fld in FIELDS:
                R = hrep.get(fld, {})
                swd = R.get('strategy_w', {})
                for scode, sname, ts in STRAT[fld]:
                    sw = swd.get(scode)
                    for t in ts:
                        g = task_w.get(t)
                        loc = (g / sw) if (g is not None and sw) else None
                        wc.writerow([fld, sname, '' if sw is None else round(sw, 4), t,
                                     TASKS[t][1], '' if loc is None else round(loc, 4),
                                     '' if g is None else round(g, 4)])

    # ── K1 × K4·K5 기준 분리 검증 (사전 등록 : |rho| >= 0.6 이면 중복 판정)
    print('\n' + '=' * 78)
    print('기준 분리 검증 — K1(Ⅲ부 계층)과 K4·K5(Ⅳ부 평정)의 순위상관')
    print('=' * 78)

    def spearman(a, b):
        codes = [c for c in TASKS if a.get(c) is not None and b.get(c) is not None]
        if len(codes) < 6:
            return None, len(codes)
        def rank(d):
            o = sorted(codes, key=lambda c: d[c])
            r = {}
            i = 0
            while i < len(o):
                j = i
                while j + 1 < len(o) and abs(d[o[j + 1]] - d[o[i]]) < 1e-12:
                    j += 1
                avg = (i + j) / 2 + 1
                for k in range(i, j + 1):
                    r[o[k]] = avg
                i = j + 1
            return np.array([r[c] for c in codes])
        x, y = rank(a), rank(b)
        if x.std() < 1e-12 or y.std() < 1e-12:
            return None, len(codes)
        return float(np.corrcoef(x, y)[0, 1]), len(codes)

    flag = False
    for k in ('K4', 'K5'):
        rho, n = spearman(S['K1'], S[k])
        if rho is None:
            print(f'  K1 × {k} : 산출 불가 (공통 과제 {n}개)')
            continue
        mark = '중복 의심' if abs(rho) >= 0.6 else '분리 양호'
        flag |= abs(rho) >= 0.6
        print(f'  K1 × {k} : rho = {rho:+.3f}  (n={n})   {mark}')
    print('\n  판정 기준(사전 등록) : |rho| >= 0.6 이면 응답자가 Ⅲ부에서 실행 가능성·파급 효과를')
    print('  함께 고려한 것으로 보아 보고서에 명시하고 K4·K5 가중치를 낮춘 대안을 병기한다.')
    if flag:
        print('  ⚠ 기준 초과 — 위 절차를 적용할 것.')

    # ── 쿼터 규칙 민감도 : 3규칙 × total 11/13/15 = 9시나리오
    print('\n' + '=' * 78)
    print('쿼터 민감도 — 배분규칙 3종 × 총량 11·13·15 (9시나리오)')
    print('=' * 78)
    base_all = {c: final_scores(w, S)[c][0] for c in TASKS}
    scen, tally = [], {c: 0 for c in TASKS}
    for tt in (11, 13, 15):
        for mm in ('min1', 'weighted', 'circle'):
            pick = set(select_by_quota(base_all, quota(tt, mm)))
            scen.append((tt, mm, pick))
            for c in pick:
                tally[c] += 1
    NS = len(scen)
    always = sorted([c for c, v in tally.items() if v == NS], key=lambda c: -base_all[c])
    most = sorted([c for c, v in tally.items() if NS > v >= NS / 2], key=lambda c: -tally[c])
    some = sorted([c for c, v in tally.items() if 0 < v < NS / 2], key=lambda c: -tally[c])
    print(f'  9개 시나리오 전부에서 선정  : {len(always):2d}개  ' + ' '.join(always))
    print(f'  과반(5~8) 시나리오에서 선정 : {len(most):2d}개  '
          + ' '.join(f'{c}({tally[c]})' for c in most))
    print(f'  소수(1~4) 시나리오에서만 선정: {len(some):2d}개  '
          + ' '.join(f'{c}({tally[c]})' for c in some))
    print(f'\n  → 쿼터 규칙·총량 논쟁이 실제로 바꾸는 사업은 {len(most)+len(some)}개이며,')
    print(f'     {len(always)}개는 어떤 규칙에서도 선정된다.')

    print('\n  저장 : ahp_result.csv, ahp_weights.csv, ahp_hierarchy.csv')


if __name__ == '__main__':
    main()
