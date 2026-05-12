import time
from pathlib import Path

import httpx
import respx
from fastapi.testclient import TestClient

from fscut_openai_proxy.app import create_app
from fscut_openai_proxy.auth import RefreshClient, token_expires_soon
from fscut_openai_proxy.token_store import FileBackedTokenStore, TokenState


def test_token_expires_soon_when_exp_is_within_margin() -> None:
    exp = int(time.time()) + 30

    assert token_expires_soon(exp=exp, refresh_margin_seconds=60) is True


def test_token_expires_soon_when_exp_is_far_enough() -> None:
    exp = int(time.time()) + 600

    assert token_expires_soon(exp=exp, refresh_margin_seconds=60) is False


@respx.mock
def test_refresh_client_updates_tokens(tmp_path: Path) -> None:
    route = respx.post("https://chat.fscut.com/api/auth/refresh").mock(
        return_value=httpx.Response(
            200,
            json={
                "accessToken": "new-access",
                "refreshToken": "new-refresh",
            },
            headers={"set-cookie": "connect.sid=new-session; Path=/; HttpOnly"},
        )
    )
    store = FileBackedTokenStore(
        path=tmp_path / "token-state.json",
        initial_state=TokenState(
            access_token="old-access",
            refresh_token="old-refresh",
            connect_sid="old-session",
            token_provider="openid",
        ),
    )

    client = RefreshClient(base_url="https://chat.fscut.com", token_store=store)
    client.refresh()

    assert route.called is True
    assert store.load().access_token == "new-access"
    assert store.load().refresh_token == "new-refresh"
    assert store.load().connect_sid == "new-session"


@respx.mock
def test_chat_retries_once_after_refresh() -> None:
    chat_url = "https://chat.fscut.com/api/agents/chat/%E5%86%85%E9%83%A8%E6%A8%A1%E5%9E%8B-vllm-GLM4.7-flash"
    refresh_url = "https://chat.fscut.com/api/auth/refresh"

    chat_route = respx.post(chat_url).mock(
        side_effect=[
            httpx.Response(401, json={"message": "expired"}),
            httpx.Response(
                200,
                text='data: {"delta":"好"}\n\ndata: {"done":true}\n\n',
                headers={"content-type": "text/event-stream"},
            ),
        ]
    )
    refresh_route = respx.post(refresh_url).mock(
        return_value=httpx.Response(200, json={"accessToken": "new-access", "refreshToken": "new-refresh"})
    )

    client = TestClient(create_app())
    response = client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer local-test-key"},
        json={
            "model": "glm-4.7-flash",
            "messages": [{"role": "user", "content": "hi"}],
        },
    )

    assert response.status_code == 200
    assert response.json()["choices"][0]["message"]["content"] == "好"
    assert chat_route.call_count == 2
    assert refresh_route.called is True
