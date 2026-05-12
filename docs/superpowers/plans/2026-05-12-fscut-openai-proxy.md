# FSCUT OpenAI Proxy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a localhost-only OpenAI-compatible proxy for `chat.fscut.com` that supports one text model (`glm-4.7-flash`), automatic upstream token refresh, and both streaming and non-streaming chat completions.

**Architecture:** A FastAPI service exposes `GET /healthz`, `GET /v1/models`, and `POST /v1/chat/completions`. A dedicated auth layer owns upstream access token refresh and secret persistence. A translator layer isolates OpenAI request/response mapping from the FSCUT upstream chat/SSE protocol.

**Tech Stack:** Python 3.10+, FastAPI, Uvicorn, httpx, Pydantic v2, pytest, respx, anyio

---

> 当前工作目录不是 git 仓库。下面每个 Task 都保留了 commit 步骤，但执行前应先初始化 git；如果仍未初始化，则把 commit 步骤视为待办，不要伪造提交结果。

## Planned File Structure

- Create: `pyproject.toml`
- Create: `README.md`
- Create: `.gitignore`
- Create: `src/fscut_openai_proxy/__init__.py`
- Create: `src/fscut_openai_proxy/__main__.py`
- Create: `src/fscut_openai_proxy/app.py`
- Create: `src/fscut_openai_proxy/api.py`
- Create: `src/fscut_openai_proxy/auth.py`
- Create: `src/fscut_openai_proxy/config.py`
- Create: `src/fscut_openai_proxy/errors.py`
- Create: `src/fscut_openai_proxy/logging_config.py`
- Create: `src/fscut_openai_proxy/schemas.py`
- Create: `src/fscut_openai_proxy/token_store.py`
- Create: `src/fscut_openai_proxy/translator.py`
- Create: `src/fscut_openai_proxy/upstream.py`
- Create: `tests/conftest.py`
- Create: `tests/fixtures/upstream/README.md`
- Create: `tests/fixtures/upstream/chat_request_real.json`
- Create: `tests/fixtures/upstream/chat_stream_real.txt`
- Create: `tests/fixtures/upstream/refresh_request_real.md`
- Create: `tests/fixtures/upstream/refresh_response_real.json`
- Create: `tests/test_health.py`
- Create: `tests/test_models.py`
- Create: `tests/test_auth_refresh.py`
- Create: `tests/test_chat_nonstream.py`
- Create: `tests/test_chat_stream.py`
- Create: `tests/test_request_validation.py`

### Task 1: 固化上游真实契约

**Files:**
- Create: `tests/fixtures/upstream/README.md`
- Create: `tests/fixtures/upstream/chat_request_real.json`
- Create: `tests/fixtures/upstream/chat_stream_real.txt`
- Create: `tests/fixtures/upstream/refresh_request_real.md`
- Create: `tests/fixtures/upstream/refresh_response_real.json`

- [ ] **Step 1: 写明 fixture 采集规则**

```md
# Upstream Fixtures

这些文件必须来自 2026-05-12 之后的真实抓包，不允许手工编造。

采集要求：

1. `chat_request_real.json`
   - 保存 `POST /api/agents/chat/内部模型-vllm-GLM4.7-flash` 的真实 JSON body
   - 去掉敏感 token，但保留字段结构与空值
2. `chat_stream_real.txt`
   - 保存一次完整 SSE 响应原文
   - 至少覆盖首个事件、若干增量事件、结束事件
3. `refresh_request_real.md`
   - 保存 refresh 请求的方法、路径、必要 header、必要 cookie、必要 body
   - token 值必须打码
4. `refresh_response_real.json`
   - 保存 refresh 成功响应 JSON
   - token 值必须打码
```

- [ ] **Step 2: 手工导出聊天请求体**

Run:

```powershell
@'
1. 打开 Chrome DevTools -> Network
2. 新开会话，发送最短测试文本，例如 "1"
3. 找到 POST /api/agents/chat/内部模型-vllm-GLM4.7-flash
4. 复制 Request Payload
5. 保存到 tests/fixtures/upstream/chat_request_real.json
'@ | Set-Content tests/fixtures/upstream/README.md -Encoding utf8
```

Expected: `tests/fixtures/upstream/README.md` 出现明确采集步骤。

- [ ] **Step 3: 手工导出一条完整 SSE 响应**

Run:

```powershell
@'
在 DevTools 中打开刚才那条聊天请求：

- 复制 Response 原文
- 保存到 tests/fixtures/upstream/chat_stream_real.txt
- 保留原始 event/data 分隔，不要重新格式化
'@ | Add-Content tests/fixtures/upstream/README.md -Encoding utf8
```

Expected: `chat_stream_real.txt` 为原始 SSE 文本。

- [ ] **Step 4: 手工导出 refresh 契约**

Run:

```powershell
@'
触发一次 access token 刷新或重新登录后：

- 保存 refresh 请求说明到 tests/fixtures/upstream/refresh_request_real.md
- 保存 refresh 响应 JSON 到 tests/fixtures/upstream/refresh_response_real.json
- 所有 token 只保留前 8 位和后 6 位，中间打码
'@ | Add-Content tests/fixtures/upstream/README.md -Encoding utf8
```

Expected: refresh 请求和响应 fixture 就位。

- [ ] **Step 5: Commit**

```bash
git add tests/fixtures/upstream
git commit -m "docs: capture real upstream contract fixtures"
```

### Task 2: 脚手架与健康检查

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `src/fscut_openai_proxy/__init__.py`
- Create: `src/fscut_openai_proxy/__main__.py`
- Create: `src/fscut_openai_proxy/app.py`
- Create: `tests/test_health.py`

- [ ] **Step 1: 写失败测试，先锁定 `GET /healthz`**

```python
from fastapi.testclient import TestClient

from fscut_openai_proxy.app import create_app


def test_healthz_returns_service_metadata() -> None:
    app = create_app()
    client = TestClient(app)

    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "fscut-openai-proxy",
        "upstream": "https://chat.fscut.com",
        "model_alias": "glm-4.7-flash",
    }
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```bash
conda run -n test pytest tests/test_health.py -v
```

Expected: FAIL，提示 `ModuleNotFoundError` 或 `create_app` 不存在。

- [ ] **Step 3: 写最小实现**

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "fscut-openai-proxy"
version = "0.1.0"
description = "Local OpenAI-compatible proxy for FSCUT internal chat"
requires-python = ">=3.10"
dependencies = [
  "fastapi>=0.115,<1.0",
  "uvicorn>=0.30,<1.0",
  "httpx>=0.27,<1.0",
  "pydantic>=2.8,<3.0",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.0,<9.0",
  "pytest-asyncio>=0.23,<1.0",
  "respx>=0.21,<1.0",
]

[tool.pytest.ini_options]
pythonpath = ["src"]
```

```python
# src/fscut_openai_proxy/__init__.py
__all__ = ["__version__"]

__version__ = "0.1.0"
```

```python
# src/fscut_openai_proxy/app.py
from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI(title="fscut-openai-proxy")

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {
            "status": "ok",
            "service": "fscut-openai-proxy",
            "upstream": "https://chat.fscut.com",
            "model_alias": "glm-4.7-flash",
        }

    return app
```

```python
# src/fscut_openai_proxy/__main__.py
import uvicorn

from fscut_openai_proxy.app import create_app


def main() -> None:
    uvicorn.run(create_app(), host="127.0.0.1", port=8787)


if __name__ == "__main__":
    main()
```

```gitignore
__pycache__/
.pytest_cache/
.venv/
dist/
build/
*.pyc
*.pyo
*.pyd
*.log
tests/fixtures/upstream/*real*.json
tests/fixtures/upstream/*real*.txt
tests/fixtures/upstream/*real*.md
```

- [ ] **Step 4: 运行测试确认通过**

Run:

```bash
conda run -n test pytest tests/test_health.py -v
```

Expected: PASS。

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml .gitignore src/fscut_openai_proxy/__init__.py src/fscut_openai_proxy/__main__.py src/fscut_openai_proxy/app.py tests/test_health.py
git commit -m "feat: scaffold proxy service and health endpoint"
```

### Task 3: 配置加载、本地鉴权、模型列表

**Files:**
- Create: `src/fscut_openai_proxy/config.py`
- Create: `src/fscut_openai_proxy/schemas.py`
- Create: `src/fscut_openai_proxy/api.py`
- Create: `tests/conftest.py`
- Create: `tests/test_models.py`
- Create: `tests/test_request_validation.py`
- Modify: `src/fscut_openai_proxy/app.py`

- [ ] **Step 1: 写失败测试，锁定 `GET /v1/models` 与本地 API Key**

```python
from fastapi.testclient import TestClient

from fscut_openai_proxy.app import create_app


def test_models_requires_local_api_key() -> None:
    client = TestClient(create_app())

    response = client.get("/v1/models")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "local_api_key_invalid"


def test_models_returns_single_glm_model() -> None:
    client = TestClient(create_app())

    response = client.get(
        "/v1/models",
        headers={"Authorization": "Bearer local-test-key"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "object": "list",
        "data": [
            {
                "id": "glm-4.7-flash",
                "object": "model",
                "owned_by": "fscut-proxy",
            }
        ],
    }
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```bash
conda run -n test pytest tests/test_models.py -v
```

Expected: FAIL，提示 `/v1/models` 不存在或未鉴权。

- [ ] **Step 3: 写最小实现**

```python
# src/fscut_openai_proxy/config.py
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
    appdata = os.getenv("APPDATA")
    if appdata:
        return Path(appdata) / "fscut-openai-proxy" / "config.toml"
    return Path("config.toml")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    path = resolve_config_path()
    if not path.exists():
        return Settings()
    with path.open("rb") as fh:
        payload = tomllib.load(fh)
    settings = Settings.model_validate(payload)
    if not settings.auth.state_path:
        settings.auth.state_path = str(path.with_name("token-state.json"))
    return settings
```

```python
# src/fscut_openai_proxy/schemas.py
from pydantic import BaseModel


class ErrorBody(BaseModel):
    message: str
    type: str
    code: str
    retryable: bool


class ErrorEnvelope(BaseModel):
    error: ErrorBody
```

```python
# src/fscut_openai_proxy/api.py
from fastapi import APIRouter, Depends, Header, HTTPException, status

from fscut_openai_proxy.config import Settings, get_settings


def require_local_api_key(
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> None:
    expected = f"Bearer {settings.server.local_api_key}"
    if authorization != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "message": "Invalid local API key",
                    "type": "authentication_error",
                    "code": "local_api_key_invalid",
                    "retryable": False,
                }
            },
        )


router = APIRouter()


@router.get("/v1/models", dependencies=[Depends(require_local_api_key)])
def list_models(settings: Settings = Depends(get_settings)) -> dict[str, object]:
    return {
        "object": "list",
        "data": [
            {
                "id": settings.upstream.model_alias,
                "object": "model",
                "owned_by": "fscut-proxy",
            }
        ],
    }
```

```python
# src/fscut_openai_proxy/app.py
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from fscut_openai_proxy.api import router
from fscut_openai_proxy.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="fscut-openai-proxy")

    @app.exception_handler(Exception)
    async def handle_exception(_: Request, exc: Exception) -> JSONResponse:
        if hasattr(exc, "detail") and isinstance(exc.detail, dict):
            return JSONResponse(status_code=getattr(exc, "status_code", 500), content=exc.detail)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "message": "Internal server error",
                    "type": "server_error",
                    "code": "internal_error",
                    "retryable": False,
                }
            },
        )

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {
            "status": "ok",
            "service": "fscut-openai-proxy",
            "upstream": settings.upstream.base_url,
            "model_alias": settings.upstream.model_alias,
        }

    app.include_router(router)
    return app
```

- [ ] **Step 4: 再加一个失败测试，锁定不支持的模型名**

```python
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
```

- [ ] **Step 5: 运行测试**

Run:

```bash
conda run -n test pytest tests/test_models.py tests/test_request_validation.py -v
```

Expected: `test_models.py` PASS，`test_request_validation.py` FAIL，说明后续聊天接口还未实现。

- [ ] **Step 6: Commit**

```bash
git add src/fscut_openai_proxy/config.py src/fscut_openai_proxy/schemas.py src/fscut_openai_proxy/api.py src/fscut_openai_proxy/app.py tests/test_models.py tests/test_request_validation.py
git commit -m "feat: add config loading and local auth guarded models endpoint"
```

### Task 4: 令牌存储与自动刷新

**Files:**
- Create: `src/fscut_openai_proxy/token_store.py`
- Create: `src/fscut_openai_proxy/auth.py`
- Create: `tests/test_auth_refresh.py`

- [ ] **Step 1: 写失败测试，锁定“过期前刷新”和“401 后重刷一次”**

```python
import time

from fscut_openai_proxy.auth import token_expires_soon


def test_token_expires_soon_when_exp_is_within_margin() -> None:
    exp = int(time.time()) + 30

    assert token_expires_soon(exp=exp, refresh_margin_seconds=60) is True


def test_token_expires_soon_when_exp_is_far_enough() -> None:
    exp = int(time.time()) + 600

    assert token_expires_soon(exp=exp, refresh_margin_seconds=60) is False
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```bash
conda run -n test pytest tests/test_auth_refresh.py -v
```

Expected: FAIL，提示 `fscut_openai_proxy.auth` 不存在。

- [ ] **Step 3: 写最小实现**

```python
# src/fscut_openai_proxy/token_store.py
import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class TokenState:
    access_token: str
    refresh_token: str
    connect_sid: str
    token_provider: str


class FileBackedTokenStore:
    def __init__(self, path: Path, initial_state: TokenState) -> None:
        self._path = path
        self._state = initial_state
        if self._path.exists():
            payload = json.loads(self._path.read_text(encoding="utf-8"))
            self._state = TokenState(**payload)
        else:
            self.save(initial_state)

    def load(self) -> TokenState:
        return self._state

    def save(self, state: TokenState) -> None:
        self._state = state
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self._path.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(asdict(state), ensure_ascii=False), encoding="utf-8")
        tmp_path.replace(self._path)
```

```python
# src/fscut_openai_proxy/auth.py
import base64
import json
import time
from typing import Any

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
```

- [ ] **Step 4: 再加一个失败测试，锁定 refresh HTTP 调用**

```python
from pathlib import Path

import httpx
import respx

from fscut_openai_proxy.auth import RefreshClient
from fscut_openai_proxy.token_store import FileBackedTokenStore, TokenState


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
```

- [ ] **Step 5: 写最小 refresh 客户端**

```python
# append to src/fscut_openai_proxy/auth.py
import re

import httpx


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
        response.raise_for_status()
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
```

> 注意：这里的 `json={"refreshToken": ...}` 只是基于当前已知信息的首版实现。若 Task 1 采集到的真实契约不同，必须先按真实契约调整这里，再继续后续任务。

- [ ] **Step 6: 运行测试确认通过**

Run:

```bash
conda run -n test pytest tests/test_auth_refresh.py -v
```

Expected: PASS。

- [ ] **Step 7: Commit**

```bash
git add src/fscut_openai_proxy/token_store.py src/fscut_openai_proxy/auth.py tests/test_auth_refresh.py
git commit -m "feat: add token store and automatic refresh primitives"
```

### Task 5: OpenAI 请求模型与非流式聊天

**Files:**
- Modify: `src/fscut_openai_proxy/schemas.py`
- Create: `src/fscut_openai_proxy/translator.py`
- Create: `src/fscut_openai_proxy/upstream.py`
- Modify: `src/fscut_openai_proxy/api.py`
- Create: `tests/test_chat_nonstream.py`

- [ ] **Step 1: 写失败测试，锁定最小非流式聊天**

```python
import httpx
import respx
from fastapi.testclient import TestClient

from fscut_openai_proxy.app import create_app


@respx.mock
def test_chat_completions_nonstream_returns_openai_shape() -> None:
    respx.post("https://chat.fscut.com/api/agents/chat/%E5%86%85%E9%83%A8%E6%A8%A1%E5%9E%8B-vllm-GLM4.7-flash").mock(
        return_value=httpx.Response(
            200,
            text='data: {"delta":"你"}\\n\\ndata: {"delta":"好"}\\n\\ndata: {"done":true}\\n\\n',
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
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```bash
conda run -n test pytest tests/test_chat_nonstream.py -v
```

Expected: FAIL，提示 `/v1/chat/completions` 未实现。

- [ ] **Step 3: 写请求/响应模型与转换器最小实现**

```python
# append to src/fscut_openai_proxy/schemas.py
from typing import Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class ChatCompletionRequest(BaseModel):
    model: str
    messages: list[ChatMessage]
    stream: bool = False
    temperature: float | None = None
    top_p: float | None = None
    max_tokens: int | None = None
    stop: str | list[str] | None = None
    user: str | None = None


class OpenAIError(Exception):
    def __init__(self, status_code: int, code: str, message: str, error_type: str = "invalid_request_error") -> None:
        self.status_code = status_code
        self.detail = {
            "error": {
                "message": message,
                "type": error_type,
                "code": code,
                "retryable": False,
            }
        }
```

```python
# src/fscut_openai_proxy/translator.py
import json
import time
import uuid
from collections.abc import Iterable

from fscut_openai_proxy.config import Settings
from fscut_openai_proxy.schemas import ChatCompletionRequest, OpenAIError


def build_upstream_payload(request: ChatCompletionRequest) -> dict[str, object]:
    if request.model != "glm-4.7-flash":
        raise OpenAIError(status_code=400, code="unsupported_model", message="Only glm-4.7-flash is supported")
    return {
        "messages": [message.model_dump() for message in request.messages],
        "stream": True,
        "temperature": request.temperature,
        "top_p": request.top_p,
        "max_tokens": request.max_tokens,
        "stop": request.stop,
        "user": request.user,
    }


def collect_text_from_sse_lines(lines: Iterable[str]) -> tuple[str, str]:
    parts: list[str] = []
    finish_reason = "stop"
    for line in lines:
        if not line.startswith("data: "):
            continue
        payload = line[6:]
        if payload == "[DONE]":
            break
        data = json.loads(payload)
        delta = data.get("delta")
        if isinstance(delta, str):
            parts.append(delta)
        if data.get("done") is True:
            break
    return "".join(parts), finish_reason


def build_nonstream_response(content: str, settings: Settings) -> dict[str, object]:
    created = int(time.time())
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex}",
        "object": "chat.completion",
        "created": created,
        "model": settings.upstream.model_alias,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
    }
```

```python
# src/fscut_openai_proxy/upstream.py
import httpx

from fscut_openai_proxy.auth import AuthManager
from fscut_openai_proxy.config import Settings


class UpstreamClient:
    def __init__(self, settings: Settings, auth_manager: AuthManager) -> None:
        self._settings = settings
        self._auth_manager = auth_manager

    def post_chat(self, payload: dict[str, object]) -> httpx.Response:
        token = self._auth_manager.current_access_token()
        endpoint = httpx.URL(
            f"{self._settings.upstream.base_url}/api/agents/chat/{self._settings.upstream.agent_endpoint}"
        )
        return httpx.post(
            str(endpoint),
            json=payload,
            headers={"Authorization": f"Bearer {token}", "Accept": "*/*"},
            timeout=300.0,
        )
```

```python
# replace src/fscut_openai_proxy/api.py
from pathlib import Path

from fastapi import APIRouter, Depends, Header, HTTPException

from fscut_openai_proxy.auth import AuthManager
from fscut_openai_proxy.config import Settings, get_settings
from fscut_openai_proxy.schemas import ChatCompletionRequest
from fscut_openai_proxy.token_store import FileBackedTokenStore, TokenState
from fscut_openai_proxy.translator import build_nonstream_response, build_upstream_payload, collect_text_from_sse_lines
from fscut_openai_proxy.upstream import UpstreamClient


def require_local_api_key(
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> None:
    expected = f"Bearer {settings.server.local_api_key}"
    if authorization != expected:
        raise HTTPException(
            status_code=401,
            detail={
                "error": {
                    "message": "Invalid local API key",
                    "type": "authentication_error",
                    "code": "local_api_key_invalid",
                    "retryable": False,
                }
            },
        )


def get_auth_manager(settings: Settings = Depends(get_settings)) -> AuthManager:
    store = FileBackedTokenStore(
        path=Path(settings.auth.state_path),
        initial_state=TokenState(
            access_token=settings.auth.access_token,
            refresh_token=settings.auth.refresh_token,
            connect_sid=settings.auth.connect_sid,
            token_provider=settings.auth.token_provider,
        ),
    )
    return AuthManager(token_store=store, refresh_margin_seconds=settings.auth.refresh_margin_seconds)


router = APIRouter()


@router.get("/v1/models", dependencies=[Depends(require_local_api_key)])
def list_models(settings: Settings = Depends(get_settings)) -> dict[str, object]:
    return {
        "object": "list",
        "data": [
            {
                "id": settings.upstream.model_alias,
                "object": "model",
                "owned_by": "fscut-proxy",
            }
        ],
    }


@router.post("/v1/chat/completions", dependencies=[Depends(require_local_api_key)])
def chat_completions(
    request: ChatCompletionRequest,
    settings: Settings = Depends(get_settings),
    auth_manager: AuthManager = Depends(get_auth_manager),
) -> dict[str, object]:
    client = UpstreamClient(settings=settings, auth_manager=auth_manager)
    payload = build_upstream_payload(request)
    response = client.post_chat(payload)
    response.raise_for_status()
    content, _ = collect_text_from_sse_lines(response.text.splitlines())
    return build_nonstream_response(content=content, settings=settings)
```

- [ ] **Step 4: 运行测试确认通过**

Run:

```bash
conda run -n test pytest tests/test_chat_nonstream.py tests/test_request_validation.py -v
```

Expected: `test_chat_nonstream.py` PASS；若 `test_request_validation.py` 仍未通过，则补齐未知模型错误映射直到一起 PASS。

- [ ] **Step 5: Commit**

```bash
git add src/fscut_openai_proxy/schemas.py src/fscut_openai_proxy/translator.py src/fscut_openai_proxy/upstream.py src/fscut_openai_proxy/api.py tests/test_chat_nonstream.py
git commit -m "feat: add non-stream chat completions adapter"
```

### Task 6: SSE 流式转发

**Files:**
- Modify: `src/fscut_openai_proxy/translator.py`
- Modify: `src/fscut_openai_proxy/upstream.py`
- Modify: `src/fscut_openai_proxy/api.py`
- Create: `tests/test_chat_stream.py`

- [ ] **Step 1: 写失败测试，锁定 OpenAI SSE 形态**

```python
import httpx
import respx
from fastapi.testclient import TestClient

from fscut_openai_proxy.app import create_app


@respx.mock
def test_chat_completions_stream_returns_openai_sse() -> None:
    respx.post("https://chat.fscut.com/api/agents/chat/%E5%86%85%E9%83%A8%E6%A8%A1%E5%9E%8B-vllm-GLM4.7-flash").mock(
        return_value=httpx.Response(
            200,
            text='data: {"delta":"你"}\\n\\ndata: {"delta":"好"}\\n\\ndata: {"done":true}\\n\\n',
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
    assert 'chat.completion.chunk' in body
    assert '"content":"你"' in body
    assert '"content":"好"' in body
    assert 'data: [DONE]' in body
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```bash
conda run -n test pytest tests/test_chat_stream.py -v
```

Expected: FAIL，说明当前实现没有流式输出。

- [ ] **Step 3: 写最小流式实现**

```python
# append to src/fscut_openai_proxy/translator.py
import json
import time
import uuid
from collections.abc import Iterable, Iterator


def to_openai_sse_chunks(lines: Iterable[str], model_alias: str) -> Iterator[str]:
    request_id = f"chatcmpl-{uuid.uuid4().hex}"
    created = int(time.time())
    yield (
        'data: '
        + json.dumps(
            {
                "id": request_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": model_alias,
                "choices": [{"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}],
            },
            ensure_ascii=False,
        )
        + "\n\n"
    )
    for line in lines:
        if not line.startswith("data: "):
            continue
        payload = line[6:]
        if payload == "[DONE]":
            break
        data = json.loads(payload)
        delta = data.get("delta")
        if isinstance(delta, str) and delta:
            yield (
                'data: '
                + json.dumps(
                    {
                        "id": request_id,
                        "object": "chat.completion.chunk",
                        "created": created,
                        "model": model_alias,
                        "choices": [{"index": 0, "delta": {"content": delta}, "finish_reason": None}],
                    },
                    ensure_ascii=False,
                )
                + "\n\n"
            )
        if data.get("done") is True:
            yield (
                'data: '
                + json.dumps(
                    {
                        "id": request_id,
                        "object": "chat.completion.chunk",
                        "created": created,
                        "model": model_alias,
                        "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
                    },
                    ensure_ascii=False,
                )
                + "\n\n"
            )
            break
    yield "data: [DONE]\n\n"
```

```python
# replace src/fscut_openai_proxy/upstream.py
import httpx

from fscut_openai_proxy.auth import AuthManager
from fscut_openai_proxy.config import Settings


class UpstreamClient:
    def __init__(self, settings: Settings, auth_manager: AuthManager) -> None:
        self._settings = settings
        self._auth_manager = auth_manager

    def post_chat(self, payload: dict[str, object]) -> httpx.Response:
        token = self._auth_manager.current_access_token()
        endpoint = httpx.URL(
            f"{self._settings.upstream.base_url}/api/agents/chat/{self._settings.upstream.agent_endpoint}"
        )
        return httpx.post(
            str(endpoint),
            json=payload,
            headers={"Authorization": f"Bearer {token}", "Accept": "*/*"},
            timeout=300.0,
        )
```

```python
# replace chat_completions in src/fscut_openai_proxy/api.py
from fastapi.responses import StreamingResponse

from fscut_openai_proxy.translator import (
    build_nonstream_response,
    build_upstream_payload,
    collect_text_from_sse_lines,
    to_openai_sse_chunks,
)


@router.post("/v1/chat/completions", dependencies=[Depends(require_local_api_key)])
def chat_completions(
    request: ChatCompletionRequest,
    settings: Settings = Depends(get_settings),
    auth_manager: AuthManager = Depends(get_auth_manager),
):
    client = UpstreamClient(settings=settings, auth_manager=auth_manager)
    payload = build_upstream_payload(request)
    response = client.post_chat(payload)
    response.raise_for_status()
    lines = response.text.splitlines()
    if request.stream:
        return StreamingResponse(
            to_openai_sse_chunks(lines=lines, model_alias=settings.upstream.model_alias),
            media_type="text/event-stream",
        )
    content, _ = collect_text_from_sse_lines(lines)
    return build_nonstream_response(content=content, settings=settings)
```

- [ ] **Step 4: 运行测试确认通过**

Run:

```bash
conda run -n test pytest tests/test_chat_stream.py tests/test_chat_nonstream.py -v
```

Expected: PASS。

- [ ] **Step 5: Commit**

```bash
git add src/fscut_openai_proxy/translator.py src/fscut_openai_proxy/upstream.py src/fscut_openai_proxy/api.py tests/test_chat_stream.py
git commit -m "feat: stream upstream sse as openai chat chunks"
```

### Task 7: 错误映射、401 刷新重试、README

**Files:**
- Create: `src/fscut_openai_proxy/errors.py`
- Create: `src/fscut_openai_proxy/logging_config.py`
- Modify: `src/fscut_openai_proxy/auth.py`
- Modify: `src/fscut_openai_proxy/token_store.py`
- Modify: `src/fscut_openai_proxy/upstream.py`
- Modify: `src/fscut_openai_proxy/app.py`
- Modify: `tests/test_health.py`
- Create: `README.md`

- [ ] **Step 1: 写失败测试，锁定 401 后刷新一次并重试**

```python
import httpx
import respx
from fastapi.testclient import TestClient

from fscut_openai_proxy.app import create_app


def test_healthz_includes_request_id_header() -> None:
    client = TestClient(create_app())
    response = client.get("/healthz")

    assert response.status_code == 200
    assert "x-request-id" in response.headers
    assert response.headers["x-request-id"]


@respx.mock
def test_chat_retries_once_after_refresh() -> None:
    chat_url = "https://chat.fscut.com/api/agents/chat/%E5%86%85%E9%83%A8%E6%A8%A1%E5%9E%8B-vllm-GLM4.7-flash"
    refresh_url = "https://chat.fscut.com/api/auth/refresh"

    respx.post(chat_url).mock(
        side_effect=[
            httpx.Response(401, json={"message": "expired"}),
            httpx.Response(
                200,
                text='data: {"delta":"好"}\\n\\ndata: {"done":true}\\n\\n',
                headers={"content-type": "text/event-stream"},
            ),
        ]
    )
    respx.post(refresh_url).mock(
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
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```bash
conda run -n test pytest tests/test_auth_refresh.py tests/test_chat_nonstream.py -v
```

Expected: FAIL，说明还没有 401 后重试机制。

- [ ] **Step 3: 写最小实现**

```python
# src/fscut_openai_proxy/errors.py
class UpstreamAuthExpiredError(Exception):
    def __init__(self) -> None:
        self.status_code = 502
        self.detail = {
            "error": {
                "message": "Upstream authentication expired",
                "type": "upstream_auth_error",
                "code": "upstream_auth_expired",
                "retryable": False,
            }
        }


class UpstreamRateLimitError(Exception):
    def __init__(self) -> None:
        self.status_code = 429
        self.detail = {
            "error": {
                "message": "Upstream rate limit exceeded",
                "type": "rate_limit_error",
                "code": "upstream_rate_limited",
                "retryable": True,
            }
        }
```

```python
# replace src/fscut_openai_proxy/upstream.py
import httpx

from fscut_openai_proxy.auth import AuthManager, RefreshClient
from fscut_openai_proxy.config import Settings
from fscut_openai_proxy.errors import UpstreamAuthExpiredError, UpstreamRateLimitError


class UpstreamClient:
    def __init__(self, settings: Settings, auth_manager: AuthManager) -> None:
        self._settings = settings
        self._auth_manager = auth_manager
        self._refresh_client = RefreshClient(settings.upstream.base_url, auth_manager.token_store)

    def _do_post(self, payload: dict[str, object]) -> httpx.Response:
        try:
            token = self._auth_manager.current_access_token()
        except RuntimeError:
            self._refresh_client.refresh()
            token = self._auth_manager.current_access_token()
        endpoint = httpx.URL(
            f"{self._settings.upstream.base_url}/api/agents/chat/{self._settings.upstream.agent_endpoint}"
        )
        return httpx.post(
            str(endpoint),
            json=payload,
            headers={"Authorization": f"Bearer {token}", "Accept": "*/*"},
            timeout=300.0,
        )

    def post_chat(self, payload: dict[str, object]) -> httpx.Response:
        response = self._do_post(payload)
        if response.status_code == 401:
            self._refresh_client.refresh()
            response = self._do_post(payload)
        if response.status_code == 401:
            raise UpstreamAuthExpiredError()
        if response.status_code == 429:
            raise UpstreamRateLimitError()
        response.raise_for_status()
        return response
```

```python
# replace src/fscut_openai_proxy/auth.py
import base64
import json
import re
import time
from typing import Any

import httpx

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
        response.raise_for_status()
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
```

```python
# src/fscut_openai_proxy/logging_config.py
import logging
import uuid
from collections.abc import Awaitable, Callable

from fastapi import Request, Response


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


async def inject_request_id(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    request_id = uuid.uuid4().hex
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["x-request-id"] = request_id
    return response
```

```python
# replace src/fscut_openai_proxy/app.py
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from fscut_openai_proxy.api import router
from fscut_openai_proxy.config import get_settings
from fscut_openai_proxy.logging_config import configure_logging, inject_request_id


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging()
    app = FastAPI(title="fscut-openai-proxy")
    app.middleware("http")(inject_request_id)

    @app.exception_handler(Exception)
    async def handle_exception(request: Request, exc: Exception) -> JSONResponse:
        if hasattr(exc, "detail") and isinstance(exc.detail, dict):
            response = JSONResponse(status_code=getattr(exc, "status_code", 500), content=exc.detail)
            response.headers["x-request-id"] = getattr(request.state, "request_id", "")
            return response
        response = JSONResponse(
            status_code=500,
            content={
                "error": {
                    "message": "Internal server error",
                    "type": "server_error",
                    "code": "internal_error",
                    "retryable": False,
                }
            },
        )
        response.headers["x-request-id"] = getattr(request.state, "request_id", "")
        return response

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {
            "status": "ok",
            "service": "fscut-openai-proxy",
            "upstream": settings.upstream.base_url,
            "model_alias": settings.upstream.model_alias,
        }

    app.include_router(router)
    return app
```

```md
# README.md

## FSCUT OpenAI Proxy

本项目把 `chat.fscut.com` 的单模型文本聊天能力适配为本地 OpenAI 兼容接口。

### 已实现

- `GET /healthz`
- `GET /v1/models`
- `POST /v1/chat/completions`
- `stream=true`
- `stream=false`

### 默认地址

- `http://127.0.0.1:8787`

### 默认模型

- `glm-4.7-flash`

### 启动

```bash
conda run -n test python -m fscut_openai_proxy
```

### 注意

- 只监听本机
- 不要把上游 token 提交到仓库
- 上游 refresh 契约必须以真实抓包为准
```

- [ ] **Step 4: 运行测试确认通过**

Run:

```bash
conda run -n test pytest tests/test_health.py tests/test_models.py tests/test_auth_refresh.py tests/test_chat_nonstream.py tests/test_chat_stream.py tests/test_request_validation.py -v
```

Expected: 全部 PASS。

- [ ] **Step 5: Commit**

```bash
git add src/fscut_openai_proxy/errors.py src/fscut_openai_proxy/logging_config.py src/fscut_openai_proxy/auth.py src/fscut_openai_proxy/upstream.py README.md
git commit -m "feat: add retrying upstream auth and project runbook"
```

## Self-Review

### Spec coverage

- 本地 OpenAI 兼容接口：Task 2、Task 3、Task 5、Task 6
- 单模型 `glm-4.7-flash`：Task 3、Task 5
- 自动刷新：Task 4、Task 7
- 上游真实契约固化：Task 1
- 结构化模块边界：Task 2 到 Task 7
- 错误模型与最小可观测性：Task 7

无缺口。

### Placeholder scan

- 计划中没有 `TODO` / `TBD`
- 唯一允许变化的是 Task 1 抓到真实上游契约后，对 Task 4 的 refresh 细节和 Task 5 的聊天 payload 细节做“按真实契约替换”
- 这不是占位，而是已明确列出的实现前校验条件

### Type consistency

- 对外模型名统一为 `glm-4.7-flash`
- 上游 endpoint 统一为 `内部模型-vllm-GLM4.7-flash`
- 本地鉴权错误统一 `local_api_key_invalid`
- 上游鉴权错误统一 `upstream_auth_expired`

一致。
