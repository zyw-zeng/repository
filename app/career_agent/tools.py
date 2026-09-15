"""把求职顾问服务封装为严格白名单工具。"""

from typing import Any

from langchain_core.tools import BaseTool, StructuredTool

from app.services.career_advice_service import CareerAdviceService

CAREER_ALLOWED_TOOL_NAMES = {
    "generate_self_introductions",
    "select_project_highlights",
    "prepare_interview_questions",
    "build_capability_plan",
    "analyze_advantages",
    "analyze_risks",
    "analyze_gaps",
    "recommend_application_strategy",
}


class CareerToolbox:
    """只暴露岗位报告分析能力，不允许访问通用 Agent 工具。"""

    def __init__(self, service: CareerAdviceService):
        self.service = service
        self.tools = self._build_tools()

    def _build_tools(self) -> dict[str, BaseTool]:
        """把无参数只读顾问方法转换为 LangChain 工具。"""

        def generate_self_introductions() -> dict[str, Any]:
            """生成 30 秒、1 分钟和文字版岗位定制自我介绍。"""
            return self.service.generate_self_introductions()

        def select_project_highlights() -> dict[str, Any]:
            """从可信材料中选择适合目标岗位的项目亮点。"""
            return self.service.select_project_highlights()

        def prepare_interview_questions() -> dict[str, Any]:
            """生成针对性面试问题和回答思路。"""
            return self.service.prepare_interview_questions()

        def build_capability_plan() -> dict[str, Any]:
            """生成分阶段能力与证据补足计划。"""
            return self.service.build_capability_plan()

        def analyze_advantages() -> dict[str, Any]:
            """分析当前目标岗位下最有证据的优势。"""
            return self.service.analyze_advantages()

        def analyze_risks() -> dict[str, Any]:
            """分析当前岗位的必备项风险。"""
            return self.service.analyze_risks()

        def analyze_gaps() -> dict[str, Any]:
            """区分真实能力缺口和材料证据缺口。"""
            return self.service.analyze_gaps()

        def recommend_application_strategy() -> dict[str, Any]:
            """给出是否投递及准备顺序建议。"""
            return self.service.recommend_application_strategy()

        functions = [
            generate_self_introductions,
            select_project_highlights,
            prepare_interview_questions,
            build_capability_plan,
            analyze_advantages,
            analyze_risks,
            analyze_gaps,
            recommend_application_strategy,
        ]
        return {
            function.__name__: StructuredTool.from_function(function)
            for function in functions
        }

    def invoke(self, name: str) -> dict[str, Any]:
        """白名单之外的名称始终拒绝执行。"""
        if name not in CAREER_ALLOWED_TOOL_NAMES or name not in self.tools:
            raise ValueError(f"不允许调用求职顾问工具：{name}")
        return self.tools[name].invoke({})
