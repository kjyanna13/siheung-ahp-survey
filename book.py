# -*- coding: utf-8 -*-
"""전문가 AHP 응답 입력·집계 서식 (xlsx)"""
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from taskdata import TASKS

F = '맑은 고딕'
HDR = PatternFill('solid', fgColor='1F3864')
SUB = PatternFill('solid', fgColor='E8EDF5')
IN = PatternFill('solid', fgColor='FFF9E0')     # 입력 칸
OUT = PatternFill('solid', fgColor='F2F2F2')    # 자동 계산
BAD = PatternFill('solid', fgColor='FFD9D9')
thin = Side(style='thin', color='BBBBBB')
BOX = Border(left=thin, right=thin, top=thin, bottom=thin)

CRIT = [('K1', '정책적 중요도'), ('K2', '주민 체감·수요'), ('K3', '격차기여 유형'),
        ('K4', '실행 가능성'), ('K5', '파급·연계 효과')]
PAIRS = [(i, j) for i in range(5) for j in range(i + 1, 5)]

wb = openpyxl.Workbook()

def style(ws, widths):
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w

def title(ws, row, text, span, size=13):
    c = ws.cell(row=row, column=1, value=text)
    c.font = Font(F, size=size, bold=True, color='FFFFFF')
    c.fill = HDR
    c.alignment = Alignment(vertical='center')
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=span)
    ws.row_dimensions[row].height = 26

def head(ws, row, vals, start=1):
    for k, v in enumerate(vals):
        c = ws.cell(row=row, column=start + k, value=v)
        c.font = Font(F, size=9, bold=True)
        c.fill = SUB
        c.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        c.border = BOX
    ws.row_dimensions[row].height = 30

# ───────────────────────────── 1. 안내
ws = wb.active
ws.title = '안내'
style(ws, [3, 22, 100])
title(ws, 1, '시흥시 지역균형발전 우선순위사업 — 전문가 AHP 응답 입력·집계 서식', 3, 14)
rows = [
    ('', ''),
    ('이 서식이 하는 일', '전문가 조사표의 응답을 입력하면 개인별 일관성비율(CR)과 집단 가중치가 자동 계산됩니다.'),
    ('', 'CR > 0.1인 응답은 붉게 표시되며, 재응답 요청 또는 제외 대상입니다.'),
    ('', ''),
    ('입력하는 곳', '노란색 칸에만 입력하십시오. 회색 칸은 수식이므로 건드리지 마십시오.'),
    ('', ''),
    ('① 쌍대비교 입력', '전문가 1명당 1행. P1~P10에 조사표 Ⅱ부의 응답을 부호를 붙여 적습니다.'),
    ('', '   왼쪽 기준에 ○ → 그 숫자를 그대로 (예: 5)'),
    ('', '   오른쪽 기준에 ○ → 음수로 (예: -3)'),
    ('', '   가운데 1에 ○ → 1'),
    ('', ''),
    ('② 평정 입력', '전문가 × 핵심과제. K4 실행가능성, K5 파급·연계를 1~5로 적습니다. 무응답은 비워 둡니다.'),
    ('', ''),
    ('③ 집단 가중치', '①에서 CR ≤ 0.1인 응답만 모아 기하평균으로 종합합니다. 자동 계산됩니다.'),
    ('', ''),
    ('④ 과제 기준점수', 'K3은 사업 자료로 이미 채워져 있습니다.'),
    ('', '   K1은 5·6번 시트의 계층 AHP 결과(전역 가중치)를 옮겨 적으면 분야 내에서 자동 정규화됩니다.'),
    ('', '   K2는 통장 수요조사 결과를, K4·K5는 ②의 평정 평균이 자동으로 들어옵니다.'),
    ('', ''),
    ('⑤ 최종 점수', '기준 가중치 × 기준점수의 가중합. 값이 없는 기준은 제외하고 가중치를 재정규화합니다.'),
    ('', ''),
    ('주의', '이 서식은 행 기하평균 근사법으로 가중치를 구합니다. 보고서에 실을 최종 수치는'),
    ('', 'ahp.py(고유벡터법)로 산출하십시오. 두 값은 통상 소수 셋째 자리에서 갈립니다.'),
    ('', ''),
    ('⑥ 계층 AHP 입력', '분야별 전략·핵심과제 쌍대비교(3~15문항). 블록별 가중치와 CR이 자동 계산됩니다.'),
    ('', '   항목이 2개뿐인 블록은 CR이 「—」로 표시됩니다 — 일관성 검정이 정의상 불가능합니다.'),
    ('', ''),
    ('일관성비율 기준', 'CR = CI / RI,  CI = (λmax − n) / (n − 1).  RI : n=3 → 0.58, n=4 → 0.90, n=5 → 1.12'),
    ('', 'CR ≤ 0.1 이면 논리적으로 일관된 응답으로 봅니다 (Saaty). n=2는 검정 불가.'),
    ('', ''),
    ('분야 간 배분', '분야별로 몇 개를 뽑을지는 이 서식이 정하지 않습니다. 진단 원표(6분야×9생활권)로'),
    ('', 'ahp.py가 산출합니다 — 기본값은 교통2·주거3·복지2·교육2·산업2·문화2 = 13개.'),
]
for i, (a, b) in enumerate(rows, start=2):
    ws.cell(row=i, column=2, value=a).font = Font(F, size=10, bold=True)
    ws.cell(row=i, column=3, value=b).font = Font(F, size=10)

# 기준 설명
r = len(rows) + 4
title(ws, r, '다섯 가지 기준', 3, 12)
for k, (code, name) in enumerate(CRIT):
    ws.cell(row=r + 1 + k, column=2, value=code).font = Font(F, size=10, bold=True)
    ws.cell(row=r + 1 + k, column=3, value=name).font = Font(F, size=10)

# ───────────────────────────── 2. 쌍대비교 입력
ws = wb.create_sheet('1_쌍대비교입력')
style(ws, [10, 14, 12] + [7] * 10 + [3] + [9] * 10 + [3] + [9] * 5 + [3, 11, 11, 11, 12])
title(ws, 1, '① 쌍대비교 입력  —  노란 칸(P1~P10)에만 입력하십시오', 45, 12)
sub = ['전문가', '구분', '전문분야'] + [f'P{k+1}' for k in range(10)] + [''] + \
      [f'R{k+1}' for k in range(10)] + [''] + [c for c, _ in CRIT] + [''] + \
      ['λmax', 'CI', 'CR', '판정']
head(ws, 3, sub)
# P1~P10 쌍 이름
for k, (i, j) in enumerate(PAIRS):
    c = ws.cell(row=2, column=4 + k, value=f'{CRIT[i][0]}↔{CRIT[j][0]}')
    c.font = Font(F, size=8, color='666666')
    c.alignment = Alignment(horizontal='center')

NEXP = 30
for e in range(NEXP):
    r = 4 + e
    ws.cell(row=r, column=1, value=f'E{e+1:02d}').font = Font(F, size=10)
    for col in (2, 3):
        ws.cell(row=r, column=col).font = Font(F, size=10)
    for k in range(10):
        c = ws.cell(row=r, column=4 + k)
        c.fill = IN; c.border = BOX
        c.alignment = Alignment(horizontal='center')
        c.font = Font(F, size=10, color='0000FF')
    # R : 부호를 비율로
    for k in range(10):
        p = get_column_letter(4 + k)
        c = ws.cell(row=r, column=15 + k,
                    value=f'=IF({p}{r}="","",IF({p}{r}>=0,ABS({p}{r}),1/ABS({p}{r})))')
        c.fill = OUT; c.font = Font(F, size=9); c.number_format = '0.000'
    R = [get_column_letter(15 + k) + str(r) for k in range(10)]
    # 행 기하평균 (a_ii = 1)
    gm = [
        f'=IF({R[0]}="","",({R[0]}*{R[1]}*{R[2]}*{R[3]})^(1/5))',
        f'=IF({R[0]}="","",(1/{R[0]}*{R[4]}*{R[5]}*{R[6]})^(1/5))',
        f'=IF({R[0]}="","",(1/{R[1]}*1/{R[4]}*{R[7]}*{R[8]})^(1/5))',
        f'=IF({R[0]}="","",(1/{R[2]}*1/{R[5]}*1/{R[7]}*{R[9]})^(1/5))',
        f'=IF({R[0]}="","",(1/{R[3]}*1/{R[6]}*1/{R[8]}*1/{R[9]})^(1/5))',
    ]
    # 임시 GM 열 (숨김) : 41~45
    for k in range(5):
        c = ws.cell(row=r, column=41 + k, value=gm[k])
        c.font = Font(F, size=8, color='999999'); c.number_format = '0.0000'
    G = [get_column_letter(41 + k) + str(r) for k in range(5)]
    gsum = f'SUM({G[0]}:{G[4]})'
    for k in range(5):
        c = ws.cell(row=r, column=26 + k, value=f'=IF({G[0]}="","",{G[k]}/{gsum})')
        c.fill = OUT; c.font = Font(F, size=9, bold=True); c.number_format = '0.000'
    Wc = [get_column_letter(26 + k) + str(r) for k in range(5)]
    # λmax = 평균 of (Aw)_i / w_i
    aw = [
        f'({Wc[0]}+{R[0]}*{Wc[1]}+{R[1]}*{Wc[2]}+{R[2]}*{Wc[3]}+{R[3]}*{Wc[4]})/{Wc[0]}',
        f'({Wc[0]}/{R[0]}+{Wc[1]}+{R[4]}*{Wc[2]}+{R[5]}*{Wc[3]}+{R[6]}*{Wc[4]})/{Wc[1]}',
        f'({Wc[0]}/{R[1]}+{Wc[1]}/{R[4]}+{Wc[2]}+{R[7]}*{Wc[3]}+{R[8]}*{Wc[4]})/{Wc[2]}',
        f'({Wc[0]}/{R[2]}+{Wc[1]}/{R[5]}+{Wc[2]}/{R[7]}+{Wc[3]}+{R[9]}*{Wc[4]})/{Wc[3]}',
        f'({Wc[0]}/{R[3]}+{Wc[1]}/{R[6]}+{Wc[2]}/{R[8]}+{Wc[3]}/{R[9]}+{Wc[4]})/{Wc[4]}',
    ]
    c = ws.cell(row=r, column=32, value=f'=IF({G[0]}="","",({"+".join(aw)})/5)')
    c.fill = OUT; c.font = Font(F, size=9); c.number_format = '0.000'
    c = ws.cell(row=r, column=33, value=f'=IF(AF{r}="","",(AF{r}-5)/4)')
    c.fill = OUT; c.font = Font(F, size=9); c.number_format = '0.000'
    c = ws.cell(row=r, column=34, value=f'=IF(AG{r}="","",AG{r}/1.12)')
    c.fill = OUT; c.font = Font(F, size=10, bold=True); c.number_format = '0.000'
    c = ws.cell(row=r, column=35, value=f'=IF(AH{r}="","",IF(AH{r}<=0.1,"채택","제외"))')
    c.fill = OUT; c.font = Font(F, size=10, bold=True)
    c.alignment = Alignment(horizontal='center')
    # 채택 응답만 뽑아 둔 보조열 (표준편차 계산용, 배열수식 회피)
    for k in range(5):
        wcol = get_column_letter(26 + k)
        c = ws.cell(row=r, column=47 + k, value=f'=IF($AI{r}="채택",{wcol}{r},"")')
        c.font = Font(F, size=8, color='999999'); c.number_format = '0.0000'

# 예시 행
ex = [5, 3, 3, 5, 1, 2, 3, -2, 2, 3]
for k, v in enumerate(ex):
    ws.cell(row=4, column=4 + k, value=v)
ws.cell(row=4, column=2, value='분야전문가')
ws.cell(row=4, column=3, value='교통')
ws.cell(row=3 + NEXP + 2, column=1,
        value='※ 4행은 형식을 보이기 위한 예시입니다. 실제 응답을 입력하실 때 지우고 쓰십시오.').font = Font(F, size=9, color='C00000')
ws.cell(row=3 + NEXP + 3, column=1,
        value='※ AO~AS열과 AU~AY열(회색 작은 글씨)은 계산용 중간값입니다. 지우지 마십시오.').font = Font(F, size=9, color='999999')
ws.freeze_panes = 'D4'

# 요약
r0 = 3 + NEXP + 5
title(ws, r0, '응답 요약', 10, 11)
ws.cell(row=r0 + 1, column=1, value='응답 수').font = Font(F, size=10, bold=True)
ws.cell(row=r0 + 1, column=3, value=f'=COUNTA(D4:D{3+NEXP})').font = Font(F, size=10)
ws.cell(row=r0 + 2, column=1, value='채택(CR≤0.1)').font = Font(F, size=10, bold=True)
ws.cell(row=r0 + 2, column=3, value=f'=COUNTIF(AI4:AI{3+NEXP},"채택")').font = Font(F, size=10)
ws.cell(row=r0 + 3, column=1, value='제외').font = Font(F, size=10, bold=True)
ws.cell(row=r0 + 3, column=3, value=f'=COUNTIF(AI4:AI{3+NEXP},"제외")').font = Font(F, size=10)
ws.cell(row=r0 + 4, column=1, value='제외율').font = Font(F, size=10, bold=True)
c = ws.cell(row=r0 + 4, column=3, value=f'=IFERROR(C{r0+3}/C{r0+1},"")')
c.font = Font(F, size=10); c.number_format = '0.0%'

# ───────────────────────────── 3. 집단 가중치
ws = wb.create_sheet('2_집단가중치')
style(ws, [4, 8, 22, 13, 13, 13, 13, 13, 3, 40])
title(ws, 1, '③ 집단 가중치  —  CR ≤ 0.1인 응답만 기하평균', 10, 12)
head(ws, 3, ['', '기준', '명칭', '가중치', '개인 최소', '개인 최대', '평균', '표준편차'])
last = 3 + NEXP
for k, (code, name) in enumerate(CRIT):
    r = 4 + k
    col = get_column_letter(26 + k)
    ws.cell(row=r, column=2, value=code).font = Font(F, size=11, bold=True)
    ws.cell(row=r, column=3, value=name).font = Font(F, size=11)
    # 채택된 응답만의 기하평균 → 정규화
    gm = f"EXP(AVERAGEIF('1_쌍대비교입력'!$AI$4:$AI${last},\"채택\",'1_쌍대비교입력'!{col}4:{col}{last}))"
    ws.cell(row=r, column=4, value=f"=IFERROR(AVERAGEIF('1_쌍대비교입력'!$AI$4:$AI${last},\"채택\",'1_쌍대비교입력'!{col}$4:{col}${last})/$D$9,\"\")")
    ws.cell(row=r, column=4).number_format = '0.000'
    ws.cell(row=r, column=4).font = Font(F, size=11, bold=True)
    ws.cell(row=r, column=4).fill = OUT
    for col_i, fn in ((5, 'MINIFS'), (6, 'MAXIFS')):
        ws.cell(row=r, column=col_i,
                value=f"=IFERROR(_xlfn.{fn}('1_쌍대비교입력'!{col}$4:{col}${last},'1_쌍대비교입력'!$AI$4:$AI${last},\"채택\"),\"\")")
        ws.cell(row=r, column=col_i).number_format = '0.000'
        ws.cell(row=r, column=col_i).font = Font(F, size=10)
    ws.cell(row=r, column=7,
            value=f"=IFERROR(AVERAGEIF('1_쌍대비교입력'!$AI$4:$AI${last},\"채택\",'1_쌍대비교입력'!{col}$4:{col}${last}),\"\")")
    ws.cell(row=r, column=7).number_format = '0.000'
    ws.cell(row=r, column=7).font = Font(F, size=10)
    hcol = get_column_letter(47 + k)
    ws.cell(row=r, column=8, value=f"=IFERROR(STDEV('1_쌍대비교입력'!{hcol}$4:{hcol}${last}),\"\")")
    ws.cell(row=r, column=8).number_format = '0.000'
    ws.cell(row=r, column=8).font = Font(F, size=10)
# 정규화 분모
ws.cell(row=9, column=3, value='합계(정규화 분모)').font = Font(F, size=10, bold=True)
ws.cell(row=9, column=4, value=f"=SUM(G4:G8)").font = Font(F, size=10)
ws.cell(row=9, column=4).number_format = '0.000'
ws.cell(row=10, column=3, value='가중치 합').font = Font(F, size=10, bold=True)
ws.cell(row=10, column=4, value='=SUM(D4:D8)').font = Font(F, size=10, bold=True)
ws.cell(row=10, column=4).number_format = '0.000'
ws.cell(row=12, column=2, value='※ 개인 가중치의 산술평균을 정규화한 값입니다. 보고서 수치는 ahp.py(고유벡터·기하평균 종합)로 산출하십시오.').font = Font(F, size=9, color='C00000')
ws.cell(row=13, column=2, value='※ 개인 최소·최대의 폭이 크면 전문가 간 이견이 큰 기준입니다. 그 사실을 보고서에 함께 적으십시오.').font = Font(F, size=9, color='555555')

# ───────────────────────────── 4. 평정 입력
ws = wb.create_sheet('3_평정입력')
style(ws, [10, 10, 42, 12, 12])
title(ws, 1, '② 평정 입력  —  전문가 × 핵심과제. C4·C5를 1~5로. 무응답은 비워 두십시오', 5, 12)
head(ws, 3, ['전문가', '코드', '핵심과제', 'C4 실행가능성', 'C5 파급·연계'])
r = 4
codes = list(TASKS)
for e in range(1, 4):
    for code in codes:
        ws.cell(row=r, column=1, value=f'E{e:02d}').font = Font(F, size=9)
        ws.cell(row=r, column=2, value=code).font = Font(F, size=9, bold=True)
        ws.cell(row=r, column=3, value=TASKS[code][1]).font = Font(F, size=9)
        for col in (4, 5):
            c = ws.cell(row=r, column=col)
            c.fill = IN; c.border = BOX
            c.alignment = Alignment(horizontal='center')
            c.font = Font(F, size=10, color='0000FF')
        r += 1
ws.cell(row=r + 1, column=1, value='※ 전문가 3명분(132행)만 미리 만들어 두었습니다. 인원이 늘면 블록을 복사해 이어 붙이십시오.').font = Font(F, size=9, color='C00000')
ws.freeze_panes = 'A4'
RATE_END = r - 1

# ───────────────────────────── 5. 과제 기준점수·최종점수
ws = wb.create_sheet('4_최종점수')
style(ws, [9, 10, 42, 12, 11, 11, 11, 11, 3, 12, 10, 3, 12])
title(ws, 1, '④⑤ 과제별 기준점수와 최종 점수  (분야 안에서 순위를 매긴다)', 13, 12)
head(ws, 3, ['코드', '분야', '핵심과제', 'K1 전역가중치', 'K1 정규화', 'K2 수요', 'K3 유형',
             'K4 실행', 'K5 파급', '', '최종점수', '분야내순위'])
import importlib
ahp = importlib.import_module('ahp')
from hierdata import STRAT, FIELDS
k3 = ahp.normalize01(ahp.score_k3())
order = [t for f in FIELDS for _c, _n, ts in STRAT[f] for t in ts]
rows_of = {}
r = 4
for f in FIELDS:
    ts = [t for _c, _n, tt in STRAT[f] for t in tt]
    rows_of[f] = (r, r + len(ts) - 1)
    r += len(ts)
for i, code in enumerate(order):
    r = 4 + i
    f = TASKS[code][0]
    lo, hi = rows_of[f]
    ws.cell(row=r, column=1, value=code).font = Font(F, size=9, bold=True)
    ws.cell(row=r, column=2, value=f).font = Font(F, size=9)
    ws.cell(row=r, column=3, value=TASKS[code][1]).font = Font(F, size=9)
    # K1 : 계층 AHP 전역 가중치 입력 → 분야 안에서 0~1 정규화
    c = ws.cell(row=r, column=4)
    c.fill = IN; c.border = BOX; c.number_format = '0.0000'
    c.font = Font(F, size=9, color='0000FF')
    c = ws.cell(row=r, column=5,
                value=f'=IF(D{r}="","",IF(MAX($D${lo}:$D${hi})=MIN($D${lo}:$D${hi}),0.5,'
                      f'(D{r}-MIN($D${lo}:$D${hi}))/(MAX($D${lo}:$D${hi})-MIN($D${lo}:$D${hi}))))')
    c.fill = OUT; c.font = Font(F, size=9); c.number_format = '0.000'
    # K2 : 통장조사 (0~1)
    c = ws.cell(row=r, column=6)
    c.fill = IN; c.border = BOX; c.number_format = '0.000'
    c.font = Font(F, size=9, color='0000FF')
    # K3 : 자료 고정값
    c = ws.cell(row=r, column=7, value=round(k3[code], 4))
    c.fill = OUT; c.font = Font(F, size=9); c.number_format = '0.000'
    # K4·K5 : 평정 평균
    for col, src in ((8, 'D'), (9, 'E')):
        c = ws.cell(row=r, column=col,
                    value=f"=IFERROR(_xlfn.SWITCH(ROUND(AVERAGEIF('3_평정입력'!$B$4:$B${RATE_END},$A{r},"
                          f"'3_평정입력'!${src}$4:${src}${RATE_END}),0),5,1,4,0.7,3,0.45,2,0.25,1,0.1,\"\"),\"\")")
        c.fill = OUT; c.font = Font(F, size=9); c.number_format = '0.000'
    # 최종점수 : 값이 있는 기준만 가중평균
    cols = ['E', 'F', 'G', 'H', 'I']
    num = '+'.join([f"IF(ISNUMBER({cols[k]}{r}),'2_집단가중치'!$D${4+k}*{cols[k]}{r},0)" for k in range(5)])
    den = '+'.join([f"IF(ISNUMBER({cols[k]}{r}),'2_집단가중치'!$D${4+k},0)" for k in range(5)])
    c = ws.cell(row=r, column=11, value=f'=IFERROR(({num})/({den}),"")')
    c.fill = OUT; c.font = Font(F, size=10, bold=True); c.number_format = '0.000'
    c = ws.cell(row=r, column=12, value=f'=IFERROR(RANK(K{r},$K${lo}:$K${hi}),"")')
    c.fill = OUT; c.font = Font(F, size=10); c.number_format = '0'
end = 3 + len(order)
notes = [
 '※ K1 : 5·6번 시트의 계층 AHP로 얻은 전역 가중치(분야 내 합 1)를 D열에 옮겨 적으면 분야 안에서 0~1로 자동 정규화됩니다.',
 '※ K2 : 통장 수요조사의 과제점수(0~100)를 100으로 나눈 값을 입력하십시오. 조사 전에는 비워 두십시오 — 그 기준을 빼고 가중치가 재정규화됩니다.',
 '※ K3 : 그 과제에 배치된 사업의 격차기여 유형(Ⅰ 1.0 / Ⅱ 0.5 / Ⅲ 0.3) 가중평균을 44개 안에서 정규화한 고정값입니다.',
 '※ K4·K5 : 3_평정입력의 평균을 5→1.00 / 4→0.70 / 3→0.45 / 2→0.25 / 1→0.10으로 환산한 값입니다.',
 '※ 순위는 분야 안에서 매깁니다. 분야별로 몇 개를 뽑을지는 진단 원표로 정한 쿼터를 따릅니다(ahp.py 출력).',
 '※ 진단 판정은 이 표의 기준에 들어가지 않습니다. 분야 간 쿼터 산정에 이미 쓰였으므로 다시 쓰면 이중 계산입니다.',
]
for k, t in enumerate(notes):
    ws.cell(row=end + 2 + k, column=1, value=t).font = Font(F, size=9, color='C00000' if k in (1, 5) else '555555')
ws.freeze_panes = 'A4'

wb.save('/root/ahp/AHP 응답입력·집계 서식.xlsx')
print('saved')
