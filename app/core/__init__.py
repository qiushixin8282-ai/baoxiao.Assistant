"""核心领域模块：规则引擎、OCR、发票识别、LLM 客户端、城市分级。

本目录下的部分实现改编自开源项目 megemini/AuditAgent（Apache-2.0），
已针对小荷包报销助手进行裁剪与重构。
"""

from .rules_engine import RulesEngine, ReimbursementRule, rules_engine
from .city_tier import get_city_tier, get_city_tier_label

__all__ = [
    "RulesEngine",
    "ReimbursementRule",
    "rules_engine",
    "get_city_tier",
    "get_city_tier_label",
]
