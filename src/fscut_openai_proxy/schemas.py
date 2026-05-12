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
    content: str


class ChatCompletionRequest(BaseModel):
    model: str
    messages: list[ChatMessage]
    stream: bool = False
