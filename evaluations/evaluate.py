"""运行可靠 RAG 标准评测并生成可留档的质量报告。"""

from __future__ import annotations

import argparse
import json
import math
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

DEFAULT_REPORT_DIR = Path("evaluations/reports")


def load_cases(path: Path) -> list[dict[str, Any]]:
    """读取并校验 UTF-8 标准问题集。"""
    cases = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(cases, list) or not cases:
        raise ValueError("评测集必须是非空数组")
    identifiers = [case.get("id") for case in cases]
    if any(not identifier for identifier in identifiers):
        raise ValueError("每个评测问题都必须包含 id")
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("评测问题 id 不能重复")
    return cases


def _expected_groups(case: dict[str, Any], field: str) -> list[list[str]]:
    """兼容旧版单层关键词，并统一转换为等价表述分组。"""
    groups = case.get(field)
    if groups is not None:
        return groups
    if field == "expected_evidence_groups":
        return [[term] for term in case.get("expected_evidence_terms", [])]
    return case.get("expected_evidence_groups", [])


def _groups_in_text(groups: list[list[str]], text: str) -> bool:
    """每组事实至少命中一个等价表述，所有事实组都必须满足。"""
    return all(any(term.lower() in text.lower() for term in group) for group in groups)


def citation_supports_case(case: dict[str, Any], response: dict[str, Any]) -> bool:
    """判断引用正文是否包含题集指定的关键依据。"""
    if not response.get("grounded") or not response.get("citations"):
        return False
    quotes = "\n".join(citation.get("quote", "") for citation in response["citations"])
    return _groups_in_text(_expected_groups(case, "expected_evidence_groups"), quotes)


def answer_supports_case(case: dict[str, Any], response: dict[str, Any]) -> bool:
    """使用确定性关键事实检查回答完整性，不以模型自评替代验收。"""
    if not response.get("grounded"):
        return False
    return _groups_in_text(
        _expected_groups(case, "expected_answer_groups"), response.get("answer", "")
    )


def source_matches_case(case: dict[str, Any], response: dict[str, Any]) -> bool:
    """当题集声明来源时，确认至少有一个引用来自允许的文件。"""
    expected_sources = {item.lower() for item in case.get("expected_sources", [])}
    if not expected_sources:
        return True
    filenames = {
        str(citation.get("filename", "")).lower() for citation in response.get("citations", [])
    }
    return bool(expected_sources & filenames)


def percentile(values: list[float], quantile: float) -> float:
    """计算最近秩百分位，空集合返回 0。"""
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, math.ceil(quantile * len(ordered)) - 1))
    return round(ordered[index], 2)


def calculate_metrics(
    cases: list[dict[str, Any]], responses: list[dict[str, Any]]
) -> dict[str, Any]:
    """计算回答、引用、拒答、检索、错误和延迟指标。"""
    if len(cases) != len(responses):
        raise ValueError("评测问题和响应数量必须一致")
    answerable_total = answer_correct_total = citation_supported_total = 0
    source_matched_total = retrieval_hit_total = 0
    no_answer_total = refused_total = error_total = 0
    latencies: list[float] = []
    type_totals: dict[str, dict[str, int]] = {}

    for case, response in zip(cases, responses, strict=True):
        case_type = case.get("type", "unknown")
        type_metric = type_totals.setdefault(case_type, {"total": 0, "passed": 0})
        type_metric["total"] += 1
        latency = float(response.get("latency_ms", 0))
        if latency > 0:
            latencies.append(latency)
        error_total += int(bool(response.get("error")))
        if case["expected_grounded"]:
            answerable_total += 1
            answer_ok = answer_supports_case(case, response)
            citation_ok = citation_supports_case(case, response)
            source_ok = source_matches_case(case, response)
            retrieval_ok = bool(response.get("retrieved_count", 0) or response.get("citations"))
            answer_correct_total += int(answer_ok)
            citation_supported_total += int(citation_ok)
            source_matched_total += int(source_ok)
            retrieval_hit_total += int(retrieval_ok)
            type_metric["passed"] += int(answer_ok and citation_ok and source_ok)
        else:
            no_answer_total += 1
            refused = not response.get("grounded") and not response.get("citations")
            refused_total += int(refused)
            type_metric["passed"] += int(refused)

    def rate(value: int, total: int) -> float:
        return round(value / total, 4) if total else 1.0

    return {
        "case_total": len(cases),
        "answerable_total": answerable_total,
        "answer_correct_total": answer_correct_total,
        "answer_accuracy": rate(answer_correct_total, answerable_total),
        "citation_supported_total": citation_supported_total,
        "citation_accuracy": rate(citation_supported_total, answerable_total),
        "source_matched_total": source_matched_total,
        "source_accuracy": rate(source_matched_total, answerable_total),
        "retrieval_hit_total": retrieval_hit_total,
        "retrieval_hit_rate": rate(retrieval_hit_total, answerable_total),
        "no_answer_total": no_answer_total,
        "refused_total": refused_total,
        "no_answer_refusal_rate": rate(refused_total, no_answer_total),
        "error_total": error_total,
        "error_rate": rate(error_total, len(cases)),
        "latency_ms": {
            "min": round(min(latencies), 2) if latencies else 0.0,
            "p50": percentile(latencies, 0.5),
            "p95": percentile(latencies, 0.95),
            "max": round(max(latencies), 2) if latencies else 0.0,
        },
        "by_type": {
            name: {**values, "pass_rate": rate(values["passed"], values["total"])}
            for name, values in sorted(type_totals.items())
        },
    }


def run_evaluation(base_url: str, cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """逐题调用后端，每道题使用独立上下文并记录端到端延迟。"""
    observations: list[dict[str, Any]] = []
    with httpx.Client(base_url=base_url.rstrip("/"), timeout=120) as client:
        for index, case in enumerate(cases, start=1):
            started_at = time.perf_counter()
            payload: dict[str, Any] | None = None
            error: str | None = None
            for attempt in range(3):
                try:
                    response = client.post(
                        "/api/v1/chat/query",
                        json={"question": case["question"], "mode": "knowledge_base"},
                    )
                    response.raise_for_status()
                    payload = response.json()
                    break
                except httpx.HTTPError as exc:
                    error = f"{type(exc).__name__}: {exc}"
                    if attempt == 2:
                        break
                    time.sleep(2**attempt)
            latency_ms = round((time.perf_counter() - started_at) * 1000, 2)
            observation = payload or {
                "answer": "",
                "grounded": False,
                "citations": [],
                "retrieved_count": 0,
            }
            observation["latency_ms"] = latency_ms
            observation["error"] = error if payload is None else None
            observations.append(observation)
            print(f"[{index}/{len(cases)}] {case['id']} - {latency_ms:.0f} ms")
    return observations


def build_details(
    cases: list[dict[str, Any]], responses: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """构造便于定位失败问题的逐题报告。"""
    details = []
    for case, response in zip(cases, responses, strict=True):
        if case["expected_grounded"]:
            answer_ok = answer_supports_case(case, response)
            citation_ok = citation_supports_case(case, response)
            source_ok = source_matches_case(case, response)
            passed = answer_ok and citation_ok and source_ok and not response.get("error")
        else:
            answer_ok = citation_ok = source_ok = None
            passed = (
                not response.get("grounded")
                and not response.get("citations")
                and not response.get("error")
            )
        details.append(
            {
                "id": case["id"],
                "type": case.get("type", "unknown"),
                "question": case["question"],
                "passed": passed,
                "grounded": response.get("grounded", False),
                "answer_correct": answer_ok,
                "citation_supported": citation_ok,
                "source_matched": source_ok,
                "citation_count": len(response.get("citations", [])),
                "retrieved_count": response.get("retrieved_count", 0),
                "latency_ms": response.get("latency_ms", 0),
                "error": response.get("error"),
            }
        )
    return details


def write_report(
    output_path: Path,
    dataset_path: Path,
    base_url: str,
    thresholds: dict[str, float],
    metrics: dict[str, Any],
    details: list[dict[str, Any]],
    passed: bool,
) -> None:
    """以 UTF-8 JSON 保存一次可追踪的评测结果。"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).isoformat(),
        "dataset": str(dataset_path),
        "base_url": base_url,
        "thresholds": thresholds,
        "passed": passed,
        "metrics": metrics,
        "details": details,
    }
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    """运行评测，保存报告并按质量门槛返回退出码。"""
    parser = argparse.ArgumentParser(description="评测 ZYW 的 AI 小助理可靠 RAG")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument(
        "--dataset", type=Path, default=Path("evaluations/datasets/smoke_questions.json")
    )
    parser.add_argument("--min-answer-accuracy", type=float, default=0.8)
    parser.add_argument("--min-citation-accuracy", type=float, default=0.9)
    parser.add_argument("--min-refusal-rate", type=float, default=0.9)
    parser.add_argument("--min-retrieval-hit-rate", type=float, default=0.85)
    parser.add_argument("--max-error-rate", type=float, default=0.0)
    parser.add_argument("--max-p95-ms", type=float, default=10000)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()

    cases = load_cases(arguments.dataset)
    responses = run_evaluation(arguments.base_url, cases)
    metrics = calculate_metrics(cases, responses)
    details = build_details(cases, responses)
    thresholds = {
        "answer_accuracy": arguments.min_answer_accuracy,
        "citation_accuracy": arguments.min_citation_accuracy,
        "no_answer_refusal_rate": arguments.min_refusal_rate,
        "retrieval_hit_rate": arguments.min_retrieval_hit_rate,
        "error_rate": arguments.max_error_rate,
        "p95_latency_ms": arguments.max_p95_ms,
    }
    passed = (
        metrics["answer_accuracy"] >= arguments.min_answer_accuracy
        and metrics["citation_accuracy"] >= arguments.min_citation_accuracy
        and metrics["no_answer_refusal_rate"] >= arguments.min_refusal_rate
        and metrics["retrieval_hit_rate"] >= arguments.min_retrieval_hit_rate
        and metrics["error_rate"] <= arguments.max_error_rate
        and metrics["latency_ms"]["p95"] <= arguments.max_p95_ms
    )
    output_path = arguments.output or (
        DEFAULT_REPORT_DIR / f"evaluation-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    )
    write_report(
        output_path,
        arguments.dataset,
        arguments.base_url,
        thresholds,
        metrics,
        details,
        passed,
    )
    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    print(f"评测报告：{output_path}")
    print("评测结论：通过" if passed else "评测结论：未通过")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

