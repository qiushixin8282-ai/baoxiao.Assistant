"""发票去重与最优组合。

- 去重：按（发票代码, 发票号码, 价税合计）识别重复发票。
- 组合：从一组发票中选出子集，使其价税合计尽可能接近目标报销金额。
  小规模用 meet-in-the-middle 精确求解，规模过大时退化为贪心。
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

MAX_EXACT_N = 34  # meet-in-the-middle 可承受的发票张数上限


def _to_amount(value: Any) -> Optional[float]:
    if value is None:
        return None
    match = re.search(r"-?\d+(?:\.\d+)?", str(value).replace(",", ""))
    return float(match.group()) if match else None


def invoice_amount(record_or_fields: Dict[str, Any]) -> Optional[float]:
    """从发票记录或字段字典中取价税合计。"""
    fields = record_or_fields.get("fields", record_or_fields)
    return _to_amount((fields or {}).get("通用字段", {}).get("价税合计"))


def invoice_signature(record_or_fields: Dict[str, Any]) -> Tuple[str, str, str]:
    fields = record_or_fields.get("fields", record_or_fields)
    common = (fields or {}).get("通用字段", {})
    return (
        (common.get("发票代码") or "").strip(),
        (common.get("发票号码") or "").strip(),
        (common.get("价税合计") or "").strip(),
    )


def find_duplicates(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """返回重复发票分组，每组含 signature 与 records。"""
    groups: Dict[Tuple[str, str, str], List[Dict[str, Any]]] = {}
    for rec in records:
        sig = invoice_signature(rec)
        if not any(sig):
            continue
        groups.setdefault(sig, []).append(rec)

    result = []
    for sig, items in groups.items():
        if len(items) > 1:
            result.append(
                {
                    "signature": {"发票代码": sig[0], "发票号码": sig[1], "价税合计": sig[2]},
                    "count": len(items),
                    "records": items,
                }
            )
    return result


def _score(diff_cents: int, tol_cents: int, count: int) -> Tuple:
    """越小越优：优先落在容差内、其次更接近目标、再优先不超支、最后张数更少。"""
    dist = abs(diff_cents)
    out_of_range = 0 if dist <= tol_cents else 1
    extra = dist if out_of_range == 0 else dist - tol_cents
    under = 1 if diff_cents < 0 else 0  # 同分时优先不欠（>=0）
    return (out_of_range, extra, under, count)


def _greedy(cents: List[int], tgt: int, tol: int) -> Optional[Tuple[int, List[int]]]:
    """贪心：降序尽量填充到不超过目标+容差，再尝试用单张替换逼近。"""
    order = sorted(range(len(cents)), key=lambda i: cents[i], reverse=True)
    chosen: List[int] = []
    total = 0
    cap = tgt + tol
    for i in order:
        if total + cents[i] <= cap:
            chosen.append(i)
            total += cents[i]
    if not chosen:
        # 退化为单张最接近
        best_i = min(range(len(cents)), key=lambda i: abs(cents[i] - tgt))
        return cents[best_i], [best_i]
    return total, sorted(chosen)


def _meet_in_middle(cents: List[int], tgt: int, tol: int) -> Tuple[int, List[int]]:
    n = len(cents)
    mid = n // 2
    left = cents[:mid]
    right = cents[mid:]

    def enumerate_subsets(arr: List[int]) -> List[Tuple[int, int]]:
        subs = [(0, 0)]
        for idx, val in enumerate(arr):
            subs += [(s + val, mask | (1 << idx)) for s, mask in subs]
        return subs

    left_subs = enumerate_subsets(left)
    right_subs = enumerate_subsets(right)
    right_subs.sort(key=lambda x: x[0])
    right_sums = [s for s, _ in right_subs]

    import bisect

    best_score = None
    best_total = 0
    best_mask_left = 0
    best_mask_right = 0

    for ls, lmask in left_subs:
        # 理想右半和 = tgt - ls，二分找最近几个
        pos = bisect.bisect_left(right_sums, tgt - ls)
        last = len(right_sums) - 1
        for cand in {max(0, pos - 1), min(pos, last), min(pos + 1, last)}:
            rs, rmask = right_subs[cand]
            total = ls + rs
            diff = total - tgt
            count = bin(lmask).count("1") + bin(rmask).count("1")
            sc = _score(diff, tol, count)
            if best_score is None or sc < best_score:
                best_score = sc
                best_total = total
                best_mask_left = lmask
                best_mask_right = rmask

    indices = [i for i in range(mid) if best_mask_left >> i & 1]
    indices += [mid + i for i in range(n - mid) if best_mask_right >> i & 1]
    return best_total, sorted(indices)


def select_combination(
    amounts: List[float],
    target: float,
    tolerance: float = 0.0,
) -> Optional[Dict[str, Any]]:
    """选择子集使合计最接近目标。返回 {indices, sum, diff, exact}。"""
    if not amounts:
        return None
    cents = [round(a * 100) for a in amounts]
    tgt = round(target * 100)
    tol = round(tolerance * 100)

    if len(cents) <= MAX_EXACT_N:
        total, indices = _meet_in_middle(cents, tgt, tol)
    else:
        logger.info("发票张数 %d 超过精确上限，使用贪心算法", len(cents))
        total, indices = _greedy(cents, tgt, tol)

    return {
        "indices": indices,
        "sum": round(total / 100, 2),
        "diff": round((total - tgt) / 100, 2),
        "exact": total == tgt,
    }
