"""构建与普通聊天隔离的 JD 岗位匹配 LangGraph。"""

from langgraph.graph import END, START, StateGraph

from app.jd_matching.nodes import JdMatchingNodes
from app.jd_matching.state import JdMatchingState


def build_jd_matching_graph(nodes: JdMatchingNodes):
    """按解析、检索、核验和评分的固定可靠路径编译工作流。"""
    graph = StateGraph(JdMatchingState)
    graph.add_node("parse_jd", nodes.parse_jd)
    graph.add_node("retrieve_evidence", nodes.retrieve_evidence)
    graph.add_node("evaluate_requirements", nodes.evaluate_requirements)
    graph.add_node("verify_and_score", nodes.verify_and_score)
    graph.add_edge(START, "parse_jd")
    graph.add_edge("parse_jd", "retrieve_evidence")
    graph.add_edge("retrieve_evidence", "evaluate_requirements")
    graph.add_edge("evaluate_requirements", "verify_and_score")
    graph.add_edge("verify_and_score", END)
    return graph.compile()
