"""构建独立于普通聊天 Agent 的求职顾问 LangGraph。"""

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.career_agent.nodes import CareerAgentNodes
from app.career_agent.state import CareerAgentState


def build_career_agent_graph(nodes: CareerAgentNodes) -> CompiledStateGraph:
    """构建有界工具循环；图中不存在动态工具或普通知识库入口。"""
    graph = StateGraph(CareerAgentState)
    graph.add_node("plan", nodes.plan)
    graph.add_node("execute_tool", nodes.execute_tool)
    graph.add_node("compose", nodes.compose)
    graph.add_edge(START, "plan")
    graph.add_conditional_edges(
        "plan", nodes.route_after_plan, {"execute": "execute_tool", "compose": "compose"}
    )
    graph.add_conditional_edges(
        "execute_tool",
        nodes.route_after_tool,
        {"execute": "execute_tool", "compose": "compose"},
    )
    graph.add_edge("compose", END)
    return graph.compile(name="zyw-career-advisor-agent")
