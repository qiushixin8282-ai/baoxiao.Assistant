"""发票服务：保存上传文件并调用识别流程。"""

import logging
import uuid
from pathlib import Path
from typing import Any, Dict

from app.config import settings
from app.core.invoice_recognizer import recognize_invoice
from app.core.llm_client import LLMUnavailableError
from app.core.ocr_manager import OCRUnavailableError

logger = logging.getLogger(__name__)

ALLOWED_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp", ".pdf"}


def save_upload(filename: str, content: bytes) -> Path:
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTS:
        raise ValueError(f"不支持的文件类型: {ext or '未知'}")
    if len(content) > settings.max_upload_mb * 1024 * 1024:
        raise ValueError(f"文件超过 {settings.max_upload_mb}MB 限制")
    target = settings.upload_dir / f"{uuid.uuid4().hex}{ext}"
    target.write_bytes(content)
    return target


def process_invoice(file_path: Path, lang: str = None) -> Dict[str, Any]:
    lang = lang or settings.ocr_lang
    try:
        result = recognize_invoice(str(file_path), lang=lang)
    except (OCRUnavailableError, LLMUnavailableError) as exc:
        return {"ok": False, "error": str(exc), "file": file_path.name}
    result["ok"] = True
    result["file"] = file_path.name
    return result
