"""验证 JD 原子化、结构化档案和来源质量评分。"""

import json
from pathlib import Path

from app.jd_matching.atomic import atomize_requirements
from app.jd_matching.evidence import evidence_source_quality
from app.jd_matching.profile import CandidateProfileService
from app.jd_matching.scoring import awarded_score, calculate_scores


def test_atomize_composite_requirements() -> None:
    """年限、专业和框架能力不应继续合并成同一评分项。"""
    result = atomize_requirements(
        [
            {
                "requirement": "3年以上前端开发经验、计算机相关专业",
                "category": "必备项",
                "importance": "required",
                "weight": 9,
                "keywords": ["前端开发经验", "计算机专业"],
            },
            {
                "requirement": "熟练使用Vue框架，有TypeScript工程化实践",
                "category": "必备项",
                "importance": "required",
                "weight": 8,
                "keywords": ["Vue", "TypeScript"],
            },
        ]
    )

    assert [item["requirement"] for item in result] == [
        "3年以上前端开发经验",
        "计算机相关专业",
        "熟练使用Vue框架",
        "有TypeScript工程化实践",
    ]
    assert result[0]["requirement_type"] == "profile_fact"
    assert result[2]["requirement_type"] == "technical_skill"


def test_atomize_keeps_parenthesized_technical_details_together() -> None:
    """括号中的虚拟 DOM、响应式等说明不能被错误拆成独立要求。"""
    result = atomize_requirements(
        [
            {
                "requirement": "深入理解框架原理（虚拟DOM、响应式、生命周期），有TypeScript实践",
                "category": "必备项",
                "importance": "required",
                "weight": 8,
                "keywords": ["虚拟DOM", "TypeScript"],
            }
        ]
    )

    assert [item["requirement"] for item in result] == [
        "深入理解框架原理（虚拟DOM、响应式、生命周期）",
        "有TypeScript实践",
    ]


def test_candidate_profile_only_matches_explicit_aliases(tmp_path: Path) -> None:
    """结构化档案只能通过本人配置的明确别名命中，不能自由推断。"""
    profile_path = tmp_path / "profile.json"
    profile_path.write_text(
        json.dumps(
            {
                "version": 2,
                "facts": [
                    {
                        "id": "frontend-years",
                        "aliases": ["前端开发经验"],
                        "evidence": "拥有6年前端开发经验。",
                        "source": "个人简历.pdf",
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    service = CandidateProfileService(profile_path)

    matched = service.search("要求3年以上前端开发经验")
    unrelated = service.search("要求计算机相关专业")

    assert matched[0].chunk_id == "profile:frontend-years"
    assert matched[0].index_version == 2
    assert unrelated == []


def test_three_scores_and_source_quality_are_deterministic() -> None:
    """三个指标应分离知识缺失与已验证能力匹配程度。"""
    high_quality_score = awarded_score(10, "strong_match", 0.95)
    matches = [
        {"weight": 10, "awarded_score": high_quality_score, "evidence": [{}]},
        {"weight": 10, "awarded_score": 0, "evidence": []},
    ]

    conservative, coverage, verified_fit, feasibility = calculate_scores(matches)

    assert (conservative, coverage, verified_fit) == (47.5, 50.0, 95.0)
    assert feasibility == 41.6
    assert evidence_source_quality(
        {
            "document_id": "doc-plan",
            "filename": "DEVELOPMENT_PLAN.md",
            "quote": "下一阶段计划实现浏览器插件",
        }
    ) == 0.2
