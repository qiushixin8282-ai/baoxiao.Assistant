"""OpenAI 兼容的轻量 LLM 客户端（懒加载）。

用于发票字段抽取、智能问答与审核。未配置 API Key 时抛出 LLMUnavailableError，
调用方可据此降级为规则引擎的确定性能力。
"""

import logging
from typing import Dict, Iterator, List, Optional

from app.config import settings

logger = logging.getLogger(__name__)


class LLMUnavailableError(RuntimeError):
    pass


class LLMClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ) -> None:
        self.api_key = api_key or settings.openai_api_key
        self.base_url = base_url or settings.openai_base_url
        self.model = model or settings.openai_model

    def _client(self):
        if not self.api_key:
            raise LLMUnavailableError(
                "未配置 OPENAI_API_KEY。请在 .env 中填写或设置环境变量。"
            )
        try:
            import openai

            return openai.OpenAI(api_key=self.api_key, base_url=self.base_url)
        except Exception as exc:  # pragma: no cover
            raise LLMUnavailableError(f"初始化 OpenAI 客户端失败: {exc}") from exc

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 4000,
    ) -> str:
        client = self._client()
        resp = client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            extra_body={"enable_thinking": False},
        )
        return resp.choices[0].message.content or ""

    def stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 4000,
    ) -> Iterator[str]:
        client = self._client()
        stream = client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
            extra_body={"enable_thinking": False},
        )
        for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if delta and delta.content:
                yield delta.content


_client = LLMClient()


def get_llm_client() -> LLMClient:
    return _client
