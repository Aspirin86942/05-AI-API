from pathlib import Path

from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.responses import JSONResponse, StreamingResponse

from fscut_openai_proxy.auth import AuthManager
from fscut_openai_proxy.config import Settings, get_settings
from fscut_openai_proxy.schemas import ChatCompletionRequest, OpenAIError
from fscut_openai_proxy.token_store import FileBackedTokenStore, TokenState
from fscut_openai_proxy.translator import (
    build_nonstream_response,
    build_upstream_payload,
    collect_text_from_sse_lines,
    to_openai_sse_chunks,
)
from fscut_openai_proxy.upstream import UpstreamClient


def require_local_api_key(
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> None:
    expected = f"Bearer {settings.server.local_api_key}"
    if authorization != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "message": "Invalid local API key",
                    "type": "authentication_error",
                    "code": "local_api_key_invalid",
                    "retryable": False,
                }
            },
        )


def get_auth_manager(settings: Settings = Depends(get_settings)) -> AuthManager:
    store = FileBackedTokenStore(
        path=Path(settings.auth.state_path),
        initial_state=TokenState(
            access_token=settings.auth.access_token,
            refresh_token=settings.auth.refresh_token,
            connect_sid=settings.auth.connect_sid,
            token_provider=settings.auth.token_provider,
        ),
    )
    return AuthManager(token_store=store, refresh_margin_seconds=settings.auth.refresh_margin_seconds)


router = APIRouter()
RATE_LIMIT_HEADERS = ("x-ratelimit-limit", "x-ratelimit-remaining", "x-ratelimit-reset")


@router.get("/v1/models", dependencies=[Depends(require_local_api_key)])
def list_models(settings: Settings = Depends(get_settings)) -> dict[str, object]:
    return {
        "object": "list",
        "data": [
            {
                "id": settings.upstream.model_alias,
                "object": "model",
                "owned_by": "fscut-proxy",
            }
        ],
    }


@router.post("/v1/chat/completions", dependencies=[Depends(require_local_api_key)])
def chat_completions(
    request: ChatCompletionRequest,
    settings: Settings = Depends(get_settings),
    auth_manager: AuthManager = Depends(get_auth_manager),
):
    try:
        payload = build_upstream_payload(request)
    except OpenAIError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    client = UpstreamClient(settings=settings, auth_manager=auth_manager)
    response = client.post_chat(payload)
    response.raise_for_status()
    lines = response.text.splitlines()
    rate_limit_headers = {
        header_name: response.headers[header_name]
        for header_name in RATE_LIMIT_HEADERS
        if header_name in response.headers
    }
    if request.stream:
        return StreamingResponse(
            to_openai_sse_chunks(lines=lines, model_alias=settings.upstream.model_alias),
            media_type="text/event-stream",
            headers=rate_limit_headers,
        )
    content, _ = collect_text_from_sse_lines(lines)
    return JSONResponse(
        content=build_nonstream_response(content=content, settings=settings),
        headers=rate_limit_headers,
    )
