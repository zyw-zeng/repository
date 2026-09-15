"""组装有界 LangGraph 工作流并定义节点之间的路由规则。"""

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.agent.nodes import AgentNodes
from app.agent.state import AgentState
from app.core.config import Settings


def build_agent_graph(nodes: AgentNodes, settings: Settings) -> CompiledStateGraph:
    """构建意图识别、工具执行、检索评价与有限重试工作流。"""
    graph = StateGraph(AgentState)
    # 同步节点不能被 Python 安全强制取消；外部模型调用使用 HTTP 超时，
    # 节点之间再检查总截止时间，图本身同时受 recursion_limit 限制。
    graph.add_node("classify_intent", nodes.classify_intent)
    graph.add_node("execute_tool", nodes.execute_tool)
    graph.add_node("rewrite_for_retry", nodes.rewrite_for_retry)
    graph.add_edge(START, "classify_intent")
    graph.add_edge("classify_intent", "execute_tool")
    graph.add_conditional_edges(
        "execute_tool",
        nodes.route_after_tool,
        {"retry": "rewrite_for_retry", "finish": END},
    )
    graph.add_conditional_edges(
        "rewrite_for_retry",
        nodes.route_after_retry,
        {"execute": "execute_tool", "finish": END},
    )
    return graph.compile(name="zyw-ai-assistant-agent")
