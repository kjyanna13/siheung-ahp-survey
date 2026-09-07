# -*- coding: utf-8 -*-
"""웹폼(webform.js)과 조사표(form.js)가 읽는 formdata.json·layout.json을
hierdata·taskdata에서 재생성한다.
계층을 바꾸면 반드시 이 스크립트를 다시 돌려야 산출물이 분석코드와 어긋나지 않는다."""
import json
from hierdata import STRAT, FIELDS, FLAT, blocks, pairs, n_pairs
from taskdata import TASKS

CRIT = [
    ['K1', '정책적 중요도',  '균형발전 목표 달성에 대한 기여'],
    ['K2', '주민 체감·수요', '통장 수요조사에서 나타난 현장 시급성'],
    ['K3', '격차기여 유형',  '격차해소형(Ⅰ)인가, 기반유지(Ⅱ)·성장거점(Ⅲ)인가'],
    ['K4', '실행 가능성',    '재원·권한·기간과 소관 부서의 수용 가능성'],
    ['K5', '파급·연계 효과', '다른 분야·생활권으로의 확산과 사업 간 연계'],
]


def build():
    out = {'crit': CRIT, 'pairs': [list(p) for p in pairs(5)], 'fields': {}}
    for f in FIELDS:
        bl, no = [], 0
        for code, name, items, labels in blocks(f):
            ps = []
            for (i, j) in pairs(len(items)):
                no += 1
                ps.append([no, i, j])
            # 과제 블록의 라벨은 「1-1 …」 공식명칭으로 바꾼다
            if code == 'STRAT':
                lab = labels
                kind = 'strategy'
            else:
                lab = [TASKS[t][1] for t in items]
                kind = 'task'
            bl.append({'code': code, 'title': name, 'kind': kind,
                       'items': items, 'labels': lab, 'pairs': ps})
        tasks = [[t, TASKS[t][1]] for _c, _n, ts in STRAT[f] for t in ts]
        out['fields'][f] = {'blocks': bl, 'total': n_pairs(f), 'tasks': tasks,
                            'flat': f in FLAT}
        assert no == n_pairs(f), f'{f} 문항수 불일치 {no} != {n_pairs(f)}'
    return out


def build_layout():
    """조사표(form.js)용 layout.json"""
    out = {}
    for f in FIELDS:
        bl, no = [], 0
        for code, name, items, labels in blocks(f):
            lab = labels if code == 'STRAT' else [TASKS[t][1] for t in items]
            ps = []
            for (i, j) in pairs(len(items)):
                no += 1
                ps.append({'no': no, 'a': lab[i], 'b': lab[j],
                           'ca': items[i], 'cb': items[j]})
            bl.append({'code': code, 'name': name, 'n': len(items), 'pairs': ps})
        out[f] = {'blocks': bl, 'total': n_pairs(f),
                  'tasks': [[t, TASKS[t][1]] for _c, _n, ts in STRAT[f] for t in ts],
                  'flat': f in FLAT}
    return out


if __name__ == '__main__':
    d = build()
    with open('formdata.json', 'w', encoding='utf-8') as fh:
        json.dump(d, fh, ensure_ascii=False)
    with open('layout.json', 'w', encoding='utf-8') as fh:
        json.dump(build_layout(), fh, ensure_ascii=False)
    print('formdata.json · layout.json 재생성')
    for f in FIELDS:
        z = d['fields'][f]
        print(f"  {f:<10} 블록 {len(z['blocks']):>2}  문항 {z['total']:>3}  "
              f"과제 {len(z['tasks']):>2}  {'[평면화]' if z['flat'] else ''}")
    print(f"  {'계':<10} {'':>5}  문항 {sum(d['fields'][f]['total'] for f in FIELDS):>3}")
