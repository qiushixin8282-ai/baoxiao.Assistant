"""应用配置。所有配置均可通过环境变量或 .env 覆盖。"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RULES_DIR = BASE_DIR / "rules"
WEB_DIR = BASE_DIR / "web"
UPLOAD_DIR = DATA_DIR / "uploads"
OUTPUT_DIR = DATA_DIR / "outputs"

# 尝试加载 .env（可选依赖）
try:
    from dotenv import load_dotenv

    load_dotenv(BASE_DIR / ".env")
except Exception:  # pragma: no cover - dotenv 是可选的
    pass


def _bool(value: str, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class Settings:
    app_name: str = "小荷包报销助手"
    version: str = "0.1.0"

    # LLM（OpenAI 兼容接口）
    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    openai_base_url: str = field(
        default_factory=lambda: os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    )
    openai_model: str = field(default_factory=lambda: os.getenv("OPENAI_MODEL", "gpt-4o-mini"))

    # OCR
    ocr_lang: str = field(default_factory=lambda: os.getenv("OCR_LANG", "ch"))
    ocr_enabled: bool = field(default_factory=lambda: _bool(os.getenv("OCR_ENABLED"), True))

    # 审批流 Webhook（钉钉机器人 / 企业微信机器人）
    dingtalk_webhook: str = field(default_factory=lambda: os.getenv("DINGTALK_WEBHOOK", ""))
    dingtalk_secret: str = field(default_factory=lambda: os.getenv("DINGTALK_SECRET", ""))
    wecom_webhook: str = field(default_factory=lambda: os.getenv("WECOM_WEBHOOK", ""))

    # 存储
    upload_dir: Path = UPLOAD_DIR
    output_dir: Path = OUTPUT_DIR
    rules_dir: Path = RULES_DIR
    web_dir: Path = WEB_DIR

    # CORS，逗号分隔
    cors_origins: List[str] = field(
        default_factory=lambda: [
            o.strip()
            for o in os.getenv("CORS_ORIGINS", "*").split(",")
            if o.strip()
        ]
    )

    max_upload_mb: int = field(default_factory=lambda: int(os.getenv("MAX_UPLOAD_MB", "20")))

    @property
    def llm_configured(self) -> bool:
        return bool(self.openai_api_key)

    @property
    def approval_channels(self) -> List[str]:
        channels = []
        if self.dingtalk_webhook:
            channels.append("dingtalk")
        if self.wecom_webhook:
            channels.append("wecom")
        return channels

    def ensure_dirs(self) -> None:
        for d in (self.upload_dir, self.output_dir, self.rules_dir):
            d.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_dirs()

DEFAULT_RULES_FILE = settings.rules_dir / "default_rules.txt"
