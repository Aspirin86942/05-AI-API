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


def test_chat_completions_rejects_tools() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer local-test-key"},
        json={
            "model": "glm-4.7-flash",
            "messages": [{"role": "user", "content": "hi"}],
            "tools": [{"type": "function", "function": {"name": "lookup"}}],
        },
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "unsupported_field"


def test_chat_completions_rejects_multiple_choices() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer local-test-key"},
        json={
            "model": "glm-4.7-flash",
            "messages": [{"role": "user", "content": "hi"}],
            "n": 2,
        },
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "unsupported_field"


def test_chat_completions_accepts_text_content_parts() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer local-test-key"},
        json={
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": [{"type": "text", "text": "hi"}]}],
        },
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "unsupported_model"


def test_chat_completions_rejects_non_text_content_parts() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer local-test-key"},
        json={
            "model": "glm-4.7-flash",
            "messages": [
                {
                    "role": "user",
                    "content": [{"type": "image_url", "image_url": {"url": "https://example.com/a.png"}}],
                }
            ],
        },
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "unsupported_content"
