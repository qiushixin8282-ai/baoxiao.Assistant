"""健康检查与运行信息。"""

from fastapi import APIRouter

from app.config import settings
from app.core.rules_engine import get_rules_engine

router = APIRouter(tags=["system"])


@router.get("/health")
def health() -> dict:
    engine = get_rules_engine()
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.version,
        "llm_configured": settings.llm_configured,
        "model": settings.openai_model,
        "ocr_enabled": settings.ocr_enabled,
        "ocr_lang": settings.ocr_lang,
        "rules_count": len(engine.get_all_rules()),
    }
