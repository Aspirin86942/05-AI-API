import uvicorn

from fscut_openai_proxy.app import create_app
from fscut_openai_proxy.config import get_settings


def build_uvicorn_kwargs() -> dict[str, object]:
    settings = get_settings()
    return {"host": settings.server.host, "port": settings.server.port}


def main() -> None:
    uvicorn.run(create_app(), **build_uvicorn_kwargs())


if __name__ == "__main__":
    main()

