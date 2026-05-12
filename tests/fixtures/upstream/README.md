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

## 已确认的聊天请求头契约

2026-05-12 已从 Chrome DevTools 确认聊天请求至少需要以下认证材料：

```text
Authorization: Bearer [REDACTED_ACCESS_TOKEN]
Cookie: connect.sid=[REDACTED_SESSION]; token_provider=openid; refreshToken=[REDACTED_REFRESH_TOKEN]
```

同时已确认响应会返回限流头：

- `x-ratelimit-limit`
- `x-ratelimit-remaining`
- `x-ratelimit-reset`

详见 `chat_request_headers_redacted.md`。该文件只保存打码后的字段结构，禁止保存原始 token、cookie、邮箱、手机号或用户身份字段。

## 聊天请求体采集步骤

1. 打开 Chrome DevTools -> Network。
2. 新开会话，发送最短测试文本，例如 `1`。
3. 找到 `POST /api/agents/chat/内部模型-vllm-GLM4.7-flash`。
4. 复制 Request Payload。
5. 保存到 `tests/fixtures/upstream/chat_request_real.json`。

## SSE 响应采集步骤

在 DevTools 中打开刚才那条聊天请求：

- 复制 Response 原文。
- 保存到 `tests/fixtures/upstream/chat_stream_real.txt`。
- 保留原始 `event` / `data` 分隔，不要重新格式化。

## Refresh 契约采集步骤

触发一次 access token 刷新或重新登录后：

- 保存 refresh 请求说明到 `tests/fixtures/upstream/refresh_request_real.md`。
- 保存 refresh 响应 JSON 到 `tests/fixtures/upstream/refresh_response_real.json`。
- 所有 token 只保留前 8 位和后 6 位，中间打码。

