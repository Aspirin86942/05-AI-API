import time
from pathlib import Path

import httpx
import respx

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

