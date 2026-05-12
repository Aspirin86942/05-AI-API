import httpx
import respx
from fastapi.testclient import TestClient

from fscut_openai_proxy.app import create_app


@respx.mock
def test_chat_completions_stream_returns_openai_sse() -> None:
    respx.post("https://chat.fscut.com/api/agents/chat/%E5%86%85%E9%83%A8%E6%A8%A1%E5%9E%8B-vllm-GLM4.7-flash").mock(
        return_value=httpx.Response(
            200,
            text='data: {"delta":"你"}\n\ndata: {"delta":"好"}\n\ndata: {"done":true}\n\n',
            headers={"content-type": "text/event-stream"},
        )
    )
    client = TestClient(create_app())

    with client.stream(
        "POST",
        "/v1/chat/completions",
        headers={"Authorization": "Bearer local-test-key"},
        json={
            "model": "glm-4.7-flash",
            "stream": True,
            "messages": [{"role": "user", "content": "你好"}],
        },
    ) as response:
        body = "".join(chunk.decode("utf-8") if isinstance(chunk, bytes) else chunk for chunk in response.iter_raw())

    assert response.status_code == 200
    assert "chat.completion.chunk" in body
    assert '"content":"你"' in body
    assert '"content":"好"' in body
    assert "data: [DONE]" in body

