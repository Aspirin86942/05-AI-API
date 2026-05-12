import json
import time
import uuid
from collections.abc import Iterable

from fscut_openai_proxy.config import Settings
from fscut_openai_proxy.schemas import ChatCompletionRequest, OpenAIError


def build_upstream_payload(request: ChatCompletionRequest) -> dict[str, object]:
    if request.model != "glm-4.7-flash":
        raise OpenAIError(status_code=400, code="unsupported_model", message="Only glm-4.7-flash is supported")
    return {
        "messages": [message.model_dump() for message in request.messages],
        # 上游已确认返回 SSE；非流式响应由本地聚合，避免依赖未知的非流式上游契约。
        "stream": True,
        "temperature": request.temperature,
        "top_p": request.top_p,
        "max_tokens": request.max_tokens,
        "stop": request.stop,
        "user": request.user,
    }


def collect_text_from_sse_lines(lines: Iterable[str]) -> tuple[str, str]:
    parts: list[str] = []
    finish_reason = "stop"
    for line in lines:
        if not line.startswith("data: "):
            continue
        payload = line[6:]
        if payload == "[DONE]":
            break
        data = json.loads(payload)
        delta = data.get("delta")
        if isinstance(delta, str):
            parts.append(delta)
        if data.get("done") is True:
            break
    return "".join(parts), finish_reason


def build_nonstream_response(content: str, settings: Settings) -> dict[str, object]:
    created = int(time.time())
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex}",
        "object": "chat.completion",
        "created": created,
        "model": settings.upstream.model_alias,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
    }

