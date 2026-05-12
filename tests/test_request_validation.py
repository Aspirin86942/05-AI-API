from fastapi.testclient import TestClient

from fscut_openai_proxy.app import create_app


def test_chat_completions_rejects_unknown_model() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer local-test-key"},
        json={
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": "hi"}],
        },
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "unsupported_model"

