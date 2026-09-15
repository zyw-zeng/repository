"""提供 Career Agent 可调用的只读求职分析能力。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.jd_matching.profile import CandidateProfileService
from app.storage.models import Conversation
from app.storage.repositories.documents import DocumentRepository
from app.storage.repositories.jd_analyses import JdAnalysisRepository


@dataclass(slots=True)
class CareerContextSnapshot:
    """一次求职对话固定使用的岗位和个人档案版本。"""

    analysis_id: str
    company_name: str | None
    job_title: str
    profile_version: int | None
    current_profile_version: int | None
    score: float
    completeness: float
    feasibility: float
    matches: list[dict[str, Any]]

    @property
    def stale(self) -> bool:
        """档案版本变化后要求重新分析，避免混用新旧个人事实。"""
        if self.current_profile_version is not None and self.profile_version is None:
            return True
        return (
            self.profile_version is not None
            and self.current_profile_version is not None
            and self.profile_version != self.current_profile_version
        )


class CareerAdviceService:
    """只基于已保存 JD 报告生成可解释的求职建议。"""

    def __init__(self, session: Session, settings: Settings, conversation: Conversation):
        self.session = session
        self.settings = settings
        self.conversation = conversation
        self.documents = DocumentRepository(session)
        self.analyses = JdAnalysisRepository(session)
        self.profile = CandidateProfileService(settings.candidate_profile_path)
        self.context = self._load_context()
        self._valid_chunks = self._load_valid_chunks()

    def _load_context(self) -> CareerContextSnapshot | None:
        """读取会话明确绑定的已完成报告，不从任意历史消息猜测岗位。"""
        if not self.conversation.active_jd_analysis_id:
            return None
        analysis = self.analyses.get(self.conversation.active_jd_analysis_id)
        if analysis is None or analysis.status != "completed":
            return None
        return CareerContextSnapshot(
            analysis_id=analysis.id,
            company_name=analysis.company_name,
            job_title=analysis.job_title or "目标岗位",
            profile_version=self.conversation.candidate_profile_version,
            current_profile_version=self.profile.get_version(),
            score=float(analysis.score or 0),
            completeness=float(analysis.completeness or 0),
            feasibility=float(analysis.feasibility or analysis.score or 0),
            matches=list(analysis.matches_json or []),
        )

    def _load_valid_chunks(self) -> dict[str, Any]:
        """重新验证普通文档证据仍属于公开活动版本。"""
        if self.context is None:
            return {}
        chunk_ids = {
            str(evidence.get("chunk_id"))
            for match in self.context.matches
            for evidence in match.get("evidence", [])
            if evidence.get("document_id") != "candidate-profile"
            and evidence.get("chunk_id")
        }
        chunks = self.documents.get_verified_active_chunks(list(chunk_ids), public_only=True)
        return {chunk.id: chunk for chunk in chunks}

    def has_context(self) -> bool:
        """判断当前会话是否具有可使用的岗位报告。"""
        return self.context is not None

    def analyze_advantages(self) -> dict[str, Any]:
        """返回证据最强且岗位权重最高的优势。"""
        context = self._required_context()
        candidates = [
            item
            for item in context.matches
            if item.get("level") in {"strong_match", "partial_match"}
        ]
        candidates.sort(
            key=lambda item: (
                item.get("level") == "strong_match",
                float(item.get("awarded_score", 0)),
                float(item.get("weight", 0)),
            ),
            reverse=True,
        )
        selected = candidates[:4]
        if not selected:
            content = "当前报告还没有找到可以由可靠资料确认的岗位优势。"
        else:
            lines = [
                f"- {item['requirement']}：{item.get('reason', '已有相关证据。')}"
                for item in selected
            ]
            content = "最值得优先表达的优势：\n" + "\n".join(lines)
        return self._section("岗位优势", content, selected)

    def analyze_risks(self) -> dict[str, Any]:
        """优先识别必备项中的明确缺口、冲突和材料不足。"""
        context = self._required_context()
        priority = {"missing": 4, "conflict": 3, "unverified": 2, "partial_match": 1}
        candidates = [
            item
            for item in context.matches
            if item.get("importance") == "required"
            and item.get("level") in priority
        ]
        candidates.sort(
            key=lambda item: (
                priority.get(str(item.get("level")), 0),
                float(item.get("weight", 0)),
            ),
            reverse=True,
        )
        selected = candidates[:5]
        if not selected:
            content = "当前证据中没有发现明显的必备项风险，但仍应以招聘方实际筛选为准。"
        else:
            lines = [f"- {item['requirement']}：{self._risk_label(item)}" for item in selected]
            content = "投递前需要重点关注：\n" + "\n".join(lines)
        return self._section("应聘风险", content, selected)

    def analyze_gaps(self) -> dict[str, Any]:
        """区分真实缺口和证据缺口，并给出不会夸大经历的补足动作。"""
        context = self._required_context()
        candidates = [
            item
            for item in context.matches
            if item.get("level") in {"missing", "unverified", "partial_match", "conflict"}
        ]
        candidates.sort(
            key=lambda item: (
                item.get("importance") == "required",
                float(item.get("weight", 0)),
            ),
            reverse=True,
        )
        selected = candidates[:6]
        if not selected:
            content = "当前报告没有识别出需要优先补足的能力项。"
        else:
            lines = [
                f"- {item['requirement']}：{self._gap_action(item)}" for item in selected
            ]
            content = "能力与材料缺口建议：\n" + "\n".join(lines)
        return self._section("能力缺口", content, selected)

    def recommend_application_strategy(self) -> dict[str, Any]:
        """根据必备项优先的可行度给出保守投递策略。"""
        context = self._required_context()
        if context.feasibility >= 70:
            decision = "建议积极投递，并把强匹配项目放在自我介绍前半段。"
        elif context.feasibility >= 45:
            decision = "可以投递，但应先补齐关键证据，并准备解释部分匹配的能力迁移路径。"
        else:
            decision = "建议谨慎投递；优先补足高权重必备项，或寻找要求更贴近现有经历的岗位。"
        required_risks = sum(
            item.get("importance") == "required"
            and item.get("level") in {"missing", "conflict", "unverified"}
            for item in context.matches
        )
        content = (
            f"{decision}\n\n"
            f"- 岗位匹配度：{context.score:.1f}%\n"
            f"- 证据完整度：{context.completeness:.1f}%\n"
            f"- 求职可行度：{context.feasibility:.1f}%\n"
            f"- 需要优先处理的必备项风险：{required_risks} 项"
        )
        supporting = [
            item
            for item in context.matches
            if item.get("level") in {"strong_match", "partial_match"}
        ][:3]
        return self._section("应聘策略", content, supporting)

    def generate_self_introductions(self) -> dict[str, Any]:
        """生成三种长度的岗位定制自我介绍，并只使用已验证匹配项。"""
        context = self._required_context()
        selected = self._strongest_matches(limit=3)
        if not selected:
            content = "当前没有足够的可信证据生成岗位定制自我介绍，请先补充个人材料。"
            return self._section("岗位定制自我介绍", content, [])

        brief = self._match_phrase(selected[0])
        details = "；".join(self._match_phrase(item) for item in selected[:2])
        full_details = "；".join(self._match_phrase(item) for item in selected)
        content = (
            "#### 30 秒版\n"
            f"您好，我是 ZYW，正在应聘{context.job_title}。我最相关的优势是{brief}。"
            "我希望把这些经过项目验证的能力用于岗位实际问题，也愿意坦诚说明仍需补足的部分。\n\n"
            "#### 1 分钟版\n"
            f"您好，我是 ZYW，我关注的目标岗位是{context.job_title}。结合岗位要求，"
            f"我的主要匹配点包括{details}。这些内容均来自当前可核查的个人项目或经历。"
            "如果进入后续沟通，我会重点介绍相关项目中的职责、技术取舍和最终结果，"
            "同时对证据不足的要求给出真实的学习与迁移方案。\n\n"
            "#### 文字版\n"
            f"ZYW 希望应聘{context.company_name + '的' if context.company_name else ''}"
            f"{context.job_title}。与岗位相关的可信能力包括：{full_details}。"
            f"当前岗位匹配度为 {context.score:.1f}%，求职可行度为 {context.feasibility:.1f}%。"
            "上述表述仅采用已验证材料，适合作为简历摘要或求职平台招呼语的初稿。"
        )
        return self._section("岗位定制自我介绍", content, selected)

    def select_project_highlights(self) -> dict[str, Any]:
        """从可信证据中筛选最贴近岗位的项目亮点。"""
        self._required_context()
        candidates = [
            item
            for item in self._strongest_matches(limit=8)
            if item.get("requirement_type")
            in {"project_experience", "engineering_capability", "technical_skill"}
        ][:4]
        if not candidates:
            content = "当前报告没有找到可安全用于该岗位的项目亮点。"
        else:
            lines = []
            for index, item in enumerate(candidates, start=1):
                lines.append(
                    f"{index}. **{item['requirement']}**：{item.get('reason', '已有相关证据。')}"
                    " 面试时请补充本人真实职责、技术取舍和可核查结果，不要虚构量化数据。"
                )
            content = "建议优先展示以下项目亮点：\n" + "\n".join(lines)
        return self._section("岗位项目亮点", content, candidates)

    def prepare_interview_questions(self) -> dict[str, Any]:
        """根据优势与风险生成面试问题和有证据边界的回答思路。"""
        context = self._required_context()
        strengths = self._strongest_matches(limit=3)
        risks = [
            item
            for item in context.matches
            if item.get("level") in {"missing", "unverified", "partial_match", "conflict"}
        ]
        risks.sort(
            key=lambda item: (
                item.get("importance") == "required",
                float(item.get("weight", 0)),
            ),
            reverse=True,
        )
        selected = (strengths[:2] + risks[:2])[:4]
        if not selected:
            content = "当前岗位报告信息不足，暂时无法生成有针对性的面试问题。"
        else:
            blocks = []
            for index, item in enumerate(selected, start=1):
                if item.get("level") in {"strong_match", "partial_match"}:
                    idea = (
                        "按“场景—职责—方案—结果—复盘”回答，并引用现有项目证据；"
                        "没有记录的指标不要临时编造。"
                    )
                else:
                    idea = self._gap_action(item)
                blocks.append(
                    f"{index}. **问题：请结合实际经历说明你如何满足“{item['requirement']}”？**\n"
                    f"   回答思路：{idea}"
                )
            content = "\n".join(blocks)
        return self._section("面试问题与回答思路", content, selected)

    def build_capability_plan(self) -> dict[str, Any]:
        """按优先级生成 7、30、60 天能力与材料补足计划。"""
        context = self._required_context()
        gaps = [
            item
            for item in context.matches
            if item.get("level") in {"missing", "unverified", "partial_match", "conflict"}
        ]
        gaps.sort(
            key=lambda item: (
                item.get("importance") == "required",
                float(item.get("weight", 0)),
            ),
            reverse=True,
        )
        selected = gaps[:3]
        if not selected:
            content = "当前报告未发现需要优先补足的能力项，可重点准备项目复盘与面试表达。"
        else:
            first = selected[0]
            second = selected[1] if len(selected) > 1 else first
            third = selected[2] if len(selected) > 2 else second
            content = (
                f"- **7 天：核验与补材料**——围绕“{first['requirement']}”确认真实掌握情况，"
                "补充代码、项目说明或可验证成果。\n"
                f"- **30 天：完成针对性实践**——围绕“{second['requirement']}”完成一个可演示案例，"
                "记录目标、方案、取舍和结果。\n"
                f"- **60 天：形成稳定能力证据**——围绕“{third['requirement']}”进行复盘和迭代，"
                "将可靠结论同步到个人档案后重新执行 JD 分析。"
            )
        return self._section("能力补足计划", content, selected)

    def build_material_bundle(self) -> dict[str, Any]:
        """一次生成完整求职材料，供接口预览和报告导出共同使用。"""
        context = self._required_context()
        sections = [
            self.generate_self_introductions(),
            self.select_project_highlights(),
            self.prepare_interview_questions(),
            self.build_capability_plan(),
        ]
        return {
            "analysis_id": context.analysis_id,
            "company_name": context.company_name,
            "job_title": context.job_title,
            "profile_version": context.profile_version,
            "score": context.score,
            "completeness": context.completeness,
            "feasibility": context.feasibility,
            "sections": sections,
        }

    def render_material_report(self) -> str:
        """渲染可下载的 Markdown 报告，并给每条权威证据分配稳定编号。"""
        bundle = self.build_material_bundle()
        report_sections = [
            self.analyze_advantages(),
            self.analyze_risks(),
            self.analyze_gaps(),
            self.recommend_application_strategy(),
            *bundle["sections"],
        ]
        citation_numbers: dict[str, int] = {}
        citations: list[dict[str, Any]] = []
        profile_label = (
            f"v{bundle['profile_version']}"
            if bundle["profile_version"] is not None
            else "未记录"
        )
        body = [
            f"# {bundle['job_title']} · 求职分析与准备报告",
            "",
            f"- 目标公司：{bundle['company_name'] or '未指定'}",
            f"- 个人档案版本：{profile_label}",
            f"- 岗位匹配度：{bundle['score']:.1f}%",
            f"- 证据完整度：{bundle['completeness']:.1f}%",
            f"- 求职可行度：{bundle['feasibility']:.1f}%",
            "",
        ]
        for section in report_sections:
            markers = []
            for evidence in section["evidence"]:
                chunk_id = str(evidence["chunk_id"])
                if chunk_id not in citation_numbers:
                    citation_numbers[chunk_id] = len(citations) + 1
                    citations.append(evidence)
                markers.append(f"[{citation_numbers[chunk_id]}]")
            body.extend([f"## {section['title']}", "", section["content"], ""])
            if markers:
                body.extend([f"> 本节依据：{' '.join(markers)}", ""])

        body.extend(["## 引用资料", ""])
        if not citations:
            body.append("当前材料没有可用的权威引用。")
        for index, evidence in enumerate(citations, start=1):
            location = f"，第 {evidence['page_number']} 页" if evidence.get("page_number") else ""
            body.extend(
                [
                    f"[{index}] **{evidence['filename']}**{location}",
                    f"> {str(evidence['quote']).strip()}",
                    "",
                ]
            )
        body.append("---\n本报告由 ZYW 的 AI 小助理基于已验证资料生成，请在投递前人工确认。")
        return "\n".join(body)

    def _strongest_matches(self, *, limit: int) -> list[dict[str, Any]]:
        """按匹配等级、得分和岗位权重选择最可信的匹配项。"""
        context = self._required_context()
        candidates = [
            item
            for item in context.matches
            if item.get("level") in {"strong_match", "partial_match"}
            and any(self._validated_evidence(source) for source in item.get("evidence", []))
        ]
        candidates.sort(
            key=lambda item: (
                item.get("level") == "strong_match",
                float(item.get("awarded_score", 0)),
                float(item.get("weight", 0)),
            ),
            reverse=True,
        )
        return candidates[:limit]

    @staticmethod
    def _match_phrase(item: dict[str, Any]) -> str:
        """把匹配项转换成不夸大的自我介绍短语。"""
        requirement = str(item.get("requirement", "相关岗位能力"))
        if item.get("level") == "strong_match":
            return f"已有资料能够证明我具备{requirement}"
        return f"我在{requirement}方面具备可迁移的相关经验"

    def _required_context(self) -> CareerContextSnapshot:
        """工具只能在已绑定且版本未过期的上下文中运行。"""
        if self.context is None:
            raise RuntimeError("当前会话尚未绑定岗位分析")
        if self.context.stale:
            raise RuntimeError("个人档案版本已经变化，请重新执行岗位分析")
        return self.context

    def _section(
        self,
        title: str,
        content: str,
        matches: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """构造工具统一输出，并仅携带重新验证过的权威证据。"""
        evidence = []
        seen: set[str] = set()
        for match in matches:
            for source in match.get("evidence", []):
                normalized = self._validated_evidence(source)
                if normalized is None or normalized["chunk_id"] in seen:
                    continue
                seen.add(normalized["chunk_id"])
                evidence.append(normalized)
                if len(evidence) >= 5:
                    break
        return {"title": title, "content": content, "evidence": evidence}

    def _validated_evidence(self, source: dict[str, Any]) -> dict[str, Any] | None:
        """结构化档案校验版本，文档证据重读 SQLite 当前活动正文。"""
        if source.get("document_id") == "candidate-profile":
            if (
                self.context is None
                or self.context.stale
                or self.context.profile_version is None
                or self.context.current_profile_version != self.context.profile_version
            ):
                return None
            return {
                "chunk_id": str(source.get("chunk_id", "")),
                "document_id": "candidate-profile",
                "filename": str(source.get("filename", "结构化个人档案")),
                "quote": str(source.get("quote", "")),
                "page_number": source.get("page_number"),
                "heading": source.get("heading"),
                "index_version": int(source.get("index_version", 0)),
            }
        chunk = self._valid_chunks.get(str(source.get("chunk_id", "")))
        if chunk is None:
            return None
        return {
            "chunk_id": chunk.id,
            "document_id": chunk.document_id,
            "filename": chunk.document.filename,
            "quote": chunk.content,
            "page_number": chunk.page_number,
            "heading": chunk.heading,
            "index_version": chunk.index_version,
        }

    @staticmethod
    def _risk_label(item: dict[str, Any]) -> str:
        level = item.get("level")
        if level == "missing":
            return "现有确认资料明确显示尚未满足，应避免在简历中声称具备。"
        if level == "conflict":
            return "资料存在冲突，需要人工核对后再用于投递。"
        if level == "partial_match":
            return "具备相邻经验，但还不足以完全覆盖岗位要求。"
        return "公开资料没有足够证据，可能影响简历筛选，但不代表实际不具备。"

    @staticmethod
    def _gap_action(item: dict[str, Any]) -> str:
        level = item.get("level")
        requirement_type = item.get("requirement_type")
        if level == "unverified":
            return "先确认本人是否具备；具备则补充可核查项目或经历，不具备则列入学习计划。"
        if level == "missing":
            return "这是已确认的真实缺口，应寻找替代岗位或制定可验证的补足计划。"
        if level == "conflict":
            return "先统一简历、个人档案和项目材料中的表述。"
        if requirement_type == "project_experience":
            return "整理相邻项目的 STAR 案例，明确可迁移部分，不能写成直接经验。"
        if requirement_type == "technical_skill":
            return "准备一个可演示的小项目和技术取舍说明，补强直接证据。"
        return "补充具体成果、职责边界和可核查数据，避免只写宽泛能力。"
