from fastapi import APIRouter, Depends, Header, HTTPException, status

from fscut_openai_proxy.config import Settings, get_settings
from fscut_openai_proxy.schemas import ChatCompletionRequest


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


router = APIRouter()


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
) -> dict[str, object]:
    if request.model != settings.upstream.model_alias:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "message": f"Unsupported model: {request.model}",
                    "type": "invalid_request_error",
                    "code": "unsupported_model",
                    "retryable": False,
                }
            },
        )
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
            "error": {
                "message": "Chat completions adapter is not implemented yet",
                "type": "server_error",
                "code": "not_implemented",
                "retryable": False,
            }
        },
    )
