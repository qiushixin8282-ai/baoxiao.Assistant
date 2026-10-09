"""审批流对接：把报销单推送到钉钉 / 企业微信机器人。

真实审批（待办、审批节点、回调）需企业应用凭证；此处实现最常用的
"群机器人 Webhook"通知：提交报销单后推送 Markdown 卡片，便于审批人查看。
"""

import base64
import hashlib
import hmac
import logging
import time
from typing import Any, Dict, List
from urllib.parse import quote_plus

from app.config import settings
from app.core.combination import invoice_amount

logger = logging.getLogger(__name__)


class ApprovalUnavailableError(RuntimeError):
    pass


def _dingtalk_url() -> str:
    url = settings.dingtalk_webhook
    if settings.dingtalk_secret:
        ts = str(round(time.time() * 1000))
        string_to_sign = f"{ts}\n{settings.dingtalk_secret}"
        hmac_code = hmac.new(
            settings.dingtalk_secret.encode("utf-8"),
            string_to_sign.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()
        sign = quote_plus(base64.b64encode(hmac_code))
        url += f"&timestamp={ts}&sign={sign}"
    return url


def _markdown(records: List[Dict[str, Any]], note: str = "", title: str = "报销单提交审批") -> str:
    total = 0.0
    lines = [f"### {title}", ""]
    for i, rec in enumerate(records, 1):
        c = (rec.get("fields") or {}).get("通用字段", {})
        s = (rec.get("fields") or {}).get("销售方信息", {})
        amount = invoice_amount(rec) or 0
        total += amount
        lines.append(f"{i}. {c.get('发票号码', '无号码')} · {s.get('名称', '')} · {amount:.2f} 元")
    lines += ["", f"**发票张数：** {len(records)}", f"**合计金额：** {total:.2f} 元"]
    if note:
        lines += ["", f"**备注：** {note}"]
    lines += ["", "> 由「小荷包报销助手」推送"]
    return "\n".join(lines)


def _post(url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    import requests

    resp = requests.post(url, json=payload, timeout=10)
    resp.raise_for_status()
    try:
        return resp.json()
    except Exception:  # pragma: no cover
        return {"raw": resp.text}


def submit(
    records: List[Dict[str, Any]],
    note: str = "",
    channel: str = "auto",
) -> Dict[str, Any]:
    """推送报销单到已配置的机器人。channel: auto|dingtalk|wecom。"""
    if not records:
        raise ValueError("没有可提交的发票")

    content = _markdown(records, note)
    channels = settings.approval_channels
    if channel != "auto":
        channels = [c for c in channels if c == channel]
    if not channels:
        raise ApprovalUnavailableError(
            "未配置审批机器人。请在 .env 中设置 DINGTALK_WEBHOOK 或 WECOM_WEBHOOK。"
        )

    results: Dict[str, Any] = {}
    for ch in channels:
        if ch == "dingtalk":
            results["dingtalk"] = _post(
                _dingtalk_url(),
                {"msgtype": "markdown", "markdown": {"title": "报销单提交审批", "text": content}},
            )
        elif ch == "wecom":
            results["wecom"] = _post(
                settings.wecom_webhook,
                {"msgtype": "markdown", "markdown": {"content": content}},
            )
    return {"channels": channels, "content": content, "results": results}
