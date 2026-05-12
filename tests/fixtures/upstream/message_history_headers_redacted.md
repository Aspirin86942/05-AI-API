# Redacted Message History Request Snapshot

采集时间：2026-05-12 17:45:21 Asia/Shanghai

来源：Chrome DevTools Network，已人工打码。禁止把原始 token、cookie、邮箱、手机号、用户身份字段或真实会话 id 写入仓库。

## Response

- Status: `200 OK`
- Content-Type: `application/json; charset=utf-8`
- Content-Encoding: `br`
- ETag: `[REDACTED_ETAG]`

## Request

- Method: `GET`
- URL pattern: `https://chat.fscut.com/api/messages/{conversation_id}`
- Referrer pattern: `https://chat.fscut.com/c/{conversation_id}`
- Accept: `application/json, text/plain, */*`
- Conditional cache header: `If-None-Match: [REDACTED_ETAG]`

## Required Auth Materials

```text
Authorization: Bearer [REDACTED_ACCESS_TOKEN]
Cookie: connect.sid=[REDACTED_SESSION]; token_provider=openid; refreshToken=[REDACTED_REFRESH_TOKEN]
```

## Implementation Notes

- This endpoint is useful for future conversation/history support, not required by the first local OpenAI-compatible chat proxy.
- It confirms message-history reads use the same upstream auth materials as chat requests.
- The upstream supports cache validation through `ETag` and `If-None-Match`.
- If later we support upstream conversation reuse, this endpoint can help inspect or hydrate the upstream message tree by `conversation_id`.

