"""发票识别接口。"""

from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.core.invoice_recognizer import FIELD_KEYS
from app.services.invoice_service import process_invoice, save_upload

router = APIRouter(prefix="/invoices", tags=["invoices"])


@router.get("/schema")
def invoice_schema() -> dict:
    """返回发票字段结构，供前端渲染。"""
    return {"fields": FIELD_KEYS}


@router.post("/recognize")
async def recognize(
    file: UploadFile = File(...),
    lang: Optional[str] = Form(None),
) -> dict:
    """上传发票图片/PDF，返回 OCR 原文与结构化字段。"""
    content = await file.read()
    try:
        path = save_upload(file.filename or "invoice", content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    result = process_invoice(path, lang=lang)
    if not result.get("ok"):
        raise HTTPException(status_code=503, detail=result.get("error", "识别失败"))
    return result
