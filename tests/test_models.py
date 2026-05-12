from fastapi.testclient import TestClient

from fscut_openai_proxy.app import create_app


def test_models_requires_local_api_key() -> None:
    client = TestClient(create_app())

    response = client.get("/v1/models")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "local_api_key_invalid"


def test_models_returns_single_glm_model() -> None:
    client = TestClient(create_app())

    response = client.get(
        "/v1/models",
        headers={"Authorization": "Bearer local-test-key"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "object": "list",
        "data": [
            {
                "id": "glm-4.7-flash",
                "object": "model",
                "owned_by": "fscut-proxy",
            }
        ],
    }

