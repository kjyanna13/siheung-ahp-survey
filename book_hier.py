# -*- coding: utf-8 -*-
"""집계 서식에 「분야 내 계층 AHP」 시트를 추가한다."""
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter as CL
from hierdata import STRAT, FIELDS, blocks, pairs, n_pairs
from taskdata import TASKS

F = '맑은 고딕'
HDR = PatternFill('solid', fgColor='1F3864')
SUB = PatternFill('solid', fgColor='E8EDF5')
BLK = PatternFill('solid', fgColor='DCE6F1')
IN = PatternFill('solid', fgColor='FFF9E0')
OUT = PatternFill('solid', fgColor='F2F2F2')
thin = Side(style='thin', color='BBBBBB')
BOX = Border(left=thin, right=thin, top=thin, bottom=thin)
RI = {2: None, 3: 0.58, 4: 0.90, 5: 1.12}
NRESP = 8                       # 분야당 응답자 입력 행 수


def ahp_formulas(n, R, r):
    """n×n 비교행렬의 가중치·λmax 수식. R = 비율 셀 주소 리스트(쌍 순서)"""
    idx = {}
    for k, (i, j) in enumerate(pairs(n)):
        idx[(i, j)] = R[k]

    def a(i, j):
        if i == j:
            return '1'
        return idx[(i, j)] if i < j else f'1/{idx[(j, i)]}'

    gm = [f"({'*'.join(a(i, j) for j in range(n))})^(1/{n})" for i in range(n)]
    return gm


def build(path_in, path_out):
    wb = openpyxl.load_workbook(path_in)
    ws = wb.create_sheet('5_계층AHP입력', 3)
    ws.column_dimensions['A'].width = 11
    ws.column_dimensions['B'].width = 12
    for i in range(3, 3 + 15):
        ws.column_dimensions[CL(i)].width = 6.5
    c = ws.cell(row=1, column=1, value='⑥ 분야 내 계층 AHP 입력  —  노란 칸(H1~Hn)에만 입력하십시오')
    c.font = Font(F, size=13, bold=True, color='FFFFFF'); c.fill = HDR
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=20)
    ws.row_dimensions[1].height = 26
    ws.cell(row=2, column=1, value='왼쪽 항목에 ○ → 그 숫자 / 오른쪽 항목에 ○ → 음수 / 가운데 1 → 1').font = Font(F, size=9, color='C00000')

    row = 4
    summary_ranges = {}          # field -> {block: (첫행, 끝행, 가중치 시작열)}
    for field in FIELDS:
        lay = blocks(field)
        npair = n_pairs(field)
        # 분야 머리
        c = ws.cell(row=row, column=1, value=f'[{field}]  비교 {npair}문항 / 블록 {len(lay)}개')
        c.font = Font(F, size=11, bold=True); c.fill = BLK
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=20)
        row += 1
        # 문항 안내
        no = 0
        guide = []
        for code, name, items, labels in lay:
            ps = []
            for _ in pairs(len(items)):
                no += 1
                ps.append(no)
            guide.append(f"{'전략 간' if code=='STRAT' else name.split(' ')[0]}: H{ps[0]}~H{ps[-1]}"
                         if len(ps) > 1 else
                         f"{'전략 간' if code=='STRAT' else name.split(' ')[0]}: H{ps[0]}")
        ws.cell(row=row, column=1, value='  ' + '   |   '.join(guide)).font = Font(F, size=9, color='555555')
        row += 1
        # 헤더
        hdr = ['전문가', '분야'] + [f'H{k+1}' for k in range(npair)]
        col_after = 3 + npair + 1
        for code, name, items, labels in lay:
            hdr += ['']
            hdr += [f'{code}·w{k+1}' for k in range(len(items))]
            hdr += [f'{code}·CR']
        hdr += ['', '판정']
        for k, v in enumerate(hdr):
            cc = ws.cell(row=row, column=1 + k, value=v)
            cc.font = Font(F, size=8, bold=True); cc.fill = SUB
            cc.alignment = Alignment(horizontal='center', wrap_text=True)
            cc.border = BOX
            if k >= 2:
                ws.column_dimensions[CL(1 + k)].width = 8
        hdr_row = row
        row += 1
        first = row
        cr_cols, w_cols = [], {}
        for r in range(first, first + NRESP):
            ws.cell(row=r, column=1, value=f'{field[:2]}{r-first+1:02d}').font = Font(F, size=9)
            ws.cell(row=r, column=2, value=field).font = Font(F, size=9)
            for k in range(npair):
                cc = ws.cell(row=r, column=3 + k)
                cc.fill = IN; cc.border = BOX; cc.font = Font(F, size=9, color='0000FF')
                cc.alignment = Alignment(horizontal='center')
            # 비율 (보조열, 오른쪽 끝)
            ratio_start = 60
            for k in range(npair):
                p = CL(3 + k)
                cc = ws.cell(row=r, column=ratio_start + k,
                             value=f'=IF({p}{r}="","",IF({p}{r}>=0,ABS({p}{r}),1/ABS({p}{r})))')
                cc.font = Font(F, size=7, color='BBBBBB'); cc.number_format = '0.000'
            Rall = [CL(ratio_start + k) + str(r) for k in range(npair)]
            # 블록별 계산
            cur, gm_start, ptr = col_after, 120, 0
            crs = []
            for code, name, items, labels in lay:
                n = len(items)
                m = len(pairs(n))
                R = Rall[ptr:ptr + m]; ptr += m
                gm = ahp_formulas(n, R, r)
                gcols = []
                for i in range(n):
                    cc = ws.cell(row=r, column=gm_start, value=f'=IF({R[0]}="","",{gm[i]})')
                    cc.font = Font(F, size=7, color='DDDDDD'); cc.number_format = '0.0000'
                    gcols.append(CL(gm_start) + str(r)); gm_start += 1
                gsum = f'SUM({gcols[0]}:{gcols[-1]})'
                wcols = []
                for i in range(n):
                    cc = ws.cell(row=r, column=cur, value=f'=IF({gcols[0]}="","",{gcols[i]}/{gsum})')
                    cc.fill = OUT; cc.font = Font(F, size=8, bold=True); cc.number_format = '0.000'
                    wcols.append(CL(cur) + str(r)); cur += 1
                # λmax → CR
                if RI[n] is None:
                    cc = ws.cell(row=r, column=cur, value='—')
                    cc.fill = OUT; cc.font = Font(F, size=8, color='999999')
                    cc.alignment = Alignment(horizontal='center')
                else:
                    aw = []
                    for i in range(n):
                        terms = []
                        for j in range(n):
                            if i == j:
                                terms.append(wcols[j])
                            elif i < j:
                                terms.append(f'{R[pairs(n).index((i,j))]}*{wcols[j]}')
                            else:
                                terms.append(f'{wcols[j]}/{R[pairs(n).index((j,i))]}')
                        aw.append(f'({"+".join(terms)})/{wcols[i]}')
                    lam = f'(({"+".join(aw)})/{n})'
                    cc = ws.cell(row=r, column=cur,
                                 value=f'=IF({gcols[0]}="","",({lam}-{n})/{n-1}/{RI[n]})')
                    cc.fill = OUT; cc.font = Font(F, size=8); cc.number_format = '0.000'
                    crs.append(CL(cur) + str(r))
                w_cols.setdefault(code, []).append(wcols)
                cur += 2      # CR 칸 1 + 다음 블록 앞 빈 칸 1
            # 판정
            if crs:
                cond = ','.join(f'IF({x}="",0,{x})' for x in crs)
                cc = ws.cell(row=r, column=cur + 1,
                             value=f'=IF({Rall[0]}="","",IF(MAX({",".join(crs)})<=0.1,"채택","제외"))')
            else:
                cc = ws.cell(row=r, column=cur + 1,
                             value=f'=IF({Rall[0]}="","","검정불가")')
            cc.fill = OUT; cc.font = Font(F, size=9, bold=True)
            cc.alignment = Alignment(horizontal='center')
            judge_col = cur + 1
        summary_ranges[field] = dict(first=first, last=first + NRESP - 1,
                                     judge=judge_col, w=w_cols, hdr=hdr_row)
        row = first + NRESP + 2

    # ── 집단 종합 + 과제 전역 가중치
    ws2 = wb.create_sheet('6_계층결과', 4)
    for i, wdt in enumerate([12, 34, 11, 9, 30, 11, 11], 1):
        ws2.column_dimensions[CL(i)].width = wdt
    c = ws2.cell(row=1, column=1, value='⑦ 계층 AHP 결과  —  전략 가중치 × 과제 국지 가중치 = 전역 가중치(분야 내 합 1)')
    c.font = Font(F, size=13, bold=True, color='FFFFFF'); c.fill = HDR
    ws2.merge_cells(start_row=1, start_column=1, end_row=1, end_column=7)
    ws2.row_dimensions[1].height = 26
    for k, v in enumerate(['분야', '전략', '전략 가중치', '코드', '핵심과제', '국지 가중치', '전역 가중치']):
        cc = ws2.cell(row=3, column=1 + k, value=v)
        cc.font = Font(F, size=9, bold=True); cc.fill = SUB
        cc.alignment = Alignment(horizontal='center'); cc.border = BOX
    r2 = 4
    for field in FIELDS:
        S = STRAT[field]
        for si, (scode, sname, tasks) in enumerate(S):
            for ti, t in enumerate(tasks):
                ws2.cell(row=r2, column=1, value=field).font = Font(F, size=9)
                ws2.cell(row=r2, column=2, value=sname).font = Font(F, size=9)
                ws2.cell(row=r2, column=4, value=t).font = Font(F, size=9, bold=True)
                ws2.cell(row=r2, column=5, value=TASKS[t][1]).font = Font(F, size=9)
                for col in (3, 6, 7):
                    cc = ws2.cell(row=r2, column=col)
                    cc.fill = IN; cc.border = BOX; cc.number_format = '0.0000'
                    cc.font = Font(F, size=9, color='0000FF')
                r2 += 1
    ws2.cell(row=r2 + 1, column=1,
             value='※ 전략·국지·전역 가중치는 ahp.py(또는 hier.py)가 산출한 ahp_hierarchy.csv 값을 옮겨 적으십시오.').font = Font(F, size=9, color='C00000')
    ws2.cell(row=r2 + 2, column=1,
             value='※ 5_계층AHP입력 시트의 블록별 가중치·CR은 현장에서 즉시 확인하기 위한 것입니다. 응답자 간 종합(AIP 기하평균)은 스크립트가 수행합니다.').font = Font(F, size=9, color='555555')
    ws2.cell(row=r2 + 3, column=1,
             value='※ CR 칸이 「—」인 블록은 항목이 2개뿐이어서 일관성 검정이 불가능한 경우입니다. 응답자 간 방향 일치율로 대신 확인하십시오(스크립트가 출력).').font = Font(F, size=9, color='555555')

    wb.save(path_out)
    return path_out


if __name__ == '__main__':
    p = build('AHP 응답입력·집계 서식.xlsx', 'AHP 응답입력·집계 서식.xlsx')
    print('saved', p)
