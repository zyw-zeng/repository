"""速度模式规则路由的高置信度行为测试。"""

import pytest

from app.agent.router import route_by_rule


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("你好", "answer_casual"),
        ("你好呀！", "answer_casual"),
        ("讲个笑话吧", "answer_casual"),
        ("我今天有点难过，陪我聊聊", "answer_casual"),
        ("你喜欢什么电影？", "answer_casual"),
        ("为什么天空是蓝色的？", None),
        ("Python 怎么读取文件？", None),
        ("知识库里有哪些文档？", "list_documents"),
        ("知识.md 的状态是什么？", "get_document_info"),
        ("请总结知识.md", "summarize_document"),
        ("把你的简历 PDF 发给我", "get_resume"),
        ("我想下载曾有为的 CV", "get_resume"),
        ("ZYW 做过哪些项目？", "search_knowledge"),
        ("请介绍 ZYW 的技术能力", "search_knowledge"),
        ("执行未知任务", None),
    ],
)
def test_rule_router_only_handles_clear_intents(question: str, expected: str | None) -> None:
    """明确意图直接路由，含糊命令保留给快速模型判断。"""
    assert route_by_rule(question) == expected
