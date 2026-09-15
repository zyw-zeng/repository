"""使用高置信度规则优先完成 Agent 工具路由。"""

import re

CASUAL_PATTERN = re.compile(
    r"^(你好|您好|嗨|哈喽|hello|hi|早上好|下午好|晚上好|晚安|"
    r"谢谢|感谢|再见|拜拜|在吗|你好吗|最近怎么样)[呀啊哦呢吗～~！!。.，,\s]*$",
    re.IGNORECASE,
)

CASUAL_TOPIC_PATTERN = re.compile(
    r"(讲|说|来).{0,6}(笑话|故事)|"
    r"(陪我|和我|我们).{0,6}(聊聊|聊天)|"
    r"(随便聊|聊聊天|闲聊)|"
    r"(我|心情).{0,8}(开心|难过|伤心|焦虑|无聊|累|烦)|"
    r"你.{0,5}(喜欢|心情|会不会聊天)",
    re.IGNORECASE,
)
LIST_DOCUMENT_PATTERN = re.compile(r"(有哪些|列出|查看|显示).{0,6}(文档|资料)|文档列表")
DOCUMENT_INFO_PATTERN = re.compile(
    r"(文档|文件|\.pdf|\.docx|\.md|\.txt).{0,12}(状态|详情|信息|大小|切片|索引版本)|"
    r"(状态|详情).{0,12}(文档|文件|\.pdf|\.docx|\.md|\.txt)",
    re.IGNORECASE,
)
SUMMARY_PATTERN = re.compile(
    r"(总结|概括|摘要|归纳).{0,30}(文档|文件|资料|\.pdf|\.docx|\.md|\.txt)",
    re.IGNORECASE,
)
RESUME_PATTERN = re.compile(
    r"(下载|查看|看看|打开|获取|给我|发我|提供).{0,10}(简历|履历|CV)|"
    r"(简历|履历|CV).{0,10}(下载|链接|地址|PDF|文件|看看|查看|打开)",
    re.IGNORECASE,
)
KNOWLEDGE_PATTERN = re.compile(
    r"(ZYW|知识库|个人资料|简历|项目|技术栈|技术能力|经历|工作经历|"
    r"Agent|RAG|这个助理|这个系统|前端架构|后端架构)",
    re.IGNORECASE,
)


def route_by_rule(question: str) -> str | None:
    """命中明确规则时直接返回工具名；含糊输入交给快速路由模型。"""
    normalized = " ".join(question.strip().split())
    if CASUAL_PATTERN.fullmatch(normalized):
        return "answer_casual"
    if CASUAL_TOPIC_PATTERN.search(normalized):
        return "answer_casual"
    if RESUME_PATTERN.search(normalized):
        return "get_resume"
    if LIST_DOCUMENT_PATTERN.search(normalized):
        return "list_documents"
    if SUMMARY_PATTERN.search(normalized):
        return "summarize_document"
    if DOCUMENT_INFO_PATTERN.search(normalized):
        return "get_document_info"
    if KNOWLEDGE_PATTERN.search(normalized):
        return "search_knowledge"
    return None
