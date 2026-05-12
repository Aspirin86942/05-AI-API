import base64
import json
import time
from pathlib import Path

import pytest

from fscut_openai_proxy.config import get_settings


def _unsigned_jwt_with_exp(exp: int) -> str:
    header = base64.urlsafe_b64encode(json.dumps({"alg": "none"}).encode("utf-8")).decode("ascii").rstrip("=")
    payload = base64.urlsafe_b64encode(json.dumps({"exp": exp}).encode("utf-8")).decode("ascii").rstrip("=")
    return f"{header}.{payload}."


@pytest.fixture(autouse=True)
def fscut_proxy_test_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    token_state_path = tmp_path / "token-state.json"
    access_token = _unsigned_jwt_with_exp(int(time.time()) + 3600)
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        f"""
[server]
local_api_key = "local-test-key"

[auth]
access_token = "{access_token}"
refresh_token = "test-refresh"
connect_sid = "test-session"
token_provider = "openid"
state_path = "{token_state_path.as_posix()}"
""".strip(),
        encoding="utf-8",
    )
    monkeypatch.setenv("FSCUT_PROXY_CONFIG", str(config_path))
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()

