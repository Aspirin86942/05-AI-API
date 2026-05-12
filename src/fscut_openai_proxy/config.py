import os
import tomllib
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field


class ServerSettings(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8787
    local_api_key: str = "local-test-key"


class UpstreamSettings(BaseModel):
    base_url: str = "https://chat.fscut.com"
    agent_endpoint: str = "内部模型-vllm-GLM4.7-flash"
    model_alias: str = "glm-4.7-flash"


class AuthSettings(BaseModel):
    access_token: str = ""
    refresh_token: str = ""
    connect_sid: str = ""
    token_provider: str = "openid"
    refresh_margin_seconds: int = 60
    state_path: str = ""


class Settings(BaseModel):
    server: ServerSettings = Field(default_factory=ServerSettings)
    upstream: UpstreamSettings = Field(default_factory=UpstreamSettings)
    auth: AuthSettings = Field(default_factory=AuthSettings)


def resolve_config_path() -> Path:
    env_path = os.getenv("FSCUT_PROXY_CONFIG")
    if env_path:
        return Path(env_path)
    return Path("config.toml")


def default_state_path(config_path: Path) -> Path:
    return config_path.with_name("token-state.json")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    path = resolve_config_path()
    if not path.exists():
        settings = Settings()
        settings.auth.state_path = str(default_state_path(path))
        return settings
    with path.open("rb") as fh:
        payload = tomllib.load(fh)
    settings = Settings.model_validate(payload)
    if not settings.auth.state_path:
        settings.auth.state_path = str(default_state_path(path))
    return settings
