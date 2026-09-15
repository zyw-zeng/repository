# v0.5 发布检查清单

## 自动检查

普通发布检查不会调用云端模型：

```powershell
.\.venv\Scripts\python.exe scripts\release_check.py
```

报告保存在 `output/release/`。只有报告状态为 `passed` 才能发布。

正式候选版本可在后端已启动、标准文档已导入后执行完整检查：

```powershell
.\.venv\Scripts\python.exe evaluations\prepare_standard_docs.py
.\.venv\Scripts\python.exe scripts\release_check.py --with-evaluation
```

`--with-evaluation` 会产生真实 Embedding 和对话模型费用。Playwright 环境配置完成后可再添加
`--with-e2e`。

## 人工发布检查

- 确认 `.env` 未进入 Git，生产环境已配置强管理员密码和随机签名密钥。
- 在变更前创建备份，并在另一目录验证备份可以恢复。
- 执行 `alembic upgrade head`，确认数据库迁移成功。
- 检查 `/health` 与 `/ready`，确认 SQLite、文档目录和 Chroma 可用。
- 使用访客身份验证闲聊、知识问答、引用展开、自动朗读和停止生成。
- 使用管理员身份验证上传、公开、重新索引、删除、音色配置和任务错误展示。
- 验证私有文档不会被访客搜索或引用。
- 验证桌面端和真实移动设备，不只依赖浏览器缩放。
- 部署后保留上一个构建产物和变更前备份，以便快速回滚。

## 发布门槛

- 检索命中率不低于 85%。
- 有答案问题正确率不低于 80%。
- 引用准确率不低于 90%。
- 无答案正确拒答率不低于 90%。
- 普通问答 P95 不高于 10 秒。
- 自动化检查没有失败项，Agent 没有无限循环，可检索半成品索引为 0。
