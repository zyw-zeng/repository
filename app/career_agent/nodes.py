"""实现 Career Agent 的规划、白名单工具循环和回答组装节点。"""

import time
from typing import Any

from app.agent.runtime import (
    emit_agent_event,
    emit_agent_step,
    raise_if_agent_cancelled,
)
from app.career_agent.router import select_career_tools
from app.career_agent.state import CareerAgentState
from app.career_agent.tools import CareerToolbox
from app.services.career_advice_service import CareerContextSnapshot


class CareerAgentNodes:
    """执行最多四个只读工具，并在每个节点检查取消与截止时间。"""

    def __init__(self, toolbox: CareerToolbox, context: CareerContextSnapshot):
        self.toolbox = toolbox
        self.context = context

    def plan(self, state: CareerAgentState) -> dict[str, Any]:
        """根据问题建立确定性工具计划，不允许模型发明工具名称。"""
        self._guard(state)
        selected = select_career_tools(state["question"])
        emit_agent_event(
            "career_context",
            {
                "analysis_id": self.context.analysis_id,
                "job_title": self.context.job_title,
                "profile_version": self.context.profile_version,
                "stale": self.context.stale,
            },
        )
        return {
            "selected_tools": selected,
            "next_tool_index": 0,
            "context_stale": self.context.stale,
            "step_count": state.get("step_count", 0) + 1,
            "steps": emit_agent_step(
                "career_plan",
                status="completed",
                selected_tools=selected,
                context_stale=self.context.stale,
            ),
        }

    def execute_tool(self, state: CareerAgentState) -> dict[str, Any]:
        """每次只执行计划中的一个工具，让 LangGraph 显式记录循环。"""
        self._guard(state)
        index = state.get("next_tool_index", 0)
        tool_name = state["selected_tools"][index]
        started = time.perf_counter()
        result = self.toolbox.invoke(tool_name)
        raise_if_agent_cancelled()
        duration_ms = int((time.perf_counter() - started) * 1000)
        emit_agent_event(
            "career_tool_result",
            {"tool": tool_name, "title": result["title"], "duration_ms": duration_ms},
        )
        return {
            "next_tool_index": index + 1,
            "sections": [{"title": result["title"], "content": result["content"]}],
            "evidence": result.get("evidence", []),
            "step_count": state.get("step_count", 0) + 1,
            "timings": {
                **state.get("timings", {}),
                f"career_tool_{index + 1}_ms": duration_ms,
            },
            "steps": emit_agent_step(
                "career_tool",
                status="completed",
                tool=tool_name,
                duration_ms=duration_ms,
            ),
        }

    def compose(self, state: CareerAgentState) -> dict[str, Any]:
        """去重引用并生成可直接保存和朗读的顾问回答。"""
        if self.context.stale:
            answer = "个人档案已经更新，当前岗位报告使用的是旧版本。请重新提交该 JD 后再继续咨询。"
            citations: list[dict[str, Any]] = []
            degraded = True
            error = "career_context_stale"
        else:
            citations = self._deduplicate_citations(state.get("evidence", []))
            sections = state.get("sections", [])
            answer = f"针对《{self.context.job_title}》：\n\n" + "\n\n".join(
                f"### {section['title']}\n{section['content']}" for section in sections
            )
            if citations:
                references = "".join(f"[{item['reference_number']}]" for item in citations)
                answer += f"\n\n以上建议基于当前岗位报告中已验证的资料。{references}"
            degraded = not bool(sections)
            error = "career_tool_plan_empty" if degraded else None
        emit_agent_event("answer_delta", {"delta": answer})
        return {
            "answer": answer,
            "answer_mode": "career_advisor",
            "grounded": bool(citations),
            "citations": citations,
            "resources": [],
            "degraded": degraded,
            "error": error,
            "step_count": state.get("step_count", 0) + 1,
            "steps": emit_agent_step(
                "career_compose",
                status="fallback" if degraded else "completed",
            ),
        }

    @staticmethod
    def route_after_plan(state: CareerAgentState) -> str:
        """过期上下文直接解释，正常计划进入工具循环。"""
        if state.get("context_stale") or not state.get("selected_tools"):
            return "compose"
        if (
            state.get("step_count", 0) >= state["max_steps"] - 1
            or time.monotonic() >= state["deadline"]
        ):
            return "compose"
        return "execute"

    @staticmethod
    def route_after_tool(state: CareerAgentState) -> str:
        """仍有工具且预算充足时继续，否则进入回答组装。"""
        has_more = state.get("next_tool_index", 0) < len(state.get("selected_tools", []))
        within_budget = (
            state.get("step_count", 0) < state["max_steps"] - 1
            and time.monotonic() < state["deadline"]
        )
        return "execute" if has_more and within_budget else "compose"

    @staticmethod
    def _guard(state: CareerAgentState) -> None:
        """在每次工具调用前执行取消、步骤和总超时检查。"""
        raise_if_agent_cancelled()
        if state.get("step_count", 0) >= state["max_steps"]:
            raise RuntimeError("Career Agent 已达到最大步骤数")
        if time.monotonic() >= state["deadline"]:
            raise TimeoutError("Career Agent 已达到总超时")

    @staticmethod
    def _deduplicate_citations(evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """按切片 ID 去重并补充连续引用编号。"""
        citations = []
        seen: set[str] = set()
        for source in evidence:
            chunk_id = str(source.get("chunk_id", ""))
            if not chunk_id or chunk_id in seen:
                continue
            seen.add(chunk_id)
            citations.append(
                {
                    "reference_number": len(citations) + 1,
                    "chunk_id": chunk_id,
                    "document_id": str(source.get("document_id", "")),
                    "filename": str(source.get("filename", "")),
                    "quote": str(source.get("quote", "")),
                    "page_number": source.get("page_number"),
                    "heading": source.get("heading"),
                    "index_version": int(source.get("index_version", 0)),
                }
            )
            if len(citations) >= 8:
                break
        return citations
