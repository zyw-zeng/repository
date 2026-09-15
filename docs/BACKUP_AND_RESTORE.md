# 数据备份与恢复

v0.5 的备份工具会生成一个带 SHA-256 校验清单的 ZIP 快照，包含 SQLite、原始文档、Chroma
向量索引、TTS 缓存、结构化个人档案和公开简历。`.env`、API Key、管理员密码和日志不会进入备份包。

## 创建备份

Windows：

```powershell
.\.venv\Scripts\python.exe scripts\backup_data.py --output-dir backups --label manual
```

Linux / 宝塔：

```bash
./.venv/bin/python scripts/backup_data.py --output-dir backups --label manual
```

SQLite 使用在线备份 API；但为了让 SQLite、原始文档与 Chroma 处于同一个业务时间点，正式备份
仍建议安排在没有入库和重新索引任务的维护窗口，或短暂停止后端 Worker。建议每天自动备份一次，
并至少保留最近 7 个日备份、4 个周备份；备份包应加密后同步到服务器之外的私有存储位置。

## 校验备份

恢复命令默认只校验归档结构、文件大小和哈希，不会修改任何数据：

```powershell
.\.venv\Scripts\python.exe scripts\restore_data.py backups\zyw-ai-assistant-manual-时间.zip
```

看到“校验通过”后，才能把该文件用于正式恢复。

## 正式恢复

1. 停止 FastAPI、后台 Worker 和 Next.js 服务，避免恢复期间继续写入。
2. 执行带 `--apply` 的恢复命令。
3. 工具会先创建 `pre-restore` 安全备份，再完整替换当前数据。

Windows：

```powershell
.\.venv\Scripts\python.exe scripts\restore_data.py backups\目标备份.zip --apply
.\.venv\Scripts\python.exe -m alembic upgrade head
```

Linux / 宝塔：

```bash
./.venv/bin/python scripts/restore_data.py backups/目标备份.zip --apply
./.venv/bin/python -m alembic upgrade head
```

随后重新启动后端和前端，检查 `/health`、`/ready`、管理端文档列表、一次知识库问答及引用。

## 重要边界

- v0.5 仅支持 SQLite；迁移到 PostgreSQL 后需使用数据库原生备份工具。
- 恢复是完整快照替换，不会把两个知识库合并。
- 不要手工修改 ZIP 中的文件；任何修改都会使哈希校验失败。
- 快照包含个人文档和简历，不能上传到公开仓库或公共网盘。
- 服务器迁移时要单独、安全地迁移 `.env`，不要把密钥放入代码仓库或备份包。
