import base64
import json
import re
import time
from typing import Any

import httpx

from fscut_openai_proxy.errors import UpstreamAuthExpiredError
from fscut_openai_proxy.token_store import FileBackedTokenStore, TokenState


def decode_jwt_payload(token: str) -> dict[str, Any]:
    parts = token.split(".")
    if len(parts) != 3:
        return {}
    payload = parts[1]
    padding = "=" * (-len(payload) % 4)
    try:
        decoded = base64.urlsafe_b64decode(payload + padding).decode("utf-8")
        return json.loads(decoded)
    except Exception:
        return {}


def token_expires_soon(exp: int | None, refresh_margin_seconds: int) -> bool:
    if exp is None:
        return True
    return exp <= int(time.time()) + refresh_margin_seconds


class AuthManager:
    def __init__(self, token_store: FileBackedTokenStore, refresh_margin_seconds: int = 60) -> None:
        self.token_store = token_store
        self._refresh_margin_seconds = refresh_margin_seconds

    def current_access_token(self) -> str:
        state = self.token_store.load()
        payload = decode_jwt_payload(state.access_token)
        exp = payload.get("exp")
        if token_expires_soon(exp=exp, refresh_margin_seconds=self._refresh_margin_seconds):
            raise RuntimeError("refresh required before request")
        return state.access_token

    def replace_tokens(
        self,
        *,
        access_token: str,
        refresh_token: str,
        connect_sid: str,
        token_provider: str,
    ) -> None:
        self.token_store.save(
            TokenState(
                access_token=access_token,
                refresh_token=refresh_token,
                connect_sid=connect_sid,
                token_provider=token_provider,
            )
        )


class RefreshClient:
    def __init__(self, base_url: str, token_store: FileBackedTokenStore) -> None:
        self._base_url = base_url.rstrip("/")
        self._token_store = token_store

    def refresh(self) -> None:
        state = self._token_store.load()
        response = httpx.post(
            f"{self._base_url}/api/auth/refresh",
            json={"refreshToken": state.refresh_token},
            headers={"Authorization": f"Bearer {state.access_token}"},
            cookies={
                "connect.sid": state.connect_sid,
                "token_provider": state.token_provider,
                "refreshToken": state.refresh_token,
            },
            timeout=15.0,
        )
        if response.status_code >= 400:
            raise UpstreamAuthExpiredError()
        data = response.json()
        set_cookie = response.headers.get("set-cookie", "")
        match = re.search(r"connect\.sid=([^;]+)", set_cookie)
        connect_sid = match.group(1) if match else state.connect_sid
        self._token_store.save(
            TokenState(
                access_token=data["accessToken"],
                refresh_token=data.get("refreshToken", state.refresh_token),
                connect_sid=connect_sid,
                token_provider=state.token_provider,
            )
        )

