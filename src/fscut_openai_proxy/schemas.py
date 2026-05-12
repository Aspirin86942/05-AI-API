from typing import Any

from pydantic import BaseModel


class ErrorBody(BaseModel):
    message: str
    type: str
    code: str
    retryable: bool


class ErrorEnvelope(BaseModel):
    error: ErrorBody


class ChatMessage(BaseModel):
    role: str
    content: str | list[dict[str, Any]]


class ChatCompletionRequest(BaseModel):
    model: str
    messages: list[ChatMessage]
    stream: bool = False
    temperature: float | None = None
    top_p: float | None = None
    max_tokens: int | None = None
    stop: str | list[str] | None = None
    user: str | None = None
    tools: object | None = None
    tool_choice: object | None = None
    functions: object | None = None
    function_call: object | None = None
    response_format: object | None = None
    modalities: object | None = None
    audio: object | None = None
    n: int = 1


class OpenAIError(Exception):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        error_type: str = "invalid_request_error",
    ) -> None:
        self.status_code = status_code
        self.detail = {
            "error": {
                "message": message,
                "type": error_type,
                "code": code,
                "retryable": False,
            }
        }
