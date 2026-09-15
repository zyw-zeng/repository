"""使用确定性规则选择 Career Agent 的只读顾问工具。"""

import re

CAREER_TOOL_PATTERNS = {
    "generate_self_introductions": re.compile(
        r"自我介绍|介绍自己|30秒|一分钟|1分钟|求职简介|招呼语"
    ),
    "select_project_highlights": re.compile(r"项目亮点|项目卖点|项目怎么写|项目经历"),
    "prepare_interview_questions": re.compile(
        r"面试问题|面试题|回答思路|怎么回答|面试准备|会问什么"
    ),
    "build_capability_plan": re.compile(r"能力补足计划|学习计划|提升计划|补强计划"),
    "analyze_advantages": re.compile(r"优势|长处|竞争力|匹配点|亮点"),
    "analyze_risks": re.compile(r"风险|硬伤|劣势|不利|会不会被筛"),
    "analyze_gaps": re.compile(r"能力缺口|能力短板|能力不足|欠缺|缺少|不会|补足"),
    "recommend_application_strategy": re.compile(
        r"应聘|投递|策略|怎么准备|如何准备|适合我|值得投|建议|下一步"
    ),
}


def select_career_tools(question: str) -> list[str]:
    """按用户明确意图选择一个或多个工具，执行数量受图步骤预算限制。"""
    normalized = " ".join(question.strip().split())
    selected = [
        tool_name
        for tool_name, pattern in CAREER_TOOL_PATTERNS.items()
        if pattern.search(normalized)
    ]
    if selected:
        return selected
    if re.search(r"这个岗位|该岗位|岗位分析|匹配报告|求职顾问", normalized):
        return ["recommend_application_strategy"]
    return []
