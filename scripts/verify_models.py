"""通过最小请求验证对话模型和向量模型是否能够正常调用。"""

import sys
from pathlib import Path

# 将项目根目录加入模块搜索路径，使脚本可以直接从命令行执行。
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings  # noqa: E402
from app.llm.factory import create_chat_model, create_embeddings  # noqa: E402


def main() -> int:
    """依次验证模型配置、对话响应和 Embedding 向量维度。"""
    settings = get_settings()
    if not settings.dashscope_api_key:
        print("未配置 DASHSCOPE_API_KEY，已跳过真实模型调用。")
        return 0

    # 两次调用都使用极短文本，尽量降低连通测试产生的费用。
    answer = create_chat_model(settings).invoke("只回复：连接成功")
    print(f"对话模型：{settings.chat_model}")
    print(f"模型响应：{answer.content}")

    vector = create_embeddings(settings).embed_query("ZYW 的 AI 小助理模型连通测试")
    print(f"Embedding 模型：{settings.embedding_model}")
    print(f"向量维度：{len(vector)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
