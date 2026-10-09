"""报销审核接口。"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.audit_service import audit

router = APIRouter(prefix="/audit", tags=["audit"])


class AuditRequest(BaseModel):
    fields: Dict[str, Dict[str, str]]
    context: Optional[Dict[str, Any]] = None


@router.post("")
def run_audit(req: AuditRequest) -> dict:
    return audit(req.fields, req.context)
