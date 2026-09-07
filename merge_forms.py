# -*- coding: utf-8 -*-
"""웹폼이 내려준 응답 JSON들을 ahp.py 입력 CSV 3종으로 합친다.

사용법
    python merge_forms.py responses/            # 폴더 안의 *.json 전부
    python merge_forms.py a.json b.json ...
산출
    pairwise.csv    expert, group, field, P1~P10
    hierarchy.csv   expert, field, H1~Hn        (분야마다 n이 다르므로 최대열까지 채움)
    ratings.csv     expert, field, task, feas, spill
    submit_log.csv  응답 접수·일관성 점검 기록
빈 칸이 하나라도 있는 응답은 해당 파트에서 제외하고 submit_log.csv에 사유를 남긴다.
"""
import csv, glob, json, os, sys
from hierdata import STRAT, n_pairs

MAXH = max(n_pairs(f) for f in STRAT)


def load(paths):
    files = []
    for p in paths:
        if os.path.isdir(p):
            files += sorted(glob.glob(os.path.join(p, '*.json')))
        else:
            files.append(p)
    out = []
    for f in files:
        try:
            with open(f, encoding='utf-8-sig') as fh:
                d = json.load(fh)
            d['_src'] = os.path.basename(f)
            out.append(d)
        except Exception as e:
            print(f'  ! 건너뜀 {f}: {e}')
    return out


def main(paths):
    recs = load(paths)
    if not recs:
        print('응답 파일이 없습니다.')
        return

    # 동일인 중복 제출 → 마지막 것만
    seen = {}
    for d in recs:
        m = d.get('meta', {})
        key = (m.get('name', '').strip(), m.get('field', '').strip())
        seen[key] = d
    recs = list(seen.values())

    pw, hi, ra, log = [], [], [], []
    for d in recs:
        m = d.get('meta', {})
        who = m.get('name', '').strip() or d['_src']
        fld = m.get('field', '').strip()
        grp = m.get('group', '')
        dg = d.get('diagnostics', {}) or {}
        note = []

        # Ⅱ부 기준 쌍대비교
        P = d.get('pairwise') or []
        if len(P) == 10 and all(v is not None for v in P):
            pw.append([who, grp, fld] + [int(v) for v in P])
        else:
            note.append('기준 미완')

        # Ⅲ부 계층
        H = d.get('hierarchy') or []
        need = n_pairs(fld) if fld in STRAT else 0
        if need and len(H) >= need and all(v is not None for v in H[:need]):
            row = [who, fld] + [int(v) for v in H[:need]]
            row += [''] * (2 + MAXH - len(row))
            hi.append(row)
        else:
            note.append('계층 미완')

        # Ⅳ부 평정
        R = d.get('ratings') or {}
        n_ok = 0
        for code, v in R.items():
            if not v:
                continue
            fe, sp = v.get('feas'), v.get('spill')
            if fe is None or sp is None:
                continue
            ra.append([who, fld, code, int(fe), int(sp)])
            n_ok += 1
        if n_ok < len(R):
            note.append(f'평정 {n_ok}/{len(R)}')

        # 일관성
        cr = dg.get('criteriaCR')
        bad = [k for k, v in (dg.get('blockCR') or {}).items() if v is not None and v > 0.1]
        if cr is not None and cr > 0.1:
            note.append(f'기준 CR {cr:.3f}')
        if bad:
            note.append('블록 CR 초과: ' + ','.join(bad))

        log.append([who, m.get('org', ''), fld, grp, m.get('career', ''),
                    d.get('submittedAt', ''),
                    '' if cr is None else round(cr, 4), n_ok,
                    ' / '.join(note) or '이상 없음', d['_src']])

    def w(path, header, rows):
        with open(path, 'w', encoding='utf-8-sig', newline='') as f:
            c = csv.writer(f)
            c.writerow(header)
            c.writerows(rows)
        print(f'  {path:16s} {len(rows):3d}행')

    w('pairwise.csv', ['expert', 'group', 'field'] + [f'P{i+1}' for i in range(10)], pw)
    w('hierarchy.csv', ['expert', 'field'] + [f'H{i+1}' for i in range(MAXH)], hi)
    w('ratings.csv', ['expert', 'field', 'task', 'feas', 'spill'], ra)
    w('submit_log.csv', ['성명', '소속', '분야', '구분', '경력', '제출시각',
                         '기준CR', '평정과제수', '점검', '파일'], log)

    print(f'\n응답 {len(recs)}명 · 분야별 ' +
          ', '.join(f'{f}{sum(1 for r in recs if r.get("meta",{}).get("field")==f)}'
                    for f in STRAT))
    print('다음 단계 : python ahp.py --quota min1 --total 13')


if __name__ == '__main__':
    main(sys.argv[1:] or ['.'])
