"""多用户工作区：为每个用户 / 团队隔离规则库与发票清单。

通过请求头 `X-Workspace-Id` 区分工作区，未提供时使用 `default`。
每个工作区独立持久化于 data/workspaces/<id>/ 下。
"""

import logging
import re
from pathlib import Path
from typing import Dict

from fastapi import Header, HTTPException

from app.config import DATA_DIR, DEFAULT_RULES_FILE
from app.core.rules_engine import RulesEngine
from app.services.store import InvoiceStore

logger = logging.getLogger(__name__)

WORKSPACES_DIR = DATA_DIR / "workspaces"
DEFAULT_WORKSPACE = "default"
_WS_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


class Workspace:
    def __init__(self, workspace_id: str) -> None:
        self.id = workspace_id
        self.dir = WORKSPACES_DIR / workspace_id
        self.dir.mkdir(parents=True, exist_ok=True)

        self.rules_file = self.dir / "rules.txt"
        if not self.rules_file.exists():
            template = DEFAULT_RULES_FILE
            content = template.read_text(encoding="utf-8") if template.exists() else ""
            self.rules_file.write_text(content, encoding="utf-8")

        self.rules = RulesEngine(self.rules_file)
        self.store = InvoiceStore(self.dir / "invoices.json")

    def reset_rules(self) -> int:
        self.rules.rules = []
        self.rules.categories = {}
        if DEFAULT_RULES_FILE.exists():
            self.rules.parse_rules_from_text(DEFAULT_RULES_FILE.read_text(encoding="utf-8"))
        self.rules.save()
        return len(self.rules.get_all_rules())


class WorkspaceManager:
    def __init__(self) -> None:
        self._cache: Dict[str, Workspace] = {}

    def get(self, workspace_id: str) -> Workspace:
        if not _WS_RE.match(workspace_id or ""):
            raise ValueError("工作区 ID 只能是字母、数字、下划线或连字符，长度 1-64")
        if workspace_id not in self._cache:
            self._cache[workspace_id] = Workspace(workspace_id)
        return self._cache[workspace_id]

    def list(self) -> list:
        if not WORKSPACES_DIR.exists():
            return []
        return sorted(p.name for p in WORKSPACES_DIR.iterdir() if p.is_dir())

    def delete(self, workspace_id: str) -> bool:
        if not _WS_RE.match(workspace_id or ""):
            return False
        self._cache.pop(workspace_id, None)
        target = WORKSPACES_DIR / workspace_id
        if not target.exists():
            return False
        import shutil

        shutil.rmtree(target, ignore_errors=True)
        return True


manager = WorkspaceManager()


def get_workspace(x_workspace_id: str = Header(DEFAULT_WORKSPACE)) -> Workspace:
    """FastAPI 依赖：根据请求头解析工作区。"""
    try:
        return manager.get(x_workspace_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
