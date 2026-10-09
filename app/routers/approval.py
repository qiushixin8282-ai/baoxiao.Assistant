"""审批流对接接口。"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.config import settings
from app.services.approval_service import ApprovalUnavailableError, submit
from app.services.workspace import Workspace, get_workspace

router = APIRouter(prefix="/approval", tags=["approval"])


class SubmitRequest(BaseModel):
    invoice_ids: Optional[List[str]] = None
    note: str = ""
    channel: str = "auto"  # auto | dingtalk | wecom


@router.get("/config")
def approval_config() -> dict:
    return {
        "channels": settings.approval_channels,
        "dingtalk_configured": bool(settings.dingtalk_webhook),
        "wecom_configured": bool(settings.wecom_webhook),
        "hint": "在 .env 中配置 DINGTALK_WEBHOOK / WECOM_WEBHOOK（群机器人 Webhook）后即可推送。",
    }


@router.post("/submit")
def submit_approval(req: SubmitRequest, ws: Workspace = Depends(get_workspace)) -> dict:
    records = ws.store.get_many(req.invoice_ids) if req.invoice_ids else ws.store.list()
    if not records:
        raise HTTPException(status_code=400, detail="没有可提交的发票")
    try:
        return submit(records, note=req.note, channel=req.channel)
    except ApprovalUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
