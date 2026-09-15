# 新机器部署指南

本文以 Linux 与宝塔面板为例。生产环境由 FastAPI 提供后端服务、Next.js 提供前端服务，Nginx
统一终止 HTTPS 并反向代理到本机端口。

## 1. 环境与代码

- Python 3.12 或 3.13。
- Node.js 20.9 以上、pnpm 10。
- Nginx、有效域名与 HTTPS 证书。
- 只允许 FastAPI 和 Next.js 监听 `127.0.0.1`，不要把 8000、3000 端口直接暴露到公网。

```bash
cd /www/wwwroot/zyw-ai-assistant
python3.12 -m venv .venv
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/python -m pip install -e ".[dev]"
cd frontend
pnpm install --frozen-lockfile
pnpm build
cd ..
```

## 2. 生产配置

从 `.env.example` 复制 `.env`，至少设置以下内容：

- `APP_ENV=production`、`APP_DEBUG=false`。
- 阿里云 `DASHSCOPE_API_KEY`。
- 强随机 `ADMIN_PASSWORD`。
- 至少 32 字节随机 `AUTH_SECRET_KEY`。
- 与现有 Chroma 集合一致的 Embedding 模型、维度和集合名。

`.env` 权限应限制为仅服务用户可读，不能提交到 Git。

## 3. 初始化数据库

```bash
./.venv/bin/python -m alembic upgrade head
./.venv/bin/python scripts/backup_data.py --output-dir backups --label initial
```

如果是服务器迁移，应先上传旧服务器备份并按[备份恢复说明](BACKUP_AND_RESTORE.md)恢复，再执行迁移。

## 4. 启动服务

宝塔 Python 项目：

- 项目路径：`/www/wwwroot/zyw-ai-assistant`
- Python 环境：项目中的 `.venv`
- 启动命令：`.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`
- 启动用户：具有 `data/`、`logs/`、`output/` 和 `backups/` 写权限的低权限用户

Next.js 可由宝塔 Node 项目或进程守护器启动：

```bash
cd /www/wwwroot/zyw-ai-assistant/frontend
pnpm start --hostname 127.0.0.1 --port 3000
```

## 5. Nginx 与 SSE

网站根路径转发到 `http://127.0.0.1:3000`。SSE 经过 Next.js 同源代理时需要：

```nginx
proxy_http_version 1.1;
proxy_buffering off;
proxy_cache off;
proxy_read_timeout 300s;
proxy_send_timeout 300s;
```

不要在 Nginx 中再次删除或重复添加 `/api/backend` 前缀，路由转换由 Next.js 配置负责。

## 6. 上线验收与回滚

先执行：

```bash
./.venv/bin/python scripts/release_check.py
```

再按照[发布检查清单](RELEASE_CHECKLIST.md)完成真实访问验证。若发布后异常，停止服务、恢复上一个
构建版本和发布前备份、执行数据库迁移，然后重新启动并检查 `/health` 与 `/ready`。
