# -*- coding: utf-8 -*-
"""AHP 계산 — 가중치·일관성비율(CR)·전이성 검사

설계 근거는 「전문가 AHP 조사 개요」 6절 분석 방법을 따른다.
  · 가중치 : 고유벡터법
  · CI = (λmax − n)/(n − 1),  CR = CI / RI,  CR ≤ 0.10 통과
  · n = 2 인 블록은 CR이 정의되지 않으므로 척도 양극단 쏠림만 점검한다
  · n = 4 인 Ⅱ부는 자유도가 3으로 줄어 CR이 관대해지므로 전이성 검사를 병행한다
"""
from itertools import combinations

import numpy as np

from criteria import RI, CR_THRESHOLD


def pairs(n):
    return list(combinations(range(n), 2))


def matrix_from_signed(values, n):
    """부호 있는 값(-9…-3, 1, 3…9)을 역수행렬로 바꾼다.

    양수 = 왼쪽(i)이 더 중요 → A[i][j] = v
    음수 = 오른쪽(j)이 더 중요 → A[i][j] = 1/|v|
    """
    A = np.ones((n, n), dtype=float)
    for (i, j), v in zip(pairs(n), values):
        r = float(abs(v)) or 1.0
        A[i, j] = r if v >= 0 else 1.0 / r
        A[j, i] = 1.0 / A[i, j]
    return A


def priority(A):
    """(가중치, CR). n ≤ 2면 CR은 None."""
    n = A.shape[0]
    vals, vecs = np.linalg.eig(A)
    k = int(np.argmax(vals.real))
    lmax = float(vals[k].real)
    w = np.abs(vecs[:, k].real)
    w = w / w.sum()
    if n <= 2:
        return w, None
    ci = (lmax - n) / (n - 1)
    ri = RI.get(n, 0.0)
    cr = ci / ri if ri > 0 else None
    return w, cr


def transitivity_violations(values, labels):
    """삼각형 전수 검사. a>b 이고 b>c 인데 a≤c 이면 위반.

    n=4인 Ⅱ부는 무작위에 가까운 응답도 CR 0.10을 통과할 확률이 높다.
    CR만으로 판정하지 않기 위해 함께 본다. 삼각형 수 = nC3 (n=4이면 4개).
    """
    n = len(labels)
    A = matrix_from_signed(values, n)
    out = []
    for i, j, k in combinations(range(n), 3):
        for a, b, c in ((i, j, k), (i, k, j), (j, i, k)):
            if A[a, b] > 1 and A[b, c] > 1 and A[a, c] <= 1:
                out.append((labels[a], labels[b], labels[c]))
                break
    return out, len(list(combinations(range(n), 3)))


def extreme_flag(values):
    """2×2 블록용. 척도 양극단(±9)에 몰렸는지 점검."""
    return all(abs(v) == 9 for v in values) if values else False


def inconsistency_ranking(values, labels):
    """전체 판단구조와 가장 어긋나는 비교쌍 순서."""
    n = len(labels)
    A = matrix_from_signed(values, n)
    w, _ = priority(A)
    out = []
    for i, j in pairs(n):
        observed = A[i, j]
        expected = w[i] / w[j]
        out.append((abs(np.log(observed) - np.log(expected)), labels[i], labels[j]))
    return sorted(out, key=lambda x: x[0], reverse=True)


def cr_status(cr, n=None):
    """(판정, 설명)"""
    if cr is None:
        return "검정 제외", "비교항목이 2개인 블록은 일관성비율이 정의되지 않습니다."
    if cr <= CR_THRESHOLD:
        return "적정", f"CR = {cr:.3f} · 일관성 기준(0.10)을 충족합니다."
    return "재검토", f"CR = {cr:.3f} · 일부 판단의 재검토를 권고합니다."


def block_result(values, labels):
    """블록 하나의 진단 결과를 한 번에 돌려준다."""
    n = len(labels)
    A = matrix_from_signed(values, n)
    w, cr = priority(A)
    status, message = cr_status(cr, n)
    return {
        "n": n,
        "weights": [float(x) for x in w],
        "cr": None if cr is None else float(cr),
        "status": status,
        "message": message,
        "extreme": extreme_flag(values) if n == 2 else False,
        "worst": [(a, b) for _s, a, b in inconsistency_ranking(values, labels)[:3]]
        if status == "재검토" else [],
    }


# ── 자기 점검 ────────────────────────────────────────────────
if __name__ == "__main__":
    # 완전일관 4×4 → CR = 0
    w, cr = priority(np.array([[1, 2, 4, 8], [.5, 1, 2, 4],
                               [.25, .5, 1, 2], [.125, .25, .5, 1]]))
    print("완전일관 4x4 CR =", round(cr, 6), "(0이어야 함)")

    # Saaty 교과서 3×3 → CR ≒ 0.033  (A=[[1,3,5],[1/3,1,3],[1/5,1/3,1]])
    _, cr3 = priority(np.array([[1, 3, 5], [1 / 3, 1, 3], [1 / 5, 1 / 3, 1]]))
    print("교과서 3x3 CR =", round(cr3, 3), "(0.033 근처)")

    # 전이성 위반 : A>B, B>C 인데 C>A
    vals = [3, -3, 3]          # (A,B)=A우세, (A,C)=C우세, (B,C)=B우세
    v, tot = transitivity_violations(vals, ["A", "B", "C"])
    print(f"전이성 삼각형 {tot}개 중 위반 {len(v)}건 : {v}")

    print("RI[4] =", RI[4], "(0.90이어야 함)")
