"""智能问答接口（支持流式）。"""

import json
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.core.llm_client import LLMUnavailableError, get_llm_client
from app.core.rules_engine import get_rules_engine

router = APIRouter(prefix="/chat", tags=["chat"])

SYSTEM_PROMPT = """你是"小荷包报销助手"，一名专业、严谨的财务报销顾问。
请依据下方报销规则回答用户问题，给出明确依据与结论；规则未覆盖时明确说明，不要编造。"""


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: Optional[List[ChatMessage]] = None


def _build_messages(req: ChatRequest) -> List[dict]:
    rules_text = get_rules_engine().get_rules_for_ai_prompt()
    system = f"{SYSTEM_PROMPT}\n\n{rules_text}"
    messages = [{"role": "system", "content": system}]
    for m in req.history or []:
        messages.append({"role": m.role, "content": m.content})
    messages.append({"role": "user", "content": req.message})
    return messages


@router.post("")
def chat(req: ChatRequest) -> dict:
    """非流式问答。"""
    try:
        answer = get_llm_client().chat(_build_messages(req))
    except LLMUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"reply": answer}


@router.post("/stream")
def chat_stream(req: ChatRequest) -> StreamingResponse:
    """流式问答，返回 text/event-stream。"""
    messages = _build_messages(req)

    def event_gen():
        try:
            for token in get_llm_client().stream(messages):
                yield f"data: {json.dumps({'delta': token}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
        except LLMUnavailableError as exc:
            yield f"data: {json.dumps({'error': str(exc)}, ensure_ascii=False)}\n\n"
        except Exception as exc:  # pragma: no cover
            yield f"data: {json.dumps({'error': f'生成失败: {exc}'}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_gen(), media_type="text/event-stream")
