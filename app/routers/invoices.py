"""发票识别与发票清单接口。"""

from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile

from app.core.combination import find_duplicates
from app.core.invoice_recognizer import FIELD_KEYS
from app.services.invoice_service import process_invoice, save_upload
from app.services.store import get_invoice_store

router = APIRouter(prefix="/invoices", tags=["invoices"])


@router.get("/schema")
def invoice_schema() -> dict:
    """返回发票字段结构，供前端渲染。"""
    return {"fields": FIELD_KEYS}


@router.get("")
def list_invoices() -> dict:
    records = get_invoice_store().list()
    return {"count": len(records), "invoices": records}


@router.get("/duplicates")
def duplicates() -> dict:
    groups = find_duplicates(get_invoice_store().list())
    return {"duplicate_groups": len(groups), "groups": groups}


@router.delete("")
def clear_invoices() -> dict:
    return {"cleared": get_invoice_store().clear()}


@router.get("/{invoice_id}")
def get_invoice(invoice_id: str) -> dict:
    rec = get_invoice_store().get(invoice_id)
    if not rec:
        raise HTTPException(status_code=404, detail=f"未找到发票: {invoice_id}")
    return rec


@router.delete("/{invoice_id}")
def delete_invoice(invoice_id: str) -> dict:
    if not get_invoice_store().delete(invoice_id):
        raise HTTPException(status_code=404, detail=f"未找到发票: {invoice_id}")
    return {"deleted": invoice_id}


@router.post("/recognize")
async def recognize(
    file: UploadFile = File(...),
    lang: Optional[str] = Form(None),
    save: bool = Form(True),
) -> dict:
    """上传发票图片/PDF，返回 OCR 原文与结构化字段，并写入发票清单。"""
    content = await file.read()
    try:
        path = save_upload(file.filename or "invoice", content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    result = process_invoice(path, lang=lang)
    if not result.get("ok"):
        raise HTTPException(status_code=503, detail=result.get("error", "识别失败"))

    if save:
        record = get_invoice_store().add(
            result["fields"], filename=result.get("file"), engine=result.get("engine")
        )
        result["id"] = record["id"]
    return result
