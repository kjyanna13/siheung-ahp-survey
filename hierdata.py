# -*- coding: utf-8 -*-
"""
분야 → 전략(16) → 핵심과제(44) 계층과 분야 간 배분 쿼터
원자료 : 세부시행사업_217건_마스터.csv의 분야·전략·핵심과제 열
"""
from taskdata import DIAG

# 분야 : [(전략코드, 전략명, [핵심과제 코드])]
STRAT = {
 '교통': [
   ('교S1', '전략1 도시 대중교통체계 강화',            ['교1-1', '교1-2']),
   ('교S2', '전략2 도로·교통안전 및 생활환경 개선',    ['교2-1', '교2-2', '교2-3']),
   ('교S3', '전략3 생활권별 이동권 균형 실현',         ['교3-1', '교3-2', '교3-3', '교3-4']),
 ],
 '주거·환경': [
   ('주S1', '전략1 원도심·노후주거지 상향 정비',                  ['주1-1', '주1-2']),
   ('주S2', '전략2 주거취약계층·취약지역 주거안전망 강화',        ['주2-1', '주2-2']),
   ('주S3', '전략3 생활권 유형별 맞춤 정주기반 조성',             ['주3-1', '주3-2']),
   ('주S4', '전략4 생활환경 취약지역의 공원·녹지 접근성 개선',    ['주4-1', '주4-2', '주4-3', '주4-4']),
 ],
 '보건·복지': [
   ('복S1', '전략1 생애주기 돌봄 접근성 강화',   ['복1-1', '복1-2']),
   ('복S2', '전략2 지역사회 건강 안전망 강화',   ['복2-1', '복2-2']),
 ],
 '교육': [
   ('육S1', '전략1 교육시설 복합화·재구조화',                  ['육1-1', '육1-2', '육1-3']),
   ('육S2', '전략2 생활권 간 평생학습·돌봄 격차 완화',         ['육2-1', '육2-2', '육2-3']),
   ('육S3', '전략3 생활권 특성 기반 교육거점·공동체 육성',     ['육3-1', '육3-2', '육3-3', '육3-4']),
 ],
 '산업·경제': [
   ('산S1', '전략1 산업거점 고도화 및 성과 확산',   ['산1-1', '산1-2', '산1-3']),
   ('산S2', '전략2 생활권 경제 자생력 강화',        ['산2-1', '산2-2', '산2-3']),
 ],
 '문화·여가': [
   ('문S1', '전략1 생활밀착형 문화·여가 기반 확충',      ['문1-1', '문1-2', '문1-3']),
   ('문S2', '전략2 지역자원 기반 여가·관광 활성화',      ['문2-1', '문2-2']),
 ],
}
FIELDS = list(STRAT)


def pairs(n):
    return [(i, j) for i in range(n) for j in range(i + 1, n)]


# ── 계층 평면화 (2026-09-04 방법론 검토 반영)
# 전략이 2개뿐인 분야는 「전략 간 비교」와 「전략 내 과제 비교」가 모두 2×2가 되어
# 일관성비율(CR)을 단 한 번도 계산할 수 없다. 보건·복지는 3개 블록이 전부 2×2였다.
# 해당 분야는 전략 계층을 접고 과제를 한 블록에 놓는다.
#   보건·복지 4과제 → 6쌍(n=4, RI 0.90) / 문화·여가 5과제 → 10쌍(n=5, RI 1.12)
# 산업·경제(6과제 → 15쌍)는 응답부담을 고려해 전략 계층을 유지한다.
FLAT = {'보건·복지', '문화·여가'}


def flat_tasks(field):
    return [t for _c, _n, ts in STRAT[field] for t in ts]


def blocks(field):
    """분야별 비교 블록 : [(블록코드, 블록명, [항목코드], [항목명])]
       평면화 분야 : 과제 전체를 한 블록으로
       그 외        : ① 전략 간  ② 전략별 핵심과제 간 (과제 2개 미만 전략은 비교 없음)"""
    S = STRAT[field]
    if field in FLAT:
        ts = flat_tasks(field)
        return [('FLAT', f'{field} 핵심과제 간 비교', ts, ts)]
    out = []
    if len(S) >= 2:
        out.append(('STRAT', '전략 간 비교', [s[0] for s in S], [s[1] for s in S]))
    for code, name, tasks in S:
        if len(tasks) >= 2:
            out.append((code, name, tasks, tasks))
    return out


def n_pairs(field):
    return sum(len(pairs(len(b[2]))) for b in blocks(field))


# ── 분야 간 배분 쿼터
# 진단 원표 (claude/data/진단판정_6분야x9생활권.csv) — 54칸의 최종 판정
# ※ 원표의 분야명은 「문화·관광」이나 제4·5장 표기는 「문화·여가」. 여기서는 후자로 통일한다.
DIAG54 = {
 '교통':      {1:'─', 2:'○', 3:'◎', 4:'◎', 5:'◎', 6:'─', 7:'─', 8:'─', 9:'△'},
 '주거·환경': {1:'◎', 2:'◎', 3:'◎', 4:'○', 5:'◎', 6:'─', 7:'○', 8:'△', 9:'─'},
 '보건·복지': {1:'─', 2:'◎', 3:'◎', 4:'·', 5:'─', 6:'─', 7:'─', 8:'·', 9:'─'},
 '교육':      {1:'─', 2:'◎', 3:'◎', 4:'·', 5:'·', 6:'─', 7:'·', 8:'─', 9:'─'},
 '산업·경제': {1:'△', 2:'◎', 3:'·', 4:'·', 5:'◎', 6:'·', 7:'◎', 8:'─', 9:'─'},
 '문화·여가': {1:'─', 2:'◎', 3:'◎', 4:'○', 5:'─', 6:'─', 7:'△', 8:'·', 9:'─'},
}
DW = {'◎': 3, '○': 1, '△': 1, '─': 0, '·': 0}


def field_diag_counts():
    """분야별 진단 판정 집계 (진단 원표 54칸 기준)"""
    return {f: {'◎': sum(1 for v in z.values() if v == '◎'),
                '○△': sum(1 for v in z.values() if v in ('○', '△')),
                'score': sum(DW[v] for v in z.values())}
            for f, z in DIAG54.items()}


def _largest_remainder(exact, total):
    q = {f: int(exact[f]) for f in exact}
    rest = total - sum(q.values())
    for f in sorted(exact, key=lambda x: (-(exact[x] - int(exact[x])), x))[:max(0, rest)]:
        q[f] += 1
    return q


def quota(total=13, mode='min1', floor=1):
    """분야별 선정 쿼터
       min1      : 분야별 최소 floor개 보장 + 잔여를 가중점수(◎3+○△1) 비례 배분  ← 기본
       weighted  : 가중점수 비례 배분만 (하한 없음)
       circle    : ◎ 개수 비례 배분만
    """
    cnt = field_diag_counts()
    key = 'score' if mode in ('min1', 'weighted') else '◎'
    base = {f: cnt[f][key] for f in FIELDS}
    s = sum(base.values()) or 1
    if mode == 'min1':
        rest = total - floor * len(FIELDS)
        add = _largest_remainder({f: rest * base[f] / s for f in FIELDS}, rest)
        return {f: floor + add[f] for f in FIELDS}
    return _largest_remainder({f: total * base[f] / s for f in FIELDS}, total)


# 제5장 제4절 잠정안의 분야 배분 (대조용)
QUOTA_DRAFT = {'교통': 3, '주거·환경': 2, '보건·복지': 2, '교육': 2, '산업·경제': 2, '문화·여가': 2}


if __name__ == '__main__':
    tot_s = sum(len(v) for v in STRAT.values())
    tot_t = sum(len(t) for v in STRAT.values() for _, _, t in v)
    print(f'전략 {tot_s}개 / 핵심과제 {tot_t}개')
    print(f"\n{'분야':<10}{'전략':>4}{'과제':>4}{'블록':>5}{'쌍대비교':>8}{'2x2 블록':>10}")
    T = 0
    for f in FIELDS:
        bs = blocks(f)
        n2 = sum(1 for b in bs if len(b[2]) == 2)
        T += n_pairs(f)
        print(f'{f:<10}{len(STRAT[f]):>4}{sum(len(t) for _,_,t in STRAT[f]):>4}'
              f'{len(bs):>5}{n_pairs(f):>8}{n2:>8}/{len(bs)}')
    print(f"{'(전 분야 합)':<10}{tot_s:>4}{tot_t:>4}{'':>5}{T:>8}")

    cnt = field_diag_counts()
    qm, qw, qc = quota(13, 'min1'), quota(13, 'weighted'), quota(13, 'circle')
    print(f"\n{'분야':<10}{'◎':>4}{'○△':>5}{'가중점수':>9}"
          f"{'쿼터 min1':>11}{'가중비례':>10}{'◎비례':>9}{'제5장 잠정안':>13}")
    for f in FIELDS:
        print(f"{f:<10}{cnt[f]['◎']:>4}{cnt[f]['○△']:>5}{cnt[f]['score']:>9}"
              f"{qm[f]:>10}{qw[f]:>10}{qc[f]:>9}{QUOTA_DRAFT[f]:>12}")
    print(f"{'계':<10}{sum(c['◎'] for c in cnt.values()):>4}"
          f"{sum(c['○△'] for c in cnt.values()):>5}"
          f"{sum(c['score'] for c in cnt.values()):>9}"
          f"{sum(qm.values()):>10}{sum(qw.values()):>10}{sum(qc.values()):>9}"
          f"{sum(QUOTA_DRAFT.values()):>12}")

    # 배부목록 기반 집계와의 대조
    print('\n[대조] 배부목록(생활권별 과제목록)으로 집계하면 ○△가 몇 칸이 되는가')
    z = {}
    for f in FIELDS:
        codes = [t for s_ in STRAT[f] for t in s_[2]]
        zz = {}
        for c in codes:
            for zone, d in DIAG.get(c, {}).items():
                if zone not in zz or DW[d] > DW[zz[zone]]:
                    zz[zone] = d
        z[f] = sum(1 for v in zz.values() if v in ('○', '△'))
    print(f"  진단 원표 기준 ○△ = {sum(c['○△'] for c in cnt.values())}칸  /  "
          f"배부목록 기준 = {sum(z.values())}칸")
    print('  차이는 판정이 ○·△인데 그 생활권에 해당 분야 사업이 배치되지 않아')
    print('  배부목록에 나타나지 않는 칸이다 (주거-4·주거-7의 주거·환경 ○).')
    print('  쿼터 산정은 반드시 진단 원표를 쓴다.')
