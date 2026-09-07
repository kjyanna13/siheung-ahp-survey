# -*- coding: utf-8 -*-
"""
분야 내 계층 AHP  —  분야 → 전략 → 핵심과제
  · 블록별 쌍대비교에서 전문가별 가중치·CR 산출
  · 2×2 블록은 CR이 정의상 0이므로 검정 불가 → 응답자 간 방향 일치율·IQR로 대체 점검
  · 집단 종합은 AIP (분야별로 응답자 집단이 다르므로 개인 우선도 벡터의 기하평균)
  · 과제 전역 가중치 = 전략 가중치 × 전략 내 과제 국지 가중치  (분야 내 합 = 1)
"""
import csv
import numpy as np
from hierdata import STRAT, FLAT, flat_tasks, FIELDS, blocks, pairs, n_pairs

RI = {1: 0.0, 2: 0.0, 3: 0.58, 4: 0.90, 5: 1.12, 6: 1.24,
      7: 1.32, 8: 1.41, 9: 1.45, 10: 1.49}


def to_ratio(v):
    """+k = 왼쪽이 k배, -k = 오른쪽이 k배, ±1 = 동등"""
    v = float(v)
    a = abs(v) if abs(v) >= 1 else 1.0
    return a if v >= 0 else 1.0 / a


def matrix(n, vals):
    A = np.ones((n, n))
    for (i, j), v in zip(pairs(n), vals):
        A[i, j] = to_ratio(v)
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
    CR = CI / RI[n] if RI.get(n, 0) > 0 else None      # n<=2 → 검정 불가
    return lmax, p, CI, CR


def geo_norm(vs):
    """개인 우선도 벡터들의 기하평균 후 정규화 (AIP)"""
    M = np.stack(vs)
    g = np.exp(np.log(M).mean(axis=0))
    return g / g.sum()


# ─────────────────────────── 응답 읽기
def field_layout(field):
    """분야별 문항 배치 : [(블록코드, 블록명, 항목코드들, [(문항번호, i, j)])]"""
    out, no = [], 0
    for code, name, items, labels in blocks(field):
        ps = []
        for (i, j) in pairs(len(items)):
            no += 1
            ps.append((no, i, j))
        out.append((code, name, items, labels, ps))
    return out


def read_hier(path):
    """expert, field, H1, H2, ... 형식. 빈 칸은 무응답으로 그 전문가의 해당 분야를 제외"""
    rows = []
    with open(path, encoding='utf-8-sig') as f:
        for r in csv.DictReader(f):
            fld = r['field'].strip()
            if fld not in STRAT:
                continue
            n = n_pairs(fld)
            vals = []
            ok = True
            for k in range(1, n + 1):
                v = (r.get(f'H{k}') or '').strip()
                if v == '':
                    ok = False
                    break
                vals.append(int(v))
            if ok:
                rows.append({'expert': r['expert'].strip(), 'field': fld, 'vals': vals})
    return rows


# ─────────────────────────── 분석
def analyze(rows, verbose=True):
    """returns: task_weight {code: 분야 내 전역 가중치}, report(dict)"""
    by_field = {}
    for r in rows:
        by_field.setdefault(r['field'], []).append(r)

    task_w, rep = {}, {}
    for field, rs in by_field.items():
        lay = field_layout(field)
        per_block = {}          # 블록코드 → [개인 가중치 벡터]
        cr_rows = []            # (expert, 블록, n, CR)
        raw_ratio = {}          # (블록, 쌍) → [비율]  (2×2 대체점검용)
        kept = []
        dropped = []            # (expert, 블록, CR) — 블록 단위로 뺀 것
        for r in rs:
            v = r['vals']
            any_kept = False
            for code, name, items, labels, ps in lay:
                n = len(items)
                sub = [v[no - 1] for no, _i, _j in ps]
                A = matrix(n, sub)
                _l, p, _ci, cr = priority(A)
                cr_rows.append((r['expert'], code, n, cr))
                # ── 블록 단위 채택 : CR>0.10인 블록만 그 응답자에게서 뺀다.
                #    분야 응답 전체를 버리면 분야당 3~5명 표본이 곧바로 붕괴한다.
                if cr is not None and cr > 0.10:
                    dropped.append((r['expert'], code, float(cr)))
                    continue
                per_block.setdefault(code, []).append(p)
                any_kept = True
                for (no, i, j), val in zip(ps, sub):
                    raw_ratio.setdefault((code, i, j), []).append(to_ratio(val))
            if any_kept:
                kept.append(r['expert'])

        if not kept:
            rep[field] = {'n': len(rs), 'kept': 0, 'note': 'CR 통과 응답 없음'}
            continue

        # 블록별 집단 가중치 (AIP)
        gw = {code: geo_norm(vs) for code, vs in per_block.items()}
        S = STRAT[field]
        if field in FLAT:
            # 평면화 분야 : 과제 가중치가 곧 분야 내 전역 가중치다.
            ts = flat_tasks(field)
            fw = gw.get('FLAT', np.ones(len(ts)) / len(ts))
            for ti, t in enumerate(ts):
                task_w[t] = float(fw[ti])
        else:
            sw = gw.get('STRAT', np.ones(len(S)) / len(S))
            for si, (code, name, tasks) in enumerate(S):
                if len(tasks) == 1:
                    local = np.array([1.0])
                else:
                    local = gw.get(code, np.ones(len(tasks)) / len(tasks))
                for ti, t in enumerate(tasks):
                    task_w[t] = float(sw[si] * local[ti])

        # 2×2 블록 대체 점검 : 방향 일치율과 비율의 사분위 범위
        two = []
        for code, name, items, labels, ps in lay:
            if len(items) != 2:
                continue
            rr = np.array(raw_ratio.get((code, 0, 1), []))
            if len(rr) == 0:
                continue
            # 방향 일치율 : 「왼쪽 우세 / 오른쪽 우세 / 동등」 세 갈래 중 최빈 비율
            tie = float((rr == 1).mean())
            agree = max((rr > 1).mean(), (rr < 1).mean(), tie)
            q1, q3 = np.percentile(rr, [25, 75])
            two.append({'block': code, 'name': name, 'items': items, 'n': len(rr),
                        'agree': float(agree), 'tie': tie,
                        'median': float(np.median(rr)), 'iqr': (float(q1), float(q3))})

        block_n = {code: len(vs) for code, vs in per_block.items()}
        rep[field] = {'n': len(rs), 'kept': len(kept), 'kept_ids': kept,
                      'dropped': dropped, 'block_n': block_n,
                      'strategy_w': ({s_[0]: float(sum(task_w[t] for t in s_[2])) for s_ in S}
                                     if field in FLAT else
                                     {S[i][0]: float(sw[i]) for i in range(len(S))}),
                      'flat': field in FLAT,
                      'cr': cr_rows, 'two': two,
                      'n_pairs': n_pairs(field),
                      'n_blocks': len(lay),
                      'n_2x2': sum(1 for b in lay if len(b[2]) == 2)}

    # 분야 내 합이 1인지 확인
    for f in by_field:
        s = sum(task_w[t] for _c, _n, ts in STRAT[f] for t in ts if t in task_w)
        if s and abs(s - 1) > 1e-6:
            raise AssertionError(f'{f} 과제 가중치 합 {s:.6f} ≠ 1')

    if verbose:
        print('=' * 78)
        print('분야 내 계층 AHP')
        print('=' * 78)
        for f in FIELDS:
            if f not in rep:
                continue
            R = rep[f]
            lay = field_layout(f)
            if R.get('kept', 0) == 0:
                print(f'\n[{f}] 응답 {R["n"]}명 — {R["note"]}')
                continue
            print(f'\n[{f}]  응답 {R["n"]}명 → 채택 {R["kept"]}명   '
                  f'(비교 {R["n_pairs"]}쌍 / 블록 {R["n_blocks"]}개 중 2×2 {R["n_2x2"]}개)')
            print(('  전략 가중치(과제 가중치 합산) : ' if R.get('flat')
                   else '  전략 가중치 : ') + '  '.join(
                f'{c} {w:.3f}' for c, w in R['strategy_w'].items()))
            crs = [c for _e, _b, n, c in R['cr'] if c is not None]
            if crs:
                print(f'  CR 검정 가능한 비교 {len(crs)}건 : 평균 {np.mean(crs):.3f}, '
                      f'최대 {max(crs):.3f}, 0.1 초과 {sum(1 for c in crs if c > 0.1)}건')
                if R.get('dropped'):
                    print(f'  블록 단위 제외 {len(R["dropped"])}건 : '
                          + ', '.join(f'{e}·{b}(CR {c:.2f})' for e, b, c in R['dropped'][:6])
                          + (' …' if len(R['dropped']) > 6 else ''))
                if R.get('block_n'):
                    print('  블록별 채택 인원 : '
                          + ', '.join(f'{k} {v}명' for k, v in R['block_n'].items()))
            # 방법론 규정 : 블록별 채택 3명 미만이면 그 블록 결과를 제시하지 않는다
            weak = [b for b in [x[0] for x in lay]
                    if R.get('block_n', {}).get(b, 0) < 3]
            if weak:
                print('  ⚠ 채택 3명 미만 블록 — 결과를 제시하지 말고 동순위 처리 후 검토회의 논의 : '
                      + ', '.join(f"{b}({R.get('block_n', {}).get(b, 0)}명)" for b in weak))
            else:
                print('  ⚠ CR을 계산할 수 있는 블록이 하나도 없다 (전 블록 2×2)')
            for t in R['two']:
                flag = '일치' if t['agree'] >= 0.7 else '분산'
                print(f"    2×2 {t['block']:<6} n={t['n']:<3} 방향 일치율 {t['agree']:.0%}"
                      f"  중앙 비율 {t['median']:.2f}  IQR {t['iqr'][0]:.2f}~{t['iqr'][1]:.2f}   [{flag}]")
    return task_w, rep


# ─────────────────────────── 모의데이터
def make_demo(seed=7, per_field=4):
    rng = np.random.default_rng(seed)
    rows = []
    for f in FIELDS:
        n = n_pairs(f)
        truth = {}
        for code, name, items, labels, ps in field_layout(f):
            truth[code] = rng.dirichlet(np.ones(len(items)) * 2.0)
        for e in range(per_field):
            noise = 0.30 if e % 5 else 1.3
            vals = []
            for code, name, items, labels, ps in field_layout(f):
                t = truth[code]
                for (no, i, j) in ps:
                    r = (t[i] / t[j]) * np.exp(rng.normal(0, noise))
                    r = min(max(r, 1 / 9), 9)
                    s = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9], dtype=float)
                    v = s[np.argmin(abs(s - r))] if r >= 1 else -s[np.argmin(abs(s - 1 / r))]
                    vals.append(int(v))
            rows.append({'expert': f'{f[:2]}{e+1:02d}', 'field': f, 'vals': vals})
    return rows


def write_template(path='hierarchy_template.csv'):
    mx = max(n_pairs(f) for f in FIELDS)
    with open(path, 'w', encoding='utf-8-sig', newline='') as fp:
        w = csv.writer(fp)
        w.writerow(['expert', 'field'] + [f'H{k+1}' for k in range(mx)])
        for f in FIELDS:
            w.writerow(['', f] + [''] * n_pairs(f) + ['—'] * (mx - n_pairs(f)))
    return path


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--template':
        print('written:', write_template())
    else:
        tw, rep = analyze(make_demo())
        print('\n' + '=' * 78)
        print('과제 전역 가중치 (분야 내 합 = 1) — 모의데이터')
        print('=' * 78)
        for f in FIELDS:
            ts = [(t, tw[t]) for _c, _n, tasks in STRAT[f] for t in tasks if t in tw]
            print(f'\n[{f}]  합 {sum(v for _t, v in ts):.4f}')
            for t, v in sorted(ts, key=lambda x: -x[1]):
                print(f'   {t:<7}{v:.4f}')
