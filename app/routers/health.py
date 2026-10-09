"""健康检查与运行信息。"""

from fastapi import APIRouter, Depends

from app.config import settings
from app.services.workspace import Workspace, get_workspace

router = APIRouter(tags=["system"])


@router.get("/health")
def health(ws: Workspace = Depends(get_workspace)) -> dict:
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.version,
        "workspace": ws.id,
        "llm_configured": settings.llm_configured,
        "model": settings.openai_model,
        "ocr_enabled": settings.ocr_enabled,
        "ocr_lang": settings.ocr_lang,
        "rules_count": len(ws.rules.get_all_rules()),
        "invoices_count": len(ws.store.list()),
    }
