"""PaddleOCR 统一管理器（懒加载）。

改编自 megemini/AuditAgent 的 core/paddle_ocr_manager.py（Apache-2.0）。
paddleocr 属于重依赖，这里改为按需导入：未安装时给出明确错误而不是导入即崩溃。
"""

import logging
from typing import List

logger = logging.getLogger(__name__)


class OCRUnavailableError(RuntimeError):
    """PaddleOCR 未安装或初始化失败。"""


class PaddleOCRManager:
    def __init__(self) -> None:
        self._models = {}
        self._initialized = False

    def _load_backend(self):
        try:
            from paddleocr import PaddleOCR  # 延迟导入

            return PaddleOCR
        except Exception as exc:  # pragma: no cover - 依赖缺失
            raise OCRUnavailableError(
                "未安装 PaddleOCR。请执行 `pip install paddleocr paddlepaddle`，"
                "或设置 OCR_ENABLED=false 仅使用其他功能。"
            ) from exc

    def initialize(self, lang: str = "ch", use_textline_orientation: bool = True) -> None:
        if lang in self._models:
            return
        PaddleOCR = self._load_backend()
        logger.info("正在初始化 OCR 模型 (lang=%s)...", lang)
        self._models[lang] = PaddleOCR(lang=lang, use_textline_orientation=use_textline_orientation)
        self._initialized = True

    def extract_text(self, image_source, lang: str = "ch") -> List[str]:
        import numpy as np

        if lang not in self._models:
            self.initialize(lang=lang)
        if hasattr(image_source, "save"):  # PIL Image
            image_source = np.array(image_source)
        result = self._models[lang].ocr(image_source)
        return _parse_paddle_result(result)

    def close(self) -> None:
        self._models.clear()
        self._initialized = False


def _parse_paddle_result(result) -> List[str]:
    """兼容 PaddleOCR 2.x / 3.x 多种返回格式，统一取文本列表。"""
    if not result:
        return []
    # 3.x 字典格式
    if isinstance(result, dict):
        return result.get("rec_texts", []) or []
    if isinstance(result, list):
        if not result:
            return []
        first = result[0]
        if isinstance(first, dict):
            return first.get("rec_texts", []) or []
        # 2.x 列表格式: [[box, (text, score)], ...]
        texts = []
        for line in first or []:
            if isinstance(line, (list, tuple)) and len(line) >= 2:
                payload = line[1]
                if isinstance(payload, (list, tuple)) and payload:
                    texts.append(payload[0])
        return texts
    return []


_ocr_manager = PaddleOCRManager()


def get_ocr_manager() -> PaddleOCRManager:
    return _ocr_manager


def extract_text(image_source, lang: str = "ch") -> List[str]:
    return _ocr_manager.extract_text(image_source, lang)
