# 模型方案决策

## 结论

MVP 默认采用阿里云百炼的 OpenAI 兼容接口：

- Agent 对话模型：`qwen3.7-plus`
- Embedding 模型：`qwen3.7-text-embedding`
- Embedding 维度：1024
- 默认兼容接口：`https://dashscope.aliyuncs.com/compatible-mode/v1`

## 选择理由

- 对中文个人资料有良好的适配范围。
- 对话模型支持结构化工具调用，适合 LangGraph Agent。
- Embedding 模型支持长文本和多语言，可按需要选择向量维度。
- 对话与 Embedding 均可通过 OpenAI 兼容客户端接入。
- 应用通过模型工厂隔离供应商，未来更换模型时不需要修改 Agent 和知识库业务代码。

## 生产环境注意事项

- 公共兼容地址适合本地 MVP。正式部署时应改为业务空间专属域名。
- 模型名称、接口地址、密钥、超时和重试次数只能通过环境变量配置。
- 不同 Embedding 模型或向量维度不能混用；发生变更时必须重建向量索引。
- 开发与评测阶段固定模型版本后，应避免在同一评测周期中切换模型。
- API Key 不进入 Git、日志或错误响应。

## 降级与替换策略

模型不可用时，API 应返回明确的上游服务错误，不自动伪造回答。未来替换其他 OpenAI 兼容服务时，只需调整环境变量；若客户端协议不同，则新增模型适配器，不修改 Agent 节点。

## 官方依据

- [百炼 OpenAI 兼容模型调用](https://help.aliyun.com/zh/model-studio/model-calling-in-sub-workspace)
- [百炼 OpenAI 兼容 Embedding](https://help.aliyun.com/zh/model-studio/embedding-interfaces-compatible-with-openai)
- [百炼向量化模型说明](https://help.aliyun.com/zh/model-studio/embedding)

