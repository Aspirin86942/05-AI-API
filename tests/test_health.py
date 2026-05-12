from fastapi.testclient import TestClient

from fscut_openai_proxy.app import create_app
from fscut_openai_proxy.__main__ import build_uvicorn_kwargs


def test_healthz_returns_service_metadata() -> None:
    app = create_app()
    client = TestClient(app)

    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "fscut-openai-proxy",
        "upstream": "https://chat.fscut.com",
        "model_alias": "glm-4.7-flash",
    }


def test_healthz_includes_request_id_header() -> None:
    client = TestClient(create_app())

    response = client.get("/healthz")

    assert response.status_code == 200
    assert "x-request-id" in response.headers
    assert response.headers["x-request-id"]


def test_uvicorn_kwargs_use_configured_host_and_port(fscut_proxy_test_config) -> None:
    kwargs = build_uvicorn_kwargs()

    assert kwargs["host"] == "127.0.0.1"
    assert kwargs["port"] == 8787
