# FSCUT OpenAI 兼容代理设计

日期：2026-05-12

## 1. 背景

目标是在本机常驻运行一个后台服务，把公司内部 `https://chat.fscut.com` 的聊天能力适配成 OpenAI 兼容接口，供以下客户端接入：

- Python 脚本
- Node.js 脚本
- Cherry Studio
- 腾讯 WorkBuddy

本期范围已经明确为：

- 仅本机使用，不对外网暴露
- 第一版只支持文本对话
- 第一版只接一个上游模型：`内部模型-vllm-GLM4.7-flash`
- 登录态由用户手工提供一次，程序负责自动续期
- 对外接口采用 OpenAI 兼容形式

## 2. 已确认事实

以下事实基于 2026-05-12 的页面访问、静态资源分析和用户抓包结果：

### 2.1 页面与系统形态

- `https://chat.fscut.com/c/new` 可正常访问，返回前端页面 `BochuChat`
- 前端为打包后的 Web 应用，存在明确的同源 `/api/...` 调用
- 匿名可读接口至少包括：
  - `GET /api/config`
  - `GET /api/endpoints`
- 登录后接口至少包括：
  - `GET /api/user`
  - `GET /api/models`
  - `GET /api/messages/{conversation_id}`

### 2.2 聊天主链路

已抓到一条真实发消息请求：

- 上游请求方法：`POST`
- 上游请求路径：`/api/agents/chat/%E5%86%85%E9%83%A8%E6%A8%A1%E5%9E%8B-vllm-GLM4.7-flash`
- 上游响应状态：`200 OK`
- 上游响应类型：`text/event-stream`
- 上游存在限流响应头：
  - `x-ratelimit-limit`
  - `x-ratelimit-remaining`
  - `x-ratelimit-reset`

### 2.3 鉴权形态

已确认请求中存在以下认证材料：

- `Authorization: Bearer <access_token>`
- `Cookie: connect.sid=...`
- `Cookie: token_provider=openid`
- `Cookie: refreshToken=...`

并且系统存在刷新相关接口与身份源线索：

- `POST /api/auth/refresh` 或等价刷新链路存在
- `iss` 指向 `https://auth.fscut.com/realms/fscut`
- `azp` 为 `librechat`

### 2.4 已确认的单模型目标

第一版仅代理一个本地别名模型：

- OpenAI 对外模型名：`glm-4.7-flash`
- 上游 endpoint 名：`内部模型-vllm-GLM4.7-flash`

## 3. 无确切信息

以下内容目前没有确切信息，必须在实现前抓包或最小化实验确认，禁止臆测后直接编码：

### 3.1 上游聊天请求体精确结构

虽然已确认聊天入口是 `POST /api/agents/chat/{endpoint}`，但尚无确切信息说明请求 JSON 的完整字段名、必填项、默认值和会话字段结构。

必须确认：

- 消息数组字段名
- 是否需要 `conversationId`
- 是否需要 `parentMessageId`
- 是否需要系统参数区块
- 是否支持显式 `stream`
- 是否支持 `temperature`、`top_p`、`max_tokens`

### 3.2 SSE 事件格式

尚无确切信息说明上游 `text/event-stream` 的事件名称与数据结构。

必须确认：

- 是否使用 `event:` 行
- `data:` 的 JSON 结构
- 增量文本字段名
- 结束事件标识
- 错误事件标识
- 是否在最终事件里返回 token 用量

### 3.3 刷新接口契约

虽然接口路径与令牌形态已知，但以下内容没有确切信息：

- 刷新时到底是使用 header、body、cookie，还是三者组合
- `refreshToken` 是否既要放 body 又要放 cookie
- 成功响应里是否返回新的 `access_token`
- 是否返回新的 `refresh_token`
- `connect.sid` 是否会轮换

### 3.4 WorkBuddy 的兼容边界

当前只知道目标客户端包含腾讯 WorkBuddy，但无确切信息说明它使用的是：

- `POST /v1/chat/completions`
- `GET /v1/models`
- 还是额外依赖其他 OpenAI 兼容字段

因此第一版按主流 OpenAI Chat Completions 兼容实现，实际接入时再做小范围补齐。

## 4. 范围

### 4.1 本期范围内

- 本地 HTTP 服务，默认只监听 `127.0.0.1`
- `GET /healthz`
- `GET /v1/models`
- `POST /v1/chat/completions`
- 支持 `stream=false`
- 支持 `stream=true`
- 支持 OpenAI 风格 `Authorization: Bearer <local_api_key>`
- 支持本地配置文件加载上游鉴权信息
- 支持 access token 过期前自动刷新
- 支持把上游 SSE 转译成 OpenAI SSE
- 支持基础日志、错误模型、限流透传

### 4.2 本期范围外

- 图片、多模态输入
- 文件上传
- function calling / tools
- `responses` API
- `embeddings` API
- 多模型路由
- 浏览器自动登录
- OAuth 登录流程接管
- 分布式部署
- 面向公网暴露

## 5. 方案比较

### 5.1 方案 A：薄适配层

对外只暴露 OpenAI 兼容接口，内部完成：

- 本地 API Key 校验
- 上游令牌管理
- OpenAI 请求转上游请求
- 上游 SSE 转 OpenAI SSE

优点：

- 实现最短
- 出错面最小
- 最适合脚本和桌面客户端接入

缺点：

- 只覆盖聊天主链路
- 后续扩展更多企业站能力时需要再加模块

### 5.2 方案 B：带本地会话状态的代理层

在方案 A 基础上，本地维护对话状态、message id、缓存和恢复。

优点：

- 后续扩展空间更大
- 便于做审计和恢复

缺点：

- 复杂度明显提高
- 第一版会把时间花在会话系统而不是“先打通”

### 5.3 方案 C：浏览器耦合代理

复用浏览器 Cookie 与页面行为，程序只负责简单转发。

优点：

- 起步快

缺点：

- 易失效
- 不适合后台长期运行
- 维护成本最高

### 5.4 结论

采用 **方案 A：薄适配层**。

理由：

- 用户明确表示第一版只要“足够用”
- 当前范围是单模型、文本对话、本地使用
- 兼容 Python/Node/Cherry Studio/WorkBuddy 的关键，在于标准 OpenAI 接口，而不是本地会话系统

## 6. 对外 API 契约

### 6.1 `GET /healthz`

用途：

- 本地进程健康检查

成功响应：

```json
{
  "status": "ok",
  "service": "fscut-openai-proxy",
  "upstream": "https://chat.fscut.com",
  "model_alias": "glm-4.7-flash"
}
```

### 6.2 `GET /v1/models`

返回单模型列表：

```json
{
  "object": "list",
  "data": [
    {
      "id": "glm-4.7-flash",
      "object": "model",
      "owned_by": "fscut-proxy"
    }
  ]
}
```

### 6.3 `POST /v1/chat/completions`

第一版支持的请求字段：

- `model`
- `messages`
- `stream`
- `temperature`
- `top_p`
- `max_tokens`
- `stop`
- `user`

第一版接受但会显式拒绝的字段：

- `tools`
- `tool_choice`
- `functions`
- `function_call`
- `response_format`
- `modalities`
- `audio`
- `n > 1`

### 6.4 消息内容兼容规则

接受：

- `messages[].content` 为字符串
- `messages[].content` 为数组，但数组项仅允许文本片段

拒绝：

- 图片片段
- 音频片段
- 文件片段
- `tool` 角色消息

### 6.5 非流式响应

对外返回标准 `chat.completion`：

```json
{
  "id": "chatcmpl-local-001",
  "object": "chat.completion",
  "created": 1778570000,
  "model": "glm-4.7-flash",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "你好"
      },
      "finish_reason": "stop"
    }
  ]
}
```

说明：

- 若上游没有可靠 usage，则不伪造 token 数
- 若最终拿不到 finish reason，则按 `stop` 处理并记录日志

### 6.6 流式响应

对外返回标准 `text/event-stream`：

```text
data: {"id":"chatcmpl-local-001","object":"chat.completion.chunk","created":1778570000,"model":"glm-4.7-flash","choices":[{"index":0,"delta":{"role":"assistant"},"finish_reason":null}]}

data: {"id":"chatcmpl-local-001","object":"chat.completion.chunk","created":1778570000,"model":"glm-4.7-flash","choices":[{"index":0,"delta":{"content":"你"},"finish_reason":null}]}

data: {"id":"chatcmpl-local-001","object":"chat.completion.chunk","created":1778570000,"model":"glm-4.7-flash","choices":[{"index":0,"delta":{"content":"好"},"finish_reason":null}]}

data: {"id":"chatcmpl-local-001","object":"chat.completion.chunk","created":1778570000,"model":"glm-4.7-flash","choices":[{"index":0,"delta":{},"finish_reason":"stop"}]}

data: [DONE]
```

## 7. 核心架构

### 7.1 模块划分

建议采用 Python 3.10+ + FastAPI + httpx：

- `config.py`
  - 读取本地配置
  - 校验必填项
- `schemas.py`
  - 定义 OpenAI 请求响应模型
- `token_store.py`
  - 内存态与磁盘态令牌存取
- `auth.py`
  - access token 过期判断
  - refresh 调度
  - 401 后兜底刷新
- `upstream.py`
  - 封装对 `chat.fscut.com` 的 HTTP 调用
  - 统一设置 header/cookie
- `translator.py`
  - OpenAI 请求转上游请求
  - 上游 SSE 转 OpenAI SSE
- `api.py`
  - 暴露 `healthz`、`v1/models`、`v1/chat/completions`
- `logging_config.py`
  - 结构化日志
- `errors.py`
  - 统一错误模型与异常映射

### 7.2 设计边界

必须保持三个边界清晰：

- **本地客户端鉴权** 与 **上游站点鉴权** 分离
  - 本地客户端永远不知道上游 token
- **OpenAI 协议** 与 **上游协议** 分离
  - 所有格式转换集中在 translator 层
- **刷新逻辑** 与 **聊天逻辑** 分离
  - 便于以后切换鉴权方式

## 8. 数据流

### 8.1 非流式

1. 客户端请求 `POST /v1/chat/completions`
2. 本地校验本地 API Key
3. 校验 `model == glm-4.7-flash`
4. `AuthManager` 获取可用 access token
5. `Translator` 把 OpenAI messages 映射为上游请求体
6. `UpstreamClient` 发起上游聊天请求
7. 消费上游 SSE，聚合出完整文本
8. 转成 OpenAI 非流式 JSON 响应

### 8.2 流式

1. 前 1 到 6 步相同
2. 逐条读取上游 SSE
3. 抽取增量文本
4. 逐条输出 OpenAI chunk
5. 输出 `[DONE]`

## 9. 配置与密钥管理

### 9.1 本地配置来源

默认配置文件建议放在：

- Windows：`%APPDATA%\\fscut-openai-proxy\\config.toml`

可通过环境变量覆盖：

- `FSCUT_PROXY_CONFIG`

### 9.2 配置项

建议配置结构：

```toml
[server]
host = "127.0.0.1"
port = 8787
local_api_key = "replace-with-local-key"

[upstream]
base_url = "https://chat.fscut.com"
agent_endpoint = "内部模型-vllm-GLM4.7-flash"
model_alias = "glm-4.7-flash"
connect_timeout_seconds = 15
read_timeout_seconds = 300

[auth]
access_token = "replace-with-access-token"
refresh_token = "replace-with-refresh-token"
connect_sid = "replace-with-connect-sid"
token_provider = "openid"
refresh_margin_seconds = 60
```

### 9.3 安全要求

- 不把上游 token 写入项目代码
- 不把 token 打进普通日志
- 配置文件权限尽量收紧到当前用户
- 本地服务默认只监听 `127.0.0.1`
- 本地服务仍要求 `local_api_key`

## 10. 鉴权与续期策略

### 10.1 access token 生命周期

access token 的过期时间可通过 JWT `exp` 读取，用于“本地过期判断”，但不用于信任校验。

策略：

- 每次请求前检查 access token 是否将在 `refresh_margin_seconds` 内过期
- 若即将过期，先走 refresh
- 若请求上游返回 401，再兜底刷新一次并重试一次

### 10.2 refresh 结果持久化

若刷新成功并返回新 token：

- 更新内存态
- 原子写回本地配置或单独状态文件

若刷新失败：

- 不做无限重试
- 返回本地 502 或 401 风格错误
- 明确提示“上游登录态失效，需要重新录入凭据”

## 11. 错误模型

对外采用 OpenAI 风格错误结构：

```json
{
  "error": {
    "message": "Upstream authentication expired",
    "type": "upstream_auth_error",
    "code": "upstream_auth_expired",
    "retryable": false
  }
}
```

错误分类：

- `invalid_request_error`
  - 请求字段不支持
  - 模型名不匹配
- `authentication_error`
  - 本地 API Key 错误
- `upstream_auth_error`
  - 上游登录态失效
- `rate_limit_error`
  - 上游 429
- `bad_gateway`
  - 上游结构异常
- `upstream_unavailable`
  - 网络失败、超时、5xx

## 12. 日志与可观测性

### 12.1 日志原则

默认不记录：

- 完整 prompt
- 完整响应正文
- access token
- refresh token
- `connect.sid`

默认记录：

- `request_id`
- 请求时间
- 客户端 IP
- 模型名
- 是否流式
- 上游耗时
- 总耗时
- 上游状态码
- 本地下游状态码
- 输出字符数

### 12.2 请求关联

每个请求生成本地 `request_id`，贯穿：

- 本地日志
- 上游调用日志
- 错误响应头 `x-request-id`

## 13. 测试策略

### 13.1 单元测试

- 配置加载校验
- 本地 API Key 鉴权
- OpenAI 请求校验
- 模型列表输出
- JWT 过期判断
- refresh 触发条件
- OpenAI 消息转上游消息
- 上游 SSE 转 OpenAI SSE

### 13.2 集成测试

使用 `respx` 或等效 HTTP mock：

- mock `POST /api/auth/refresh`
- mock `POST /api/agents/chat/{endpoint}`
- 验证流式与非流式
- 验证 401 后自动刷新再重试
- 验证 429 透传

### 13.3 人工冒烟

- `curl` 非流式聊天
- `curl` 流式聊天
- Python OpenAI SDK 直连
- Cherry Studio 通过自定义 OpenAI 接口接入
- WorkBuddy 通过 OpenAI 兼容配置接入

## 14. 运行方式

第一版建议作为 Python 服务运行：

```bash
conda run -n test python -m fscut_openai_proxy serve --config C:\path\to\config.toml
```

后续如需要再增加：

- Windows 后台启动脚本
- `nssm` 服务化说明
- 单文件打包

## 15. 风险

### 15.1 最大风险

当前最大风险不是本地 OpenAI 兼容层，而是上游契约未完全确认：

- 聊天请求体未知
- SSE 事件结构未知
- refresh 契约未知

因此实现必须把“抓包固化成 fixture”放在第一任务。

### 15.2 次级风险

- 上游页面升级后接口字段变动
- refresh 令牌轮换但本地未持久化
- Cherry Studio 或 WorkBuddy 要求额外字段

## 16. 后续扩展

第二阶段如需要，可扩展：

- 多模型映射
- `responses` API
- 多模态
- 本地对话缓存
- Windows 服务安装器

## 17. 结论

第一版应实现一个 **本地、单模型、文本专用、OpenAI 兼容的薄适配层**：

- 对外只提供 `healthz`、`models`、`chat.completions`
- 对内只依赖 `auth refresh + agent chat SSE`
- 显式区分“已确认事实”和“待抓包确认契约”

这条路径在正确性、可维护性、可观测性之间最平衡，足够支撑当前用户场景。
