"""发票记录存储（JSON 文件，轻量、本地优先）。

用于把识别结果持久化，供后续去重、组合、导出台账使用。
单进程场景下直接读写 JSON，简单可靠。
"""

import json
import logging
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.config import DATA_DIR

logger = logging.getLogger(__name__)

STORE_FILE = DATA_DIR / "invoices.json"
_LOCK = threading.RLock()


class InvoiceStore:
    def __init__(self, path: Path = STORE_FILE) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("[]", encoding="utf-8")

    def _read(self) -> List[Dict[str, Any]]:
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except Exception as exc:  # pragma: no cover
            logger.error("读取发票存储失败: %s", exc)
            return []

    def _write(self, records: List[Dict[str, Any]]) -> None:
        self.path.write_text(
            json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def list(self) -> List[Dict[str, Any]]:
        with _LOCK:
            return self._read()

    def get(self, invoice_id: str) -> Optional[Dict[str, Any]]:
        for rec in self.list():
            if rec["id"] == invoice_id:
                return rec
        return None

    def get_many(self, ids: List[str]) -> List[Dict[str, Any]]:
        wanted = set(ids)
        return [r for r in self.list() if r["id"] in wanted]

    def add(self, fields: Dict[str, Any], **meta: Any) -> Dict[str, Any]:
        record = {
            "id": uuid.uuid4().hex,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "fields": fields,
            **meta,
        }
        with _LOCK:
            records = self._read()
            records.append(record)
            self._write(records)
        return record

    def delete(self, invoice_id: str) -> bool:
        with _LOCK:
            records = self._read()
            kept = [r for r in records if r["id"] != invoice_id]
            if len(kept) == len(records):
                return False
            self._write(kept)
            return True

    def clear(self) -> int:
        with _LOCK:
            count = len(self._read())
            self._write([])
            return count


invoice_store = InvoiceStore()


def get_invoice_store() -> InvoiceStore:
    return invoice_store
