# Redacted Chat Request Snapshot

采集时间：2026-05-12 17:45:15 Asia/Shanghai

来源：Chrome DevTools Network，已人工打码。禁止把原始 token、cookie、邮箱、手机号或用户身份字段写入仓库。

## Response

- Status: `200 OK`
- Content-Type: `text/event-stream`
- Rate limit headers:
  - `x-ratelimit-limit: 40`
  - `x-ratelimit-remaining: 39`
  - `x-ratelimit-reset: 1778579176`

## Request

- Method: `POST`
- URL: `https://chat.fscut.com/api/agents/chat/%E5%86%85%E9%83%A8%E6%A8%A1%E5%9E%8B-vllm-GLM4.7-flash`
- Referrer: `https://chat.fscut.com/c/new`
- Content-Type: `application/json`
- Accept: `*/*`
- Origin: `https://chat.fscut.com`

## Required Auth Materials

```text
Authorization: Bearer [REDACTED_ACCESS_TOKEN]
Cookie: connect.sid=[REDACTED_SESSION]; token_provider=openid; refreshToken=[REDACTED_REFRESH_TOKEN]
```

## Implementation Notes

- Chat requests must send both `Authorization` and the three auth cookies.
- `Origin` and `Referer` should match the browser request shape.
- Downstream responses should preserve `x-ratelimit-limit`, `x-ratelimit-remaining`, and `x-ratelimit-reset` when upstream provides them.
- The actual JSON request body is still not captured in this redacted note; save it separately as `chat_request_real.json` only after removing sensitive values.

