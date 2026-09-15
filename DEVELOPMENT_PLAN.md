# ZYW 的 AI 小助理开发计划

## 当前进度

更新时间：2026-09-14

- 阶段 0：模型方案已确定，真实对话与 Embedding 模型已经完成连通验证。
- 阶段 1：已完成并通过自动测试、代码规范检查、数据库迁移和启动验证。
- 项目规划已完成架构审查，阶段 2 已按修订后的数据一致性方案实施。
- 阶段 2：已完成文档加载、清理切分、权威正文、Chroma 索引、持久化 Worker、恢复重试、文档 API 和专项测试。
- 阶段 2 的真实百炼 Embedding 连通验证和本地确定性集成测试均已完成。
- 阶段 3：已完成查询改写、过滤检索、候选去重、上下文组装、带引用回答、事实支持复核、无依据拒答、双模式接口和独立测试。
- 阶段 3 固定标准问题集已完成真实端到端评测：引用准确率 100%（7/7），无答案正确拒答率 100%（3/3），超过 90% 验收门槛。
- 阶段 4：已完成 LangGraph 状态与节点、白名单工具、意图识别、检索评价、有限重试、步骤/时间/递归上限、失败降级、会话消息和 Agent 运行记录持久化。
- 阶段 4 真实模型验证通过：文档列表和知识问题均选择正确工具；无答案问题恰好检索 2 次后停止，没有无限循环。
- 阶段 5 方案已调整为 React/Next.js 正式访客站点；旧版 Streamlit 验证工具及其运行依赖已移除。
- 阶段 5 前置后端调整：统一品牌、管理员认证、文档公开范围、会话列表和 SSE 流式接口。
- 阶段 5.1：React/Next.js 工程、设计令牌、主题切换、FastAPI 同源代理、OpenAPI 类型生成和测试骨架已完成。
- 阶段 5.2：访客端已调整为单屏双栏结构，左侧 AI 精灵、右侧流式聊天，不再维护品牌首页、关于页和项目介绍页。
- 阶段 5.3：已完成会话创建与恢复、本地会话索引、SSE 解析与长任务心跳、LangGraph 实时步骤、正式回答 Token 流、服务端取消、引用、动态推荐追问、复制、重试和断线恢复；首页推荐按公开知识主题缓存，回答后推荐按会话和引用生成并持久化。
- 阶段 5.4：已完成独立管理端、管理员登录与令牌校验、文档全生命周期管理、公开范围控制和处理任务状态展示；管理接口继续由 FastAPI 强制鉴权。
- 前端设备架构：访客端已拆分桌面双栏工作区与移动端专用工作区，两端只共享会话和 SSE 协议；每条历史消息和实时消息均展示发送时间。
- 精灵系统：已抽离 SVG 分层角色核心、形象/服装/配饰配置和本地偏好存储；桌面端使用大舞台与换装抽屉，移动端使用可拖拽、边缘吸附并记忆位置的悬浮精灵。
- 性能优化：已启用速度模式，关闭 Qwen 默认思考，拆分路由/回答模型，移除回答后模型核验与修订调用，增加高置信度规则路由和 SSE 分阶段耗时统计。
- 阶段 5.5：已完成前端类型、组件、访问边界、桌面端、移动端、流式中断和异常恢复验收。
- 阶段 6 / v0.5：已完成 35 题标准集、多维指标与 JSON 报告、请求耗时观测、带哈希清单的完整备份恢复、统一发布检查及运维排错文档。
- v0.6.1：已完成求职顾问 Agent 的可靠匹配基础，包括原子要求、结构化档案、混合检索、来源质量、明确缺口和三项对外评分。
- v0.6.2：已完成会话岗位与档案版本绑定、优势/风险/缺口/投递策略工具、多工具有界循环、超时、取消、版本失效保护和聊天快捷追问。
- v0.6.3：已完成有事实约束的岗位定制自我介绍、可信项目亮点、面试问题与回答思路、能力补足计划，以及 Markdown 引用报告导出。
- 下一步：v0.6.4——建立求职 Agent 固定评测，验证材料真实性、引用准确性和评分稳定性。

## 1. 项目定位

项目名称：**ZYW 的 AI 小助理**

项目目标：从零开发一个可公开使用的个人知识库 AI Agent，帮助访客了解 ZYW、他的技术能力和项目。管理员可以导入并控制文档公开范围；访客通过自然语言提问，Agent 能够判断任务意图、调用公开知识库工具、评估检索结果、组织答案，并给出可核查的引用。

本项目不复用其他示例项目代码，所有模块都在 `E:\AI\repository` 中重新设计和实现。

## 2. 核心原则

1. **证据优先**：知识类回答必须尽量基于检索到的原文。
2. **引用可追踪**：答案能够追溯到文件、页码、章节或具体文本片段。
3. **不确定时拒答**：知识库没有依据时明确说明，不让模型猜测。
4. **先 RAG，后 Agent**：先保证入库和检索可靠，再增加自主决策能力。
5. **可观测**：记录模型调用、工具调用、耗时、异常和检索结果。
6. **可评测**：使用固定问题集持续验证正确率和引用准确性。
7. **最小权限**：第一版 Agent 只能读取和查询知识库，不能执行任意系统命令。
8. **原文是权威数据**：SQLite 与文件系统保存可核查的原文，Chroma 仅作为可重建的检索索引。
9. **业务服务隔离底层存储**：API 和 Agent 不直接操作 SQLite、Chroma 或文件系统。
10. **中文注释约定**：业务源码、测试和迁移脚本使用中文模块说明、中文文档字符串，并为关键设计原因和非直观逻辑添加中文注释。

## 3. MVP 功能范围

### 3.1 文档管理

- 上传 PDF、Markdown、TXT、DOCX 文件。
- 查看已导入文档及其处理状态。
- 删除文档及对应的向量数据。
- 根据文件哈希识别重复文件。
- 文件发生变化后支持重新索引。
- 保存文件名、文件类型、页码、标题层级、导入时间等元数据。
- 文档处理采用任务状态，用户可以查看解析、切分和向量化进度。
- 程序重启后能够识别并恢复未完成的处理任务。

### 3.2 文档处理

- 提取不同格式文件的正文。
- 清理空白、页眉页脚等噪声。
- 优先按标题、段落和页面边界切分。
- 对过长片段进行二次切分，并保留适量重叠。
- 为每个片段生成稳定 ID 和向量。
- 在 SQLite 中保存切片正文和引用定位信息，Chroma 中的数据可以随时重建。
- 记录处理失败原因，允许重新处理。
- 任一步骤失败时清理残缺索引，避免 SQLite、原始文件和 Chroma 状态不一致。

### 3.3 知识问答

- 支持单轮和多轮提问。
- 根据聊天上下文将追问改写为独立查询。
- 从知识库召回相关片段。
- 过滤明显无关的检索结果。
- 根据证据生成回答。
- 展示引用文件、页码或章节以及原文片段。
- 资料不足时返回明确的依据不足提示。

### 3.4 Agent 能力

第一版提供以下受控工具：

- `search_knowledge`：搜索知识库。
- `list_documents`：列出已导入文档。
- `get_document_info`：查看指定文档的信息。
- `read_document_chunks`：读取指定文档的相关片段。
- `summarize_document`：基于文档内容生成摘要。

Agent 可以自主决定是否调用工具、调用哪个工具以及是否重新检索，但需要限制最多循环次数和单次请求的工具调用次数。

Agent 工具只能调用服务层接口，不允许直接执行 SQL、直接连接 Chroma 或访问任意文件路径。

### 3.5 会话管理

- 创建和恢复会话。
- 持久化用户消息、模型回答和引用。
- 保存 Agent 执行状态与工具调用记录。
- 第一版仅实现会话记忆，不自动把聊天内容写入长期知识库。

## 4. 暂不纳入 MVP

- 多 Agent 协作。
- 自动联网搜索。
- 自动执行系统命令。
- 自动修改或删除用户原始文件。
- 知识图谱。
- OCR 和复杂表格理解。
- 多用户组织权限。
- 语音交互。
- 模型微调。

这些能力在 MVP 评测达标后按需求增加。

## 5. 推荐技术架构

### 5.1 后端

- Python 3.12 或 3.13
- FastAPI：HTTP API 和流式响应
- Pydantic Settings：配置管理
- LangGraph：Agent 状态机和工具流程
- LangChain Core：模型、消息、工具和文档接口
- SQLAlchemy：业务数据访问
- Alembic：数据库迁移
- SQLite：本地 MVP 数据库
- Chroma：本地向量数据库

文档处理在独立 Worker 边界中执行。MVP 可以使用应用内单进程 Worker，但任务状态必须持久化，不依赖不可恢复的临时后台任务。

### 5.2 模型层

通过统一接口隔离模型供应商：

- 对话模型：支持工具调用和流式输出。
- Embedding 模型：用于文档与查询向量化。
- 可选重排模型：第二阶段用于改善检索排序。

模型名称、接口地址、密钥、超时和重试次数全部通过环境变量配置，不写死在业务代码中。

### 5.3 前端

正式前端使用 React 技术栈：

- Next.js App Router + React + TypeScript：页面、路由、SEO 和服务端渲染。
- Tailwind CSS：建立统一视觉设计系统。
- shadcn/ui：提供可完全定制的无障碍基础组件。
- Motion for React：页面切换、消息出现、布局和微交互动效。
- Lucide React：统一图标风格。
- TanStack Query：接口缓存、文档任务轮询和服务端状态同步。
- React Hook Form + Zod：登录、上传和管理表单校验。
- Axios：普通 FastAPI 请求；Fetch + ReadableStream：消费 SSE 流式回答。
- react-markdown + rehype-sanitize：安全展示 AI Markdown 回答。
- Vitest + React Testing Library + Playwright：单元、组件和端到端测试。

访客端只保留一个入口页面：桌面端左侧展示会响应聊天状态的 AI 精灵，右侧直接提供知识库聊天；移动端按“精灵在上、聊天在下”自然排列。项目与 ZYW 的介绍通过推荐问题和知识库回答呈现，不再维护多个访客路由。管理端通过独立路由提供登录、文档管理和任务详情。React 功能验收完成后，旧版 Streamlit 验证工具已退出项目。

## 6. 系统架构

```text
用户界面
   │
   ▼
FastAPI
   ├── 文档管理服务 ──► 处理任务 ──► 文档 Worker
   │                                  ├──► 文件存储
   │                                  ├──► 文档解析与切分 ──► SQLite
   │                                  └──► Embedding ──► Chroma
   │
   └── 对话服务 ──► LangGraph Agent
                         ├── 意图判断
                         ├── 查询改写
                         ├── 知识库工具
                         ├── 结果质量判断
                         ├── 答案生成
                         └── 引用校验

SQLite 保存文档记录、权威切片正文、处理任务、会话、消息和运行日志。Chroma 只保存用于召回的向量、必要文本副本和检索元数据，可以根据 SQLite 中的切片重新生成。
```

## 7. Agent 工作流

```text
接收问题
  ↓
识别意图
  ├── 明确闲聊 ──────────────► 直接回答并标记“未查询知识库”
  ├── 文档管理请求 ──────────► 调用文档工具
  └── 知识问题
          ↓
      查询改写
          ↓
      检索知识库
          ↓
      相关性判断
       ├── 充分 ──────────────► 生成带引用答案
       ├── 不充分且可重试 ───► 改写后再次检索
       └── 无可靠依据 ────────► 拒答或提示补充资料
          ↓
      引用与事实一致性检查
          ↓
      返回最终结果
```

如果无法可靠区分闲聊与知识问题，默认检索知识库。知识问答模式不得绕过检索；没有有效证据时必须拒答或提示用户补充资料。

建议的 Agent 状态字段：

```text
request_id
conversation_id
messages
user_question
intent
rewritten_query
retrieved_documents
retrieval_attempts
tool_calls
draft_answer
citations
confidence
errors
```

最终响应至少包含 `answer`、`answer_mode`、`grounded`、`citations` 和 `request_id`。其中 `confidence` 只作为内部辅助信号，除非经过校准，否则不向用户展示为精确概率。

## 8. 项目目录规划

```text
E:\AI\repository
├── app/
│   ├── main.py
│   ├── api/
│   │   ├── dependencies.py
│   │   └── routes/
│   │       ├── chat.py
│   │       ├── diagnostics.py
│   │       ├── documents.py
│   │       ├── jobs.py
│   │       └── health.py
│   ├── agent/
│   │   ├── graph.py
│   │   ├── nodes.py
│   │   ├── state.py
│   │   ├── tools.py
│   │   └── prompts.py
│   ├── knowledge/
│   │   ├── loaders/
│   │   │   ├── pdf.py
│   │   │   ├── markdown.py
│   │   │   ├── text.py
│   │   │   └── docx.py
│   │   ├── cleaner.py
│   │   ├── splitter.py
│   │   ├── indexer.py
│   │   └── retriever.py
│   ├── llm/
│   │   ├── protocols.py
│   │   ├── factory.py
│   │   ├── chat.py
│   │   └── embeddings.py
│   ├── services/
│   │   ├── chat_service.py
│   │   ├── document_service.py
│   │   └── ingestion_service.py
│   ├── storage/
│   │   ├── database.py
│   │   ├── models.py
│   │   └── repositories/
│   │       ├── documents.py
│   │       ├── conversations.py
│   │       └── agent_runs.py
│   ├── workers/
│   │   └── ingestion.py
│   ├── schemas/
│   └── core/
│       ├── config.py
│       ├── logging.py
│       ├── middleware.py
│       └── exceptions.py
├── frontend/
│   ├── package.json
│   ├── next.config.ts
│   ├── tsconfig.json
│   ├── components.json
│   ├── public/
│   │   ├── logo.svg
│   │   └── images/
│   └── src/
│       ├── app/
│       │   ├── layout.tsx
│       │   ├── page.tsx
│       │   └── admin/
│       │       ├── login/page.tsx
│       │       ├── documents/page.tsx
│       │       └── jobs/[id]/page.tsx
│       ├── components/
│       │   ├── ui/
│       │   ├── assistant/
│       │   │   ├── ai-spirit.tsx
│       │   │   ├── assistant-workspace.tsx
│       │   │   └── chat-panel.tsx
│       │   ├── brand/
│       │   ├── theme/
│       │   ├── citations/
│       │   ├── agent/
│       │   └── documents/
│       ├── features/
│       │   ├── authentication/
│       │   ├── chat/
│       │   ├── conversations/
│       │   └── documents/
│       ├── hooks/
│       │   ├── use-chat-stream.ts
│       │   └── use-job-polling.ts
│       ├── lib/
│       │   ├── api-client.ts
│       │   ├── stream-client.ts
│       │   └── utils.ts
│       ├── stores/
│       │   └── chat-store.ts
│       ├── types/
│       │   └── api.ts
│       └── styles/
│           └── globals.css
├── data/
│   ├── documents/
│   ├── chroma/
│   └── app.db
├── migrations/
├── evaluations/
│   ├── datasets/
│   └── evaluate.py
├── tests/
│   ├── unit/
│   └── integration/
├── scripts/
├── .env.example
├── .gitignore
├── pyproject.toml
├── README.md
└── DEVELOPMENT_PLAN.md
```

## 9. API 初步设计

### 文档接口

- `POST /api/v1/documents`：管理员上传文档，默认设为私有，并返回 `202 Accepted` 和 `job_id`。
- `GET /api/v1/documents`：管理员获取全部文档列表。
- `GET /api/v1/documents/{document_id}`：管理员获取文档详情。
- `PATCH /api/v1/documents/{document_id}/visibility`：管理员设置 `public` 或 `private`。
- `POST /api/v1/documents/{document_id}/reindex`：管理员创建重新索引任务并返回 `job_id`。
- `DELETE /api/v1/documents/{document_id}`：管理员创建删除任务并返回 `job_id`。
- `GET /api/v1/ingestion-jobs/{job_id}`：管理员获取文档处理进度与失败原因。

### 对话接口

- `POST /api/v1/conversations`：创建会话。
- `GET /api/v1/conversations`：管理员分页查看全局会话摘要。
- `GET /api/v1/conversations/{conversation_id}`：读取会话。
- `DELETE /api/v1/conversations/{conversation_id}`：管理员删除会话及历史消息。
- `POST /api/v1/conversations/{conversation_id}/messages`：发送消息。
- `POST /api/v1/conversations/{conversation_id}/messages/stream`：以 SSE 事件返回 Agent 步骤、经过验证的回答片段和引用。

### 认证接口

- `POST /api/v1/auth/login`：使用管理员密码换取短期 Bearer 令牌。
- `GET /api/v1/auth/me`：验证管理员登录状态。

### 系统接口

- `GET /health`：仅检查应用进程是否存活，不访问外部模型。
- `GET /ready`：检查数据库、文件目录和向量库是否可用。
- `GET /diagnostics/models`：由管理员按需检查模型连通性，避免健康检查持续产生费用。

## 10. 数据设计

### documents

- `id`
- `filename`
- `file_hash`
- `file_type`
- `storage_path`
- `status`
- `size_bytes`
- `chunk_count`
- `active_index_version`
- `visibility`：`public` 或 `private`，默认 `private`
- `error_message`
- `created_at`
- `updated_at`

### document_chunks

- `id`
- `document_id`
- `index_version`
- `chunk_index`
- `page_number`
- `heading`
- `content`
- `content_hash`
- `token_count`
- `start_offset`
- `end_offset`
- `metadata_json`
- `vector_id`
- `created_at`

切片正文以 SQLite 中的数据为权威版本。Chroma 中保存检索所需副本，但不得成为引用展示和索引重建的唯一数据源。

### ingestion_jobs

- `id`
- `document_id`
- `operation`：`index`、`reindex` 或 `delete`
- `target_index_version`
- `status`：`pending`、`parsing`、`chunking`、`embedding`、`ready`、`failed` 或 `deleting`
- `progress`
- `attempts`
- `error_message`
- `started_at`
- `finished_at`
- `created_at`

### conversations

- `id`
- `title`
- `created_at`
- `updated_at`

### messages

- `id`
- `conversation_id`
- `role`
- `content`
- `citations_json`
- `created_at`

### agent_runs

- `id`
- `conversation_id`
- `request_id`
- `status`
- `tool_calls_json`
- `duration_ms`
- `error_message`
- `created_at`

## 10.1 数据一致性与失败恢复

一次文档操作会同时涉及原始文件、SQLite 和 Chroma，三者不能共享同一个数据库事务，因此必须使用明确的状态机和补偿操作。

### 上传与索引

1. 将上传内容写入临时文件并计算 SHA-256。
2. 校验格式、大小和重复文件。
3. 将文件移动到受控存储目录。
4. 写入 `documents` 和 `ingestion_jobs`，初始状态为 `pending`。
5. Worker 依次完成解析、清理、切分、保存切片和向量化。
6. 所有向量写入成功后，将文档和任务标记为 `ready`。
7. 任一步骤失败时，任务标记为 `failed`，并删除本次写入的残缺向量；原始文件和错误记录保留以便重试或排查。

### 删除

1. 将文档标记为 `deleting`，阻止新的检索请求使用它。
2. 删除对应 Chroma 向量。
3. 删除受控目录中的原始文件。
4. 删除 SQLite 中的切片和文档记录。
5. 失败时保留 `deleting` 状态，由恢复任务继续处理，避免只删除一部分数据。

### 重新索引

1. 使用新的索引版本生成切片和向量。
2. 新版本全部成功后才切换文档的 `active_index_version`。
3. 检索只使用状态为 `ready` 且版本等于 `active_index_version` 的切片。
4. 切换成功后再清理旧向量和旧切片。
5. 新版本失败时继续使用旧版本，不影响已有查询。

应用启动时扫描长时间停留在中间状态的任务，并根据操作类型恢复、重试或标记失败。所有删除和重试操作必须具有幂等性。

## 11. 分阶段开发安排

### 阶段 0：需求冻结与技术验证（1 天）

- 确定模型服务和 Embedding 服务。
- 用一份 PDF 验证解析、向量化和模型调用。
- 确定 MVP 支持的文件大小与语言范围。
- 建立首批 10 个测试问题。

完成标准：模型和文档处理链路均可调用，关键技术不存在阻塞。

### 阶段 1：工程基础（1～2 天）

- 创建正式目录结构。
- 配置依赖、环境变量和启动命令。
- 配置日志、统一异常和请求 ID。
- 建立数据库连接与迁移。
- 添加健康检查和基础自动化测试。

完成标准：新环境按照 README 可以一次启动，测试可以执行。

### 阶段 2：文档入库（3～5 天）

- 将模型适配目录统一为 `app/llm/`，并建立服务层与存储层的单向依赖边界。
- 创建 `document_chunks`、`ingestion_jobs` 和索引版本相关数据库迁移。
- 实现四种文档加载器。
- 实现文本清理与结构化切分。
- 实现哈希去重和稳定片段 ID。
- 在 SQLite 中保存权威切片正文、定位信息和索引版本。
- 实现向量化与 Chroma 写入。
- 实现持久化处理任务和应用内 Worker。
- 实现处理中断恢复、有限重试和残缺向量清理。
- 实现上传、列表、详情、删除和重新索引接口。
- 按数据一致性规则实现上传、删除和双版本重新索引。
- 测试中文、英文、空文件、损坏文件和重复文件。

完成标准：文档可以可靠地新增、更新、删除和查询，不产生重复数据；在任意处理步骤失败或程序重启后，不会留下可被检索到的半成品索引。

### 阶段 3：可靠 RAG（3～5 天）

- 实现查询改写。
- 实现向量检索和 metadata 过滤。
- 实现候选片段去重和上下文组装。
- 实现带引用回答。
- 实现无依据拒答。
- 区分 `knowledge_base` 和 `casual` 回答模式，知识问答不得绕过检索。
- 引用正文从权威切片记录读取，并验证引用片段确实属于对应文档版本。
- 建立检索与回答的独立测试。

完成标准：标准问题集上的引用准确率达到 90%，无答案问题不会强行作答。

### 阶段 4：Agent 工作流（3～5 天）

- 定义 LangGraph 状态和节点。
- 将知识库能力封装为工具。
- Agent 工具只依赖服务层接口，不直接访问数据库、向量库或文件系统。
- 实现意图识别、工具选择、检索评价和重试。
- 增加最大循环次数、超时和降级处理。
- 持久化会话及 Agent 运行记录。

完成标准：Agent 能按问题选择正确工具，失败时可控退出，不发生无限循环。

### 阶段 5：React 用户界面（5～6 天）

#### 5.1 工程与设计系统

- 创建 Next.js App Router + TypeScript 工程。
- 配置 Tailwind CSS、shadcn/ui、Motion、代码规范和测试工具。
- 定义“ZYW 的 AI 小助理”颜色、字体、间距、圆角、主题和动效规范。
- 配置 FastAPI 同源代理，并根据 `/openapi.json` 生成 TypeScript 类型。
- React 工程验收后删除旧版 Streamlit 验证工具和运行依赖。

#### 5.2 单屏 AI 助理界面

- 移除品牌首页、关于 ZYW、项目介绍和独立聊天页，只保留根路由。
- 桌面端使用左右结构：左侧 AI 精灵，右侧聊天；移动端使用独立全屏聊天与可拖拽悬浮精灵。
- AI 精灵根据空闲、检索、回答和错误状态改变提示语与动效。
- 空状态推荐根据公开文档主题和索引版本动态生成并缓存，不在前端写死。
- 支持浅色、深色和 `prefers-reduced-motion` 无障碍设置。

#### 5.3 流式聊天完善

状态：已完成。

- 实现会话创建、恢复和本地会话索引。
- 使用 Fetch + ReadableStream 消费 SSE 事件。
- 后端长时间执行 Agent 时定期发送心跳，异常通过结构化 `error` 事件结束，避免代理空闲超时截断连接。
- LangGraph 节点完成时立即推送步骤，模型正式回答通过 `answer_delta` 实时传输。
- `answer_final` 只校正传输拼接结果，不触发额外模型核验或撤回流程。
- 展示 Agent 执行进度、经过验证的最终回答、引用来源和推荐追问。
- 回答完成后由独立小模型结合最近会话、回答模式和引用生成推荐追问，通过 `followup_suggestions` SSE 事件发送并保存到助手消息。
- 停止生成时同时调用服务端取消接口并关闭浏览器流；支持复制、重试、空状态、断线和错误恢复。
- 接入 CosyVoice，将 `answer_delta` 按语义边界分句后立即进入音频播放队列，实现回答生成期间自动朗读；停止回答时同步取消语音。
- 将朗读状态映射为精灵的 `speaking` 动作，同时保留消息级暂停、继续、停止和重播控制。
- 保持单屏双栏视觉结构，会话历史与引用详情按需使用抽屉或折叠区域，不新增访客页面。

#### 5.4 管理端

状态：已完成。

- 实现管理员登录和令牌状态验证。
- 实现文档上传、列表、详情、公开范围、删除和重新索引。
- 展示任务进度、尝试次数、失败原因和索引版本。
- 所有管理能力必须由 FastAPI 鉴权，不能只在前端隐藏入口。
- 管理端固定使用 `/admin` 独立路由，不改变访客端的单屏双栏结构。
- 管理员令牌仅保存在当前浏览器标签页的 `sessionStorage` 中，并在进入管理端时调用 `/auth/me` 校验有效性与过期状态。
- 文档写操作和任务状态查询均通过 FastAPI 的 Bearer 令牌鉴权；遇到 `401` 时立即清理本地令牌并返回登录页。
- 增加星云、比特和沫沫的独立音色配置，管理员可设置 CosyVoice 模型、音色 ID、启用状态和自动朗读策略。

#### 5.5 测试与验收

- 增加前端类型检查、组件测试和 Playwright 端到端测试。
- 验证访客不能访问私有文档和管理接口。
- 验证上传、公开、提问、引用、删除和重新索引完整流程。
- 验证桌面端、移动端、流式中断和减少动画模式。
- Streamlit 运行依赖已在 React 功能对等测试通过后移除。

完成标准：非开发人员打开根页面即可通过 AI 精灵聊天了解 ZYW 和项目、核查引用；管理员可以安全管理文档，私有资料不会进入访客检索，页面在桌面与移动设备均可正常使用。

### 阶段 6：评测与发布（3～5 天）

状态：已完成（v0.5.0）。

- 扩充到 30～50 个标准问题。
- 统计检索命中率、回答正确率、引用准确率和延迟。
- 添加异常恢复、数据备份和恢复说明。
- 完成安装、配置、使用和排错文档。
- 固定第一个可发布版本。

完成标准：所有 MVP 验收项通过，并能在一台新机器上按文档完成部署。

## 12. 测试与评测计划

### 单元测试

- 文件哈希和去重。
- 文本清理与切分。
- 元数据生成。
- 引用格式化。
- Agent 路由和最大重试次数。

### 集成测试

- 上传文件到完成索引。
- 提问到返回引用答案。
- 删除文件后不能再检索到对应内容。
- 在解析、切分和向量写入阶段分别模拟失败，确认残缺数据能够恢复或清理。
- 在重新索引失败时确认旧索引仍然可用。
- 重复执行删除和重试操作不会产生异常状态。
- 服务重启后数据仍然存在。
- 模型或向量服务失败时返回可理解的错误。

### 评测数据类型

- 可由单个片段直接回答的问题。
- 需要综合多个片段的问题。
- 多轮追问。
- 知识库中没有答案的问题。
- 包含相似词但语义无关的问题。
- 来源互相冲突的问题。

### MVP 指标

- 检索命中率：标准答案所在片段出现在 Top K 结果中的问题占比，目标不低于 85%。
- 引用准确率：引用确实支持对应答案陈述的引用数量占全部引用数量的比例，目标不低于 90%。
- 有答案问题正确率：人工或固定评分规则判定为完整正确的问题占比，目标不低于 80%。
- 无答案问题正确拒答率：知识库无依据且系统没有编造答案的问题占比，目标不低于 90%。
- 文档重复导入率：0%。
- 可检索半成品索引：0 个。
- Agent 无限循环：0 次。
- 普通问答 P95 响应时间：目标低于 10 秒，具体按模型服务调整。

## 13. 安全与可靠性

- 只允许解析白名单文件格式。
- 限制上传文件大小、数量和文件名长度。
- 不信任文档中的指令，防止提示注入影响 Agent。
- 工具参数使用结构化模型校验。
- 不在日志中记录 API Key 和完整敏感文档。
- 删除文档时同时清理业务记录和向量记录。
- 对模型调用设置超时、有限重试和错误降级。
- 所有 Agent 循环必须有明确次数上限。

## 14. 版本路线

### v0.1：知识库基础

完成文档导入、索引、检索和基础 API。

### v0.2：可靠问答

完成带引用 RAG、拒答机制和评测集。

### v0.3：AI Agent

完成工具调用、状态机、多轮会话和运行记录。

### v0.4：可用产品

完成用户界面、流式输出、部署与备份。

### v0.5：稳定与评测

完成 35 题标准集、多维质量和延迟报告、数据备份恢复、统一发布验收与运维文档。

### v0.6：求职顾问 Agent

将证据化 JD 匹配升级为可持续对话的求职顾问，逐步增加岗位上下文、优势与缺口分析、定制自我介绍、面试准备、报告导出和固定 JD 评测。

### v1.0：稳定版本

达到验收指标，补齐测试、安全、文档和发布流程。

## 15. 开发执行顺序

严格按照以下顺序推进：

```text
工程骨架
→ 数据模型
→ 文档解析
→ 文档切分
→ 向量索引
→ 检索测试
→ 带引用 RAG
→ Agent 工具
→ LangGraph 工作流
→ 会话持久化
→ 用户界面
→ 自动评测
→ 发布
```

在“带引用 RAG”通过评测前，不增加多 Agent、联网搜索等高级功能。
