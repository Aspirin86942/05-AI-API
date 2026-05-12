from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI(title="fscut-openai-proxy")

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {
            "status": "ok",
            "service": "fscut-openai-proxy",
            "upstream": "https://chat.fscut.com",
            "model_alias": "glm-4.7-flash",
        }

    return app

