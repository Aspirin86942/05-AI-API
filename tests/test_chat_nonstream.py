import httpx
import respx
from fastapi.testclient import TestClient

from fscut_openai_proxy.app import create_app


@respx.mock
def test_chat_completions_nonstream_returns_openai_shape() -> None:
    respx.post("https://chat.fscut.com/api/agents/chat/%E5%86%85%E9%83%A8%E6%A8%A1%E5%9E%8B-vllm-GLM4.7-flash").mock(
        return_value=httpx.Response(
            200,
            text='data: {"delta":"你"}\n\ndata: {"delta":"好"}\n\ndata: {"done":true}\n\n',
            headers={"content-type": "text/event-stream"},
        )
    )

    client = TestClient(create_app())
    response = client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer local-test-key"},
        json={
            "model": "glm-4.7-flash",
            "stream": False,
            "messages": [{"role": "user", "content": "你好"}],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["object"] == "chat.completion"
    assert body["model"] == "glm-4.7-flash"
    assert body["choices"][0]["message"]["content"] == "你好"
    assert body["choices"][0]["finish_reason"] == "stop"


@respx.mock
def test_chat_request_sends_upstream_auth_cookies_and_rate_limit_headers() -> None:
    route = respx.post("https://chat.fscut.com/api/agents/chat/%E5%86%85%E9%83%A8%E6%A8%A1%E5%9E%8B-vllm-GLM4.7-flash").mock(
        return_value=httpx.Response(
            200,
            text='data: {"delta":"好"}\n\ndata: {"done":true}\n\n',
            headers={
                "content-type": "text/event-stream",
                "x-ratelimit-limit": "40",
                "x-ratelimit-remaining": "39",
                "x-ratelimit-reset": "1778579176",
            },
        )
    )

    client = TestClient(create_app())
    response = client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer local-test-key"},
        json={
            "model": "glm-4.7-flash",
            "messages": [{"role": "user", "content": "你好"}],
        },
    )

    assert response.status_code == 200
    request = route.calls.last.request
    assert request.headers["authorization"].startswith("Bearer ")
    assert request.headers["origin"] == "https://chat.fscut.com"
    assert request.headers["referer"] == "https://chat.fscut.com/c/new"
    assert request.headers["accept"] == "*/*"
    assert "connect.sid=test-session" in request.headers["cookie"]
    assert "token_provider=openid" in request.headers["cookie"]
    assert "refreshToken=test-refresh" in request.headers["cookie"]
    assert response.headers["x-ratelimit-limit"] == "40"
    assert response.headers["x-ratelimit-remaining"] == "39"
    assert response.headers["x-ratelimit-reset"] == "1778579176"


@respx.mock
def test_chat_returns_upstream_forbidden_error_without_internal_500() -> None:
    respx.post("https://chat.fscut.com/api/agents/chat/%E5%86%85%E9%83%A8%E6%A8%A1%E5%9E%8B-vllm-GLM4.7-flash").mock(
        return_value=httpx.Response(
            403,
            json={"message": "Your account has been temporarily banned due to violations of our service."},
        )
    )

    client = TestClient(create_app(), raise_server_exceptions=False)
    response = client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer local-test-key"},
        json={
            "model": "glm-4.7-flash",
            "messages": [{"role": "user", "content": "你好"}],
        },
    )

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "upstream_forbidden"
    assert response.json()["error"]["retryable"] is False

