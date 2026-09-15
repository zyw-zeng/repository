# ZYW 的 AI 小助理

一个帮助访客了解 ZYW 及其项目、引用优先且可核查的个人知识库 AI Agent。

当前版本：`v0.6.3` 求职材料生成。阶段 1～6 已完成，并在可靠 RAG、LangGraph Agent、React 用户界面和稳定评测基础上，支持岗位上下文连续咨询、证据约束的自我介绍、项目亮点、面试准备、能力补足计划和带引用报告导出。

## 环境要求

- Python 3.12 或 3.13
- Node.js 20.9 或更高版本，以及 pnpm
- 阿里云百炼 API Key（仅模型连通测试和后续问答需要）

## 本地启动

```powershell
cd E:\AI\repository
Copy-Item .env.example .env
# 编辑 .env，填写 DASHSCOPE_API_KEY；聊天模型与 CosyVoice 共用该密钥
# 同时填写 ADMIN_PASSWORD，并为 AUTH_SECRET_KEY 生成至少 32 字节随机值

.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

启动 React/Next.js 前端：

```powershell
cd E:\AI\repository
cd frontend
pnpm install
Copy-Item .env.example .env.local
pnpm dev
```

- React 界面：`http://127.0.0.1:3000`
- Swagger 接口文档：`http://127.0.0.1:8000/docs`
- 后端根地址：`http://127.0.0.1:8000`（自动跳转至 Swagger）

更新 FastAPI 后，可以在前端目录重新生成接口类型：

```powershell
pnpm api:types
```

项目只维护 Swagger 作为后端接口文档，接口参数、响应模型、错误状态和中文说明均以
`/docs` 中展示的 OpenAPI 定义为准。

## 文档管理接口

文档管理、处理任务和诊断接口需要先登录并携带 Bearer 令牌。新上传和历史迁移后的文档默认是 `private`，只有管理员明确设为 `public` 后才允许访客检索。

- `POST /api/v1/documents`：上传 PDF、Markdown、TXT 或 DOCX，返回文档和任务。
- `GET /api/v1/documents`：分页查看文档。
- `GET /api/v1/documents/{document_id}`：查看文档状态。
- `PATCH /api/v1/documents/{document_id}/visibility`：设置公开或私有。
- `POST /api/v1/documents/{document_id}/reindex`：创建下一版本索引。
- `DELETE /api/v1/documents/{document_id}`：创建可恢复的删除任务。
- `GET /api/v1/ingestion-jobs/{job_id}`：查看任务进度和失败原因。

上传后会在后台执行解析、切分和向量化。只有新版本全部写入成功后，系统才会切换活动索引；失败时旧版本仍可继续使用。

## 可靠 RAG 接口

`POST /api/v1/chat/query` 支持两种显式模式：

- `knowledge_base`：默认模式，强制执行查询改写、检索、回答和引用复核；没有可靠依据时拒答。
- `casual`：仅用于明确的闲聊，不查询知识库，也不会返回知识库引用。

请求示例：

```json
{
  "question": "这个项目如何保证引用可靠？",
  "mode": "knowledge_base",
  "history": [],
  "filters": {
    "document_ids": [],
    "filenames": []
  }
}
```

最终引用正文始终从 SQLite 当前活动版本读取。模型引用不存在的编号、活动版本已经变化，或引用正文不能支持答案时，接口都会返回 `grounded=false`。

## 检查项目

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe scripts\verify_models.py
```

最后一个命令会产生真实模型调用费用；未配置 API Key 时会安全退出。

发布前可以执行统一验收；它会依次检查 Python、数据库迁移分支、前端规范、类型、组件测试和生产构建，并在 `output/release/` 保存 JSON 报告：

```powershell
.\.venv\Scripts\python.exe scripts\release_check.py
```

导入与标准问题集对应的项目文档后，可以运行真实端到端评测：

```powershell
.\.venv\Scripts\python.exe evaluations\prepare_standard_docs.py
.\.venv\Scripts\python.exe evaluations\evaluate.py
```

标准集包含 35 题，覆盖直接问法、改写问法、多片段综合和无答案问题。报告保存到 `evaluations/reports/`，统计检索命中率、回答正确率、来源准确率、引用准确率、拒答率、错误率以及 P50/P95/最大延迟。该命令会调用真实 Embedding 和对话模型并产生费用。

阶段 3 验收结果（2026-09-12）：10 道真实模型题目中，7 道可回答问题全部返回受权威正文支持的引用，3 道无答案问题全部拒答；引用准确率 100%，无答案正确拒答率 100%。

## LangGraph Agent 接口

- `POST /api/v1/conversations`：创建持久化会话。
- `GET /api/v1/conversations`：管理员分页读取全部会话摘要。
- `GET /api/v1/conversations/{conversation_id}`：读取会话和最近消息。
- `DELETE /api/v1/conversations/{conversation_id}`：管理员删除会话。
- `POST /api/v1/conversations/{conversation_id}/messages`：运行 Agent 并保存结果。
- `POST /api/v1/conversations/{conversation_id}/messages/stream`：使用 SSE 实时返回 LangGraph 步骤、正式回答 Token、引用、动态推荐问题和完成状态。
- `POST /api/v1/conversations/{conversation_id}/runs/{request_id}/cancel`：通知服务端停止对应模型流和后续 Agent 节点。
- `GET /api/v1/suggestions`：按当前公开文档主题生成并缓存首页空状态推荐问题。

Agent 只会从以下白名单能力中选择：闲聊、搜索公开知识库、列出公开文档、读取公开文档信息和总结指定公开文档。知识检索没有候选时允许改写查询再次检索；默认最多检索 2 次、执行 8 个节点，并受模型请求超时、总截止时间和 LangGraph 递归上限共同约束。模型输出通过 `answer_delta` 直接作为正式回答流式发送，不再经过“草稿、模型核验、确认或撤回”流程；引用来源仍从 SQLite 当前活动版本读取。

速度模式默认启用：`MODEL_ENABLE_THINKING=false` 关闭默认思考，`CHAT_MODEL` 负责回答，`ROUTER_MODEL` 负责含糊意图和查询改写。明确问题优先通过本地规则路由，避免额外模型调用。SSE 会实时发送 `timing` 事件，完成事件的 `timings` 字段包含路由、改写、检索、上下文、回答和总耗时。

推荐问题由独立的 `SUGGESTION_MODEL` 小模型生成，不进入 Agent 主工具循环。首页推荐按公开文档及活动索引版本缓存；回答后的推荐结合最近会话、回答模式和引用主题生成，通过 `followup_suggestions` 事件发送，并保存到助手消息的 `suggestions_json`，刷新会话后无需再次生成。推荐服务超时或失败只使用规则候选，不影响主回答。

当前公开知识检索阈值默认为 `RAG_MIN_SCORE=0.35`。完整独立问题即使处在旧会话中也会直接检索；只有包含“它、其中、上述、继续、展开”等上下文指代的追问才调用查询改写模型。

## v0.6 求职顾问 Agent

- `POST /api/v1/jd-analyses/stream`：在当前聊天会话中流式执行 JD 解析、逐项证据检索、核验和评分。
- `GET /api/v1/jd-analyses/{analysis_id}`：恢复已经持久化的岗位分析报告。
- `POST /api/v1/jd-analyses/runs/{request_id}/cancel`：取消仍在执行的岗位分析。

JD 会先拆成可独立评价的原子要求；结构化个人档案、SQLite 关键词和 Chroma 向量结果经过混合排序后，再由受约束模型判断。最终分数由代码确定性计算，分别展示岗位匹配度、证据完整度和求职可行度。没有资料只标记为“证据不足”，只有可信资料明确证明未达到要求时才标记为“明确未满足”。详细设计与后续路线见 [v0.6 求职顾问 Agent](docs/V06_CAREER_AGENT.md)。

完成一次绑定会话的 JD 分析后，用户可以直接继续询问岗位优势、应聘风险、能力缺口和投递策略。请求会进入独立 Career Agent，只能调用四个只读顾问工具；该工作流具有 6 步上限、20 秒总超时并复用聊天取消接口。会话保存 JD 分析 ID 和个人档案版本，档案更新后旧报告会被标记为过期并要求重新分析。

## CosyVoice 朗读接口

- `POST /api/v1/tts/stream`：按当前角色音色合成并流式返回 MP3，使用 `X-Request-ID` 标识任务。
- `POST /api/v1/tts/runs/{request_id}/cancel`：取消正在执行的云端合成。
- `GET /api/v1/tts/profiles/{character_id}`：访客端读取角色是否启用自动朗读。
- `GET /api/v1/tts/profiles`：管理员读取星云、比特和沫沫的音色配置。
- `PUT /api/v1/tts/profiles/{character_id}`：管理员更新模型、音色和自动朗读策略。

前端收到 `answer_delta` 后会按中文标点和最大长度分句，完整句子立即进入 CosyVoice 音频队列，无需等待整段回答完成或点击朗读。管理员可以在 `/admin` 分别配置三个角色的音色，并关闭某个角色的语音或自动朗读。朗读时精灵进入 `speaking` 状态；停止回答会同时清空未播放句子、中断浏览器音频流和取消服务端合成。相同模型、音色、语速和正文会复用 `data/tts-cache` 缓存。

## 管理端认证

- `POST /api/v1/auth/login`：使用 `.env` 中的 `ADMIN_PASSWORD` 登录。
- `GET /api/v1/auth/me`：验证 Bearer 令牌是否有效。
- React 管理端地址：`http://127.0.0.1:3000/admin`。
- 登录令牌仅保存在当前标签页会话中；退出、过期或接口返回 `401` 后会自动清理。
- 文档上传、详情、公开范围、删除、重新索引和任务查询均由 FastAPI 强制校验管理员令牌，不能通过直接调用接口绕过前端限制。

未配置 `ADMIN_PASSWORD` 或 `AUTH_SECRET_KEY` 时，管理接口会安全返回 `503`，不会退化成无认证访问。

## 文档

- [完整开发计划](DEVELOPMENT_PLAN.md)
- [模型方案决策](docs/MODEL_DECISION.md)
- [数据备份与恢复](docs/BACKUP_AND_RESTORE.md)
- [新机器与宝塔部署](docs/DEPLOYMENT.md)
- [v0.5 发布检查清单](docs/RELEASE_CHECKLIST.md)
- [常见问题排查](docs/TROUBLESHOOTING.md)
- [v0.6 求职顾问 Agent](docs/V06_CAREER_AGENT.md)

## 代码注释约定

- 业务源码、测试和迁移脚本统一使用中文模块说明与中文文档字符串。
- 对配置边界、状态变化、异常处理和不直观逻辑添加中文行内注释。
- 注释说明设计原因和约束，不逐行复述代码表面含义。
- 第三方库名称、协议名、字段名和必要技术术语保留标准英文写法。
- `.venv`、`*.egg-info`、`__pycache__` 等自动生成目录不手工修改。
