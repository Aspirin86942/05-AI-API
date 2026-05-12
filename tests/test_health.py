from fastapi.testclient import TestClient

from fscut_openai_proxy.app import create_app


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

