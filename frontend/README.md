# ZYW 的 AI 小助理前端

基于 Next.js App Router、React、TypeScript、Tailwind CSS、shadcn/ui 和 Motion 构建的正式访客界面。访客端不设置多个介绍页面，只保留一个“左侧 AI 精灵、右侧知识库聊天”的入口；移动设备自动改为上下结构。

## 本地运行

先启动项目根目录的 FastAPI，再启动前端：

```powershell
cd E:\AI\repository\frontend
Copy-Item .env.example .env.local
pnpm install
pnpm dev
```

浏览器访问 `http://127.0.0.1:3000`；管理员访问 `http://127.0.0.1:3000/admin`。`/api/backend/*` 会由 Next.js 同源转发到 FastAPI 的 `/api/v1/*`。

## 接口类型

FastAPI 运行后执行：

```powershell
pnpm api:types
```

脚本根据 `/openapi.json` 更新 `src/types/api.generated.ts`，该文件不手工编辑。

## 质量检查

```powershell
pnpm lint
pnpm typecheck
pnpm test
pnpm build
pnpm test:e2e
```

端到端测试默认复用本机 Chrome，覆盖桌面和移动视口。

## 设计系统

- 品牌色：青色、靛青和紫色渐变。
- 字体：Geist 搭配系统中文字体回退。
- 圆角：以 `0.875rem` 为基础比例统一生成。
- 间距：双栏外壳占满视口，聊天正文限制可读行宽并随大屏逐级放宽。
- 主题：支持浅色、深色和跟随系统。
- 动效：使用 Motion，系统开启“减少动态效果”时自动降级。
- 安全：AI Markdown 使用 `rehype-sanitize` 清理后展示。

## 单屏界面结构

- `src/components/assistant/ai-spirit.tsx`：AI 精灵和空闲、检索、回答、朗读、错误状态反馈。
- `src/components/assistant/chat-panel.tsx`：会话恢复、模型 Token 流、Agent 进度、引用、动态推荐追问、复制、重试和消息朗读。
- `src/features/tts/use-speech-player.ts`：消费回答增量、低延迟分句、CosyVoice 音频队列、暂停、继续、停止、语速和服务端取消。
- `src/components/assistant/conversation-drawer.tsx`：当前浏览器的会话历史抽屉。
- `src/features/chat/conversation-storage.ts`：只保存会话 ID、标题和更新时间的本地索引，不保存完整聊天正文。
- `src/components/assistant/assistant-workspace.tsx`：按视口挂载桌面双栏或移动端全屏聊天实现。
- `/about`、`/project`、`/chat` 不再作为访客页面；ZYW 和项目介绍由知识库对话承载。

流式接口会实时接收 LangGraph 步骤和正式回答 Token，并在传输结束时使用 `answer_final` 校正拼接结果；随后接收已持久化的 `followup_suggestions` 动态追问。长时间没有业务事件时每 10 秒接收一次心跳。停止按钮会先请求 FastAPI 取消对应运行，再关闭浏览器流。若代理仍意外断开，界面会有限重试读取后端已经持久化的完整回答和推荐问题，不会自动重复执行用户问题。

## 管理端结构

- `src/app/admin/page.tsx`：独立管理端入口，不影响访客单屏页面。
- `src/components/admin/admin-login.tsx`：管理员密码登录和错误反馈。
- `src/components/admin/admin-shell.tsx`：令牌存在性与 `/auth/me` 状态验证。
- `src/components/admin/document-dashboard.tsx`：文档上传、列表、详情、公开范围、删除、重新索引与任务轮询。
- `src/features/admin/auth-storage.ts`：仅在当前标签页会话中保存令牌和本地过期时间。

所有管理请求都必须携带 FastAPI 签发的 Bearer 令牌。前端隐藏或展示管理界面不承担安全职责，真正的访问控制位于 FastAPI 文档与任务路由依赖中。

管理端的“角色声音”区域可以分别设置星云、比特和沫沫使用的 CosyVoice 模型与音色 ID，并控制是否启用自动实时朗读。保存后，下一次语音分句请求立即使用新配置。
