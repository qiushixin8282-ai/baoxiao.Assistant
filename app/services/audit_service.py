"""报销审核服务：将发票字段与规则引擎、城市分级结合，做确定性校验。

确定性规则覆盖核心制度（票据规范、时效性、住宿标准），可离线运行；
配置了 LLM 时，可由路由层叠加"智能审核意见"。
"""

import logging
import re
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from app.core.city_tier import get_city_tier_label, get_hotel_limit

logger = logging.getLogger(__name__)

PASS, FAIL, WARN, SKIP = "pass", "fail", "warn", "skip"


def _to_amount(value: Any) -> Optional[float]:
    if value is None:
        return None
    match = re.search(r"-?\d+(?:\.\d+)?", str(value).replace(",", ""))
    return float(match.group()) if match else None


def _to_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y年%m月%d日", "%Y%m%d"):
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue
    match = re.search(r"(\d{4})\D(\d{1,2})\D(\d{1,2})", value)
    if match:
        try:
            return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        except ValueError:
            return None
    return None


def audit(
    fields: Dict[str, Dict[str, str]],
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """执行确定性审核，返回结构化结果。"""
    context = context or {}
    common = (fields or {}).get("通用字段", {})
    results: List[Dict[str, Any]] = []

    # 规则 4.1 发票要素完整
    missing = [k for k in ("发票号码", "开票日期", "价税合计") if common.get(k, "无") == "无"]
    results.append(
        {
            "rule_id": "审核制度_票据规范_4.1",
            "title": "发票要素完整",
            "status": FAIL if missing else PASS,
            "message": f"缺少要素：{'、'.join(missing)}" if missing else "发票号码、开票日期、价税合计齐全",
        }
    )

    # 规则 2.3 时效性（30 天内）
    invoice_date = _to_date(common.get("开票日期"))
    if invoice_date:
        delta = (date.today() - invoice_date).days
        results.append(
            {
                "rule_id": "审核制度_审核原则_2.3",
                "title": "报销时效性",
                "status": PASS if delta <= 30 else FAIL,
                "message": f"开票日期距今 {delta} 天，" + ("在 30 天内" if delta <= 30 else "已超过 30 天时效"),
            }
        )
    else:
        results.append(
            {
                "rule_id": "审核制度_审核原则_2.3",
                "title": "报销时效性",
                "status": SKIP,
                "message": "无法解析开票日期，跳过时效性校验",
            }
        )

    # 规则 T4.1 住宿标准
    amount = _to_amount(context.get("amount")) or _to_amount(common.get("价税合计"))
    city = context.get("city")
    nights = context.get("nights")
    if city and amount is not None:
        limit_per_night = get_hotel_limit(city)
        tier_label = get_city_tier_label(city)
        if nights:
            per_night = amount / float(nights)
            ok = per_night <= limit_per_night
            results.append(
                {
                    "rule_id": "差旅费_住宿标准_T4.1",
                    "title": "住宿费限额",
                    "status": PASS if ok else FAIL,
                    "message": f"{city}（{tier_label}）限额 {limit_per_night} 元/晚，"
                    f"实际 {per_night:.2f} 元/晚（{nights} 晚）",
                }
            )
        else:
            ok = amount <= limit_per_night
            results.append(
                {
                    "rule_id": "差旅费_住宿标准_T4.1",
                    "title": "住宿费限额",
                    "status": WARN,
                    "message": f"{city}（{tier_label}）限额 {limit_per_night} 元/晚，"
                    f"提供金额 {amount:.2f} 元但未提供住宿晚数，请补充",
                }
            )
    else:
        results.append(
            {
                "rule_id": "差旅费_住宿标准_T4.1",
                "title": "住宿费限额",
                "status": SKIP,
                "message": "未提供出差城市/金额，跳过住宿限额校验",
            }
        )

    failed = sum(1 for r in results if r["status"] == FAIL)
    warned = sum(1 for r in results if r["status"] == WARN)
    if failed:
        conclusion = "不通过"
    elif warned:
        conclusion = "需人工复核"
    else:
        conclusion = "通过"

    return {
        "results": results,
        "summary": {
            "total": len(results),
            "passed": sum(1 for r in results if r["status"] == PASS),
            "failed": failed,
            "warned": warned,
            "skipped": sum(1 for r in results if r["status"] == SKIP),
            "conclusion": conclusion,
        },
    }
