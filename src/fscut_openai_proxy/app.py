from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from fscut_openai_proxy.api import router
from fscut_openai_proxy.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="fscut-openai-proxy")

    @app.exception_handler(HTTPException)
    async def handle_http_exception(_: Request, exc: HTTPException) -> JSONResponse:
        if isinstance(exc.detail, dict):
            return JSONResponse(status_code=exc.status_code, content=exc.detail)
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "message": str(exc.detail),
                    "type": "request_error",
                    "code": "http_error",
                    "retryable": False,
                }
            },
        )

    @app.exception_handler(Exception)
    async def handle_exception(_: Request, exc: Exception) -> JSONResponse:
        if hasattr(exc, "detail") and isinstance(exc.detail, dict):
            return JSONResponse(status_code=getattr(exc, "status_code", 500), content=exc.detail)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "message": "Internal server error",
                    "type": "server_error",
                    "code": "internal_error",
                    "retryable": False,
                }
            },
        )

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {
            "status": "ok",
            "service": "fscut-openai-proxy",
            "upstream": settings.upstream.base_url,
            "model_alias": settings.upstream.model_alias,
        }

    app.include_router(router)
    return app
