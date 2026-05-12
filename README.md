# FSCUT OpenAI Proxy

本项目把 `chat.fscut.com` 的单模型文本聊天能力适配为本地 OpenAI 兼容接口。

## 已实现

- `GET /healthz`
- `GET /v1/models`
- `POST /v1/chat/completions`
- `stream=true`
- `stream=false`

## 默认地址

- `http://127.0.0.1:8787`

## 默认模型

- `glm-4.7-flash`

## 启动

```bash
conda run -n test python -m fscut_openai_proxy
```

## 配置

默认读取 `%APPDATA%\fscut-openai-proxy\config.toml`，也可以通过 `FSCUT_PROXY_CONFIG` 指定配置文件路径。

```toml
[server]
host = "127.0.0.1"
port = 8787
local_api_key = "replace-with-local-key"

[upstream]
base_url = "https://chat.fscut.com"
agent_endpoint = "内部模型-vllm-GLM4.7-flash"
model_alias = "glm-4.7-flash"

[auth]
access_token = "replace-with-access-token"
refresh_token = "replace-with-refresh-token"
connect_sid = "replace-with-connect-sid"
token_provider = "openid"
refresh_margin_seconds = 60
```

## 注意

- 只监听本机。
- 不要把上游 token 提交到仓库。
- 上游 refresh 契约必须以真实抓包为准。

