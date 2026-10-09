"""系统能力检查接口。"""

import importlib.util

from fastapi import APIRouter

from app.config import settings

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/ocr")
def ocr_status() -> dict:
    """报告 OCR 依赖安装状态与安装方式。"""
    has_paddleocr = importlib.util.find_spec("paddleocr") is not None
    has_paddle = importlib.util.find_spec("paddle") is not None
    available = has_paddleocr and has_paddle
    return {
        "available": available,
        "paddleocr_installed": has_paddleocr,
        "paddle_installed": has_paddle,
        "enabled": settings.ocr_enabled,
        "lang": settings.ocr_lang,
        "install_command": "python scripts/install_ocr.py",
        "gpu_install_command": "python scripts/install_ocr.py gpu",
        "hint": "未安装时图片发票无法识别；文字版 PDF、规则、审核、组合、导出台账不受影响。",
    }
