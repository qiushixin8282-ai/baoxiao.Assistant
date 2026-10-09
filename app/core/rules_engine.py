"""报销规则引擎。

改编自 megemini/AuditAgent 的 core/reimbursement_rules.py（Apache-2.0），
改为从 rules/ 目录加载规则，并提供结构化查询接口。
"""

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.config import DEFAULT_RULES_FILE

logger = logging.getLogger(__name__)

HEADER = "一级主题|二级主题|条款编号|条款标题|正文|关联附件"


@dataclass
class ReimbursementRule:
    """单条报销规则。"""

    category: str
    subcategory: str
    clause_id: str
    title: str
    content: str
    attachment: str = ""
    rule_id: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.rule_id:
            self.rule_id = f"{self.category}_{self.subcategory}_{self.clause_id}".replace(" ", "_")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class RulesEngine:
    """规则解析、检索与管理。"""

    def __init__(self, rules_file: Optional[Path] = None) -> None:
        self.rules: List[ReimbursementRule] = []
        self.categories: Dict[str, List[str]] = {}
        self.path: Optional[Path] = Path(rules_file) if rules_file else None
        if self.path and self.path.exists():
            self.load_from_file(self.path)

    # ---- 持久化 ----
    def to_text(self) -> str:
        lines = [HEADER, ""]
        for r in self.rules:
            lines.append(
                "|".join(
                    [r.category, r.subcategory, r.clause_id, r.title, r.content, r.attachment or ""]
                )
            )
        return "\n".join(lines) + "\n"

    def save(self, file_path: Optional[Path] = None) -> bool:
        target = Path(file_path) if file_path else self.path
        if target is None:
            return False
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(self.to_text(), encoding="utf-8")
            return True
        except Exception as exc:  # pragma: no cover
            logger.error("保存规则失败 %s: %s", target, exc)
            return False

    # ---- 加载 ----
    def load_from_file(self, file_path: Path) -> bool:
        try:
            text = Path(file_path).read_text(encoding="utf-8")
            return self.parse_rules_from_text(text)
        except Exception as exc:  # pragma: no cover
            logger.error("读取规则文件失败 %s: %s", file_path, exc)
            return False

    def parse_rules_from_text(self, text: str) -> bool:
        new_rules: List[ReimbursementRule] = []
        for line_num, raw in enumerate(text.splitlines(), 1):
            line = raw.strip()
            if not line or line.startswith("一级主题") or line.startswith("#"):
                continue
            parts = line.split("|")
            if len(parts) < 5:
                logger.debug("第%d行格式不正确，跳过", line_num)
                continue
            parts += [""] * (6 - len(parts))
            try:
                new_rules.append(
                    ReimbursementRule(
                        category=parts[0].strip(),
                        subcategory=parts[1].strip(),
                        clause_id=parts[2].strip(),
                        title=parts[3].strip(),
                        content=parts[4].strip(),
                        attachment=parts[5].strip(),
                    )
                )
            except Exception as exc:  # pragma: no cover
                logger.warning("第%d行解析失败: %s", line_num, exc)

        if not new_rules:
            return False
        self.rules.extend(new_rules)
        self._update_categories()
        return True

    def replace_from_text(self, text: str) -> int:
        self.rules = []
        self.categories = {}
        self.parse_rules_from_text(text)
        return len(self.rules)

    # ---- 检索 ----
    def _update_categories(self) -> None:
        self.categories.clear()
        for rule in self.rules:
            self.categories.setdefault(rule.category, [])
            if rule.subcategory not in self.categories[rule.category]:
                self.categories[rule.category].append(rule.subcategory)

    def get_all_rules(self) -> List[ReimbursementRule]:
        return list(self.rules)

    def get_rule(self, rule_id: str) -> Optional[ReimbursementRule]:
        for rule in self.rules:
            if rule.rule_id == rule_id:
                return rule
        return None

    def get_rules_by_category(self, category: str) -> List[ReimbursementRule]:
        return [r for r in self.rules if r.category == category]

    def search_rules(self, keyword: str) -> List[ReimbursementRule]:
        kw = keyword.lower()
        return [
            r
            for r in self.rules
            if kw in r.title.lower()
            or kw in r.content.lower()
            or kw in r.category.lower()
            or kw in r.subcategory.lower()
        ]

    # ---- 增删改 ----
    def add_rule(self, rule: ReimbursementRule) -> bool:
        if self.get_rule(rule.rule_id):
            return False
        self.rules.append(rule)
        self._update_categories()
        return True

    def update_rule(self, rule_id: str, **kwargs: Any) -> bool:
        rule = self.get_rule(rule_id)
        if not rule:
            return False
        for key, value in kwargs.items():
            if hasattr(rule, key):
                setattr(rule, key, value)
        self._update_categories()
        return True

    def delete_rule(self, rule_id: str) -> bool:
        for i, rule in enumerate(self.rules):
            if rule.rule_id == rule_id:
                del self.rules[i]
                self._update_categories()
                return True
        return False

    # ---- 导出 ----
    def get_rules_for_ai_prompt(self, category: Optional[str] = None, max_rules: int = 50) -> str:
        rules = self.get_rules_by_category(category) if category else self.rules
        rules = rules[:max_rules]
        if not rules:
            return "当前未配置报销规则"

        grouped: Dict[str, List[ReimbursementRule]] = {}
        for rule in rules:
            grouped.setdefault(rule.category, []).append(rule)

        lines = ["【报销规则】"]
        for cat, cat_rules in grouped.items():
            lines.append(f"\n【{cat}】")
            for rule in cat_rules:
                lines.append(f"  • {rule.title}：{rule.content}")
        return "\n".join(lines)

    def get_statistics(self) -> Dict[str, Any]:
        return {
            "total_rules": len(self.rules),
            "categories": list(self.categories.keys()),
            "rules_by_category": {
                cat: len(self.get_rules_by_category(cat)) for cat in self.categories
            },
        }

    def export_json(self, file_path: Path) -> bool:
        try:
            Path(file_path).write_text(
                json.dumps([r.to_dict() for r in self.rules], ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            return True
        except Exception as exc:  # pragma: no cover
            logger.error("导出规则失败: %s", exc)
            return False


# 全局实例，默认加载内置规则
rules_engine = RulesEngine(DEFAULT_RULES_FILE)


def get_rules_engine() -> RulesEngine:
    return rules_engine
