from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from fscut_openai_proxy.api import router
from fscut_openai_proxy.config import get_settings
from fscut_openai_proxy.logging_config import configure_logging, inject_request_id


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging()
    app = FastAPI(title="fscut-openai-proxy")
    app.middleware("http")(inject_request_id)

    @app.exception_handler(HTTPException)
    async def handle_http_exception(request: Request, exc: HTTPException) -> JSONResponse:
        if isinstance(exc.detail, dict):
            response = JSONResponse(status_code=exc.status_code, content=exc.detail)
        else:
            response = JSONResponse(
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
        response.headers["x-request-id"] = getattr(request.state, "request_id", "")
        return response

    @app.exception_handler(Exception)
    async def handle_exception(request: Request, exc: Exception) -> JSONResponse:
        if hasattr(exc, "detail") and isinstance(exc.detail, dict):
            response = JSONResponse(status_code=getattr(exc, "status_code", 500), content=exc.detail)
        else:
            response = JSONResponse(
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
        response.headers["x-request-id"] = getattr(request.state, "request_id", "")
        return response

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
