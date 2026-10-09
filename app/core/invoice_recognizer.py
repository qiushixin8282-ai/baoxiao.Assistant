"""发票识别：OCR/PDF 文本提取 + LLM 结构化字段解析。

改编自 megemini/AuditAgent 的 core/invoice_core_llm.py（Apache-2.0）。
"""

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.llm_client import LLMClient, LLMUnavailableError, get_llm_client
from app.core.ocr_manager import OCRUnavailableError, get_ocr_manager

logger = logging.getLogger(__name__)

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}

FIELD_KEYS = {
    "通用字段": ["发票号码", "发票代码", "开票日期", "金额", "税额", "价税合计"],
    "购买方信息": ["名称", "纳税人识别号", "地址", "电话", "开户行", "开户行账号"],
    "销售方信息": ["名称", "纳税人识别号", "地址", "电话", "开户行", "开户行账号"],
    "商品信息": ["商品名称", "规格型号", "数量", "单价", "税率"],
    "其他信息": ["收款人", "复核", "开票人"],
}


def empty_result(placeholder: str = "无") -> Dict[str, Dict[str, str]]:
    return {cat: {k: placeholder for k in keys} for cat, keys in FIELD_KEYS.items()}


def extract_text_from_pdf(pdf_path: str) -> List[str]:
    """使用 PyMuPDF 抽取 PDF 文本。"""
    try:
        import fitz  # PyMuPDF，延迟导入
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("未安装 PyMuPDF，无法解析 PDF。请 `pip install PyMuPDF`。") from exc

    lines: List[str] = []
    doc = fitz.open(pdf_path)
    try:
        for page in doc:
            text = page.get_text()
            for line in text.split("\n"):
                if line.strip():
                    lines.append(line.strip())
    finally:
        doc.close()
    return lines


def _extract_prompt(ocr_content: str) -> str:
    return f"""请从以下发票 OCR 文本中提取结构化信息。如果某个字段不存在，请返回"无"。

注意：
1. 购买方与销售方信息分离提取。
2. "地址、电话"需拆分为地址、电话两个字段；"开户行及账号"需拆分为开户行、开户行账号。

OCR文本：
{ocr_content}

请仅以 JSON 返回，结构如下：
{{
  "通用字段": {{"发票号码": "", "发票代码": "", "开票日期": "", "金额": "", "税额": "", "价税合计": ""}},
  "购买方信息": {{"名称": "", "纳税人识别号": "", "地址": "", "电话": "", "开户行": "", "开户行账号": ""}},
  "销售方信息": {{"名称": "", "纳税人识别号": "", "地址": "", "电话": "", "开户行": "", "开户行账号": ""}},
  "商品信息": {{"商品名称": "", "规格型号": "", "数量": "", "单价": "", "税率": ""}},
  "其他信息": {{"收款人": "", "复核": "", "开票人": ""}}
}}"""


def _parse_json_block(content: str) -> Optional[dict]:
    start = content.find("{")
    end = content.rfind("}") + 1
    if start == -1 or end <= 0:
        return None
    try:
        return json.loads(content[start:end])
    except json.JSONDecodeError:
        return None


def normalize_fields(data: Optional[dict]) -> Dict[str, Dict[str, str]]:
    """把 LLM 返回的对象规整为固定结构，缺失字段填 '无'。"""
    result = empty_result()
    if not isinstance(data, dict):
        return result
    for cat, keys in FIELD_KEYS.items():
        cat_data = data.get(cat) or {}
        for key in keys:
            value = cat_data.get(key)
            if value is None or str(value).strip() == "":
                continue
            result[cat][key] = str(value).strip()

    # 简单的格式校验
    date = result["通用字段"]["开票日期"]
    if date != "无" and not re.search(r"\d{4}[-/年]\d{1,2}[-/月]\d{1,2}", date):
        result["通用字段"]["开票日期"] = "无"
    for key in ("金额", "税额", "价税合计"):
        value = result["通用字段"][key]
        if value != "无" and not re.search(r"[\d.]+", value):
            result["通用字段"][key] = "无"
    return result


def get_ocr_texts(file_path: str, lang: str = "ch") -> List[str]:
    path = Path(file_path)
    if path.suffix.lower() == ".pdf":
        return extract_text_from_pdf(file_path)
    if path.suffix.lower() in IMAGE_EXTS:
        return get_ocr_manager().extract_text(str(path), lang=lang)
    raise ValueError(f"不支持的文件类型: {path.suffix}")


def recognize_invoice(
    file_path: str,
    lang: str = "ch",
    llm: Optional[LLMClient] = None,
) -> Dict[str, Any]:
    """识别单张发票，返回 {fields, ocr_lines, engine}。"""
    llm = llm or get_llm_client()
    ocr_lines = get_ocr_texts(file_path, lang=lang)

    if not ocr_lines:
        return {"fields": empty_result(), "ocr_lines": [], "engine": "none", "warning": "未提取到任何文本"}

    try:
        content = llm.chat([{"role": "user", "content": _extract_prompt("\n".join(ocr_lines))}])
        fields = normalize_fields(_parse_json_block(content))
        return {"fields": fields, "ocr_lines": ocr_lines, "engine": "llm"}
    except LLMUnavailableError as exc:
        logger.warning("LLM 不可用，仅返回 OCR 原文: %s", exc)
        return {
            "fields": empty_result(),
            "ocr_lines": ocr_lines,
            "engine": "ocr-only",
            "warning": str(exc),
        }
