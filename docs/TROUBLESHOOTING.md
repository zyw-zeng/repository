# 常见问题排查

## 后端无法启动

- 启动目标必须是 `app.main:app`，不是 `main:repository`。
- 在项目根目录执行命令，并确认虚拟环境中的依赖已安装。
- 先运行 `python -m alembic upgrade head`，再启动 Uvicorn。
- 宝塔启动命令中不要写 `cd`；项目路径应在面板的“项目路径”字段单独配置。

## 前端接口返回 404

- 浏览器请求应形如 `/api/backend/api/v1/...`，由 Next.js 代理到 FastAPI 的 `/api/v1/...`。
- 若日志出现 `/api/backend/api/backend/`，说明前端重复拼接了代理前缀。
- 检查生产环境 Nginx 是否把 `/` 转发给 Next.js，且没有二次改写 `/api/backend`。
- 打开 FastAPI `/docs`，确认目标路由已经注册并重启了正确的后端进程。

## SSE 中断或 `ERR_INCOMPLETE_CHUNKED_ENCODING`

- Nginx 对 SSE 路由应关闭响应缓冲和缓存，并设置足够长的读取超时。
- 确认后端持续发送 heartbeat，异常通过 `event: error` 正常结束流。
- 检查浏览器网络面板中的最后一个 SSE 事件，再按相同 `request_id` 查询服务端日志。
- “Permissions policy violation: unload”通常来自浏览器扩展，不是应用的 SSE 故障。

## 模型或 Embedding 报错

- 确认 `.env` 中 `DASHSCOPE_API_KEY` 已填写且后端进程已重启。
- Chat 与 Embedding 的兼容接口参数不同，不要向 Embedding 发送 Token ID 数组。
- 使用 `scripts/verify_models.py` 做最小连通测试；该命令会产生少量真实调用费用。
- 频繁超时时检查服务器到阿里云接口的网络、模型名称、并发限制和账户额度。

## 知识库总是拒答

- 管理端确认文档状态为完成、可见性为公开、活动索引版本存在。
- 检查 `/ready` 中 Chroma 与 SQLite 状态。
- 查看 SSE 的 retrieval 耗时、候选数量与最高分，不要仅靠降低阈值掩盖错误索引。
- 重新索引后仍异常时，先备份，再核对 Embedding 模型和维度是否与已有集合一致。

## TTS 没有自动朗读

- 管理端确认当前角色已启用音色和自动朗读。
- 浏览器通常要求用户先与页面交互，之后才允许自动播放音频。
- 检查 `/api/v1/tts/stream` 是否成功，以及 CosyVoice 模型和音色 ID 是否可用。
- 停止回答会同时取消 TTS，这是预期行为。

## 管理端无法登录

- 生产环境必须配置 `ADMIN_PASSWORD` 和至少 32 字节的 `AUTH_SECRET_KEY`。
- 令牌只保存在当前标签页；关闭标签页、过期或后端更换密钥后需要重新登录。
- 服务器时间偏差过大可能导致令牌立即失效，应启用系统时间同步。
