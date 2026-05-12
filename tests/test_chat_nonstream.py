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

