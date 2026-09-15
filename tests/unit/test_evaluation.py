"""验证标准问题集的正确率、引用、拒答和延迟统计。"""

from evaluations.evaluate import calculate_metrics, percentile


def test_quality_metrics_count_answer_citation_and_retrieval() -> None:
    """可回答问题需要同时统计回答、引用、来源和召回情况。"""
    cases = [
        {
            "type": "direct",
            "expected_grounded": True,
            "expected_evidence_groups": [["SQLite"]],
            "expected_answer_groups": [["SQLite"]],
            "expected_sources": ["README.md"],
        },
        {
            "type": "direct",
            "expected_grounded": True,
            "expected_evidence_groups": [["拒答"]],
            "expected_answer_groups": [["拒答"]],
        },
    ]
    responses = [
        {
            "answer": "SQLite 保存权威正文。",
            "grounded": True,
            "citations": [{"quote": "SQLite 是权威数据", "filename": "README.md"}],
            "retrieved_count": 3,
            "latency_ms": 120,
        },
        {
            "answer": "资料不足时拒答。",
            "grounded": True,
            "citations": [{"quote": "没有依据时拒答", "filename": "DEVELOPMENT_PLAN.md"}],
            "retrieved_count": 2,
            "latency_ms": 300,
        },
    ]

    metrics = calculate_metrics(cases, responses)

    assert metrics["answer_accuracy"] == 1.0
    assert metrics["citation_accuracy"] == 1.0
    assert metrics["source_accuracy"] == 1.0
    assert metrics["retrieval_hit_rate"] == 1.0
    assert metrics["latency_ms"]["p50"] == 120
    assert metrics["latency_ms"]["p95"] == 300


def test_no_answer_rate_rejects_grounded_hallucination() -> None:
    """无答案问题带引用作答时不能计为正确拒答。"""
    cases = [
        {"type": "no_answer", "expected_grounded": False},
        {"type": "no_answer", "expected_grounded": False},
    ]
    responses = [
        {"grounded": False, "citations": [], "latency_ms": 100},
        {
            "grounded": True,
            "citations": [{"quote": "无关内容"}],
            "latency_ms": 200,
        },
    ]

    metrics = calculate_metrics(cases, responses)

    assert metrics["no_answer_refusal_rate"] == 0.5
    assert metrics["by_type"]["no_answer"]["pass_rate"] == 0.5


def test_percentile_uses_nearest_rank() -> None:
    """P95 使用最近秩算法，少量样本时不会被插值掩盖慢请求。"""
    assert percentile([100, 200, 300, 400, 500], 0.95) == 500
    assert percentile([], 0.95) == 0

