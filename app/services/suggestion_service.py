"""根据公开知识主题和当前会话生成可持久化的动态推荐问题。"""

import hashlib
import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from sqlalchemy.orm import Session

from app.agent.prompts import SUGGESTION_SYSTEM_PROMPT
from app.core.config import Settings, get_settings
from app.knowledge.rag import message_text
from app.llm.factory import create_suggestion_model
from app.storage.repositories.conversations import ConversationRepository
from app.storage.repositories.documents import DocumentRepository
from app.storage.repositories.suggestions import SuggestionRepository

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class SuggestionResult:
    """一次推荐生成的文本和来源。"""

    suggestions: list[str]
    source: str


class SuggestionService:
    """独立于 Agent 工具循环生成推荐问题，失败时使用确定性候选。"""

    def __init__(
        self,
        session: Session,
        settings: Settings | None = None,
        *,
        model: BaseChatModel | None = None,
    ):
        """绑定数据库、配置和可选测试模型。"""
        self.session = session
        self.settings = settings or get_settings()
        self.model = model
        self.documents = DocumentRepository(session)
        self.conversations = ConversationRepository(session)
        self.repository = SuggestionRepository(session)

    def get_empty_suggestions(self) -> SuggestionResult:
        """根据当前公开文档版本生成首页空状态推荐并按版本缓存。"""
        documents = [
            document
            for document in self.documents.list(limit=100, public_only=True)
            if document.status == "ready"
        ]
        source_parts = sorted(
            f"{item.id}:{item.active_index_version}:{item.filename}" for item in documents
        )
        signature = hashlib.sha256("|".join(source_parts).encode("utf-8")).hexdigest()
        cache_key = f"empty:{signature[:32]}"
        cached = self.repository.get_cache(cache_key)
        if cached is not None:
            return SuggestionResult(
                suggestions=self._normalize(cached.suggestions_json),
                source="cache",
            )

        topics = [Path(item.filename).stem for item in documents[:12]]
        fallback = self._empty_fallback(topics)
        suggestions, source = self._generate(
            mode="knowledge_base",
            current_question="",
            history=[],
            answer="",
            citation_topics=[],
            document_topics=topics,
            fallback=fallback,
        )
        self.repository.save_cache(cache_key, signature, suggestions)
        self.session.commit()
        return SuggestionResult(suggestions=suggestions, source=source)

    def generate_for_answer(
        self,
        conversation_id: str,
        *,
        answer_mode: str,
        citations: list[dict[str, Any]],
    ) -> SuggestionResult:
        """根据最近对话和引用生成追问，并保存到最后一条助手消息。"""
        messages = self.conversations.list_messages(
            conversation_id,
            limit=max(2, self.settings.suggestion_history_messages + 1),
        )
        assistant_message = next(
            (message for message in reversed(messages) if message.role == "assistant"),
            None,
        )
        if assistant_message is None:
            return SuggestionResult(suggestions=[], source="fallback")
        stored = self._normalize(assistant_message.suggestions_json or [])
        if stored:
            return SuggestionResult(suggestions=stored, source="stored")

        history = [(message.role, message.content) for message in messages[:-1]]
        current_question = next(
            (content for role, content in reversed(history) if role == "user"),
            "",
        )
        citation_topics = self._citation_topics(citations)
        document_topics = [
            Path(document.filename).stem
            for document in self.documents.list(limit=12, public_only=True)
            if document.status == "ready"
        ]
        fallback = self._answer_fallback(
            current_question=current_question,
            answer_mode=answer_mode,
            citation_topics=citation_topics,
            document_topics=document_topics,
        )
        suggestions, source = self._generate(
            mode=answer_mode,
            current_question=current_question,
            history=history,
            answer=assistant_message.content,
            citation_topics=citation_topics,
            document_topics=document_topics,
            fallback=fallback,
        )
        self.repository.save_message_suggestions(assistant_message, suggestions)
        self.session.commit()
        return SuggestionResult(suggestions=suggestions, source=source)

    def _generate(
        self,
        *,
        mode: str,
        current_question: str,
        history: list[tuple[str, str]],
        answer: str,
        citation_topics: list[str],
        document_topics: list[str],
        fallback: list[str],
    ) -> tuple[list[str], str]:
        """调用小模型生成结构化问题，任何异常都安全回退。"""
        try:
            model = self.model or create_suggestion_model(self.settings)
            payload = {
                "mode": mode,
                "current_question": self._compact(current_question, 300),
                "recent_history": [
                    {"role": role, "content": self._compact(content, 400)}
                    for role, content in history[-self.settings.suggestion_history_messages :]
                ],
                "answer": self._compact(answer, 900),
                "citation_topics": citation_topics[:8],
                "public_document_topics": document_topics[:12],
            }
            response = model.invoke(
                [
                    SystemMessage(content=SUGGESTION_SYSTEM_PROMPT),
                    HumanMessage(content=json.dumps(payload, ensure_ascii=False)),
                ]
            )
            generated = self._parse_model_output(message_text(response))
            suggestions = self._fill(generated, fallback, current_question)
            return suggestions, "generated"
        except Exception as exc:
            logger.info("推荐问题生成已回退", extra={"error_type": type(exc).__name__})
            return self._fill([], fallback, current_question), "fallback"

    def _parse_model_output(self, content: str) -> list[str]:
        """兼容代码围栏或对象包装，但最终只接受字符串列表。"""
        normalized = content.strip().removeprefix("```json").removeprefix("```")
        normalized = normalized.removesuffix("```").strip()
        match = re.search(r"\[[\s\S]*\]", normalized)
        if match is None:
            return []
        parsed = json.loads(match.group(0))
        return self._normalize(parsed if isinstance(parsed, list) else [])

    def _fill(
        self,
        generated: list[str],
        fallback: list[str],
        current_question: str,
    ) -> list[str]:
        """去重、过滤当前问题并用确定性候选补足目标数量。"""
        current_key = self._comparison_key(current_question)
        result: list[str] = []
        for item in [*generated, *fallback]:
            question = self._clean_question(item)
            key = self._comparison_key(question)
            if (
                not question
                or key == current_key
                or any(self._comparison_key(old) == key for old in result)
            ):
                continue
            result.append(question)
            if len(result) >= self.settings.suggestion_count:
                break
        return result

    def _empty_fallback(self, topics: list[str]) -> list[str]:
        """没有模型结果时，根据公开文档名称构造首页问题。"""
        candidates: list[str] = []
        for topic in topics[:3]:
            short = self._compact(topic, 18)
            candidates.extend(
                [f"可以介绍一下{short}吗？", f"ZYW 在{short}中做了什么？"]
            )
        return candidates or [
            "可以介绍一下 ZYW 吗？",
            "ZYW 有哪些技术能力？",
            "这个 AI 助理如何工作？",
        ]

    def _answer_fallback(
        self,
        *,
        current_question: str,
        answer_mode: str,
        citation_topics: list[str],
        document_topics: list[str],
    ) -> list[str]:
        """根据当前上下文生成不会阻塞回答的降级候选。"""
        if answer_mode == "casual":
            topic = self._compact(current_question.rstrip("？?。！!"), 18) or "刚才的话题"
            return [
                f"可以继续聊聊{topic}吗？",
                f"换个角度怎么看{topic}？",
                "你还可以陪我聊些什么？",
            ]
        if answer_mode == "career_advisor":
            return [
                "这个岗位我的核心优势是什么？",
                "我需要优先补足哪些能力缺口？",
                "针对这个岗位应该如何准备面试？",
            ]
        topics = [*citation_topics, *document_topics]
        candidates = [f"可以进一步介绍{self._compact(topic, 18)}吗？" for topic in topics[:3]]
        return candidates or self._empty_fallback([])

    @staticmethod
    def _citation_topics(citations: list[dict[str, Any]]) -> list[str]:
        """仅提取引用的标题和文件名，不把大段正文发送给推荐模型。"""
        topics: list[str] = []
        for citation in citations:
            topic = citation.get("heading") or Path(str(citation.get("filename", ""))).stem
            if topic and str(topic) not in topics:
                topics.append(str(topic))
        return topics

    @staticmethod
    def _normalize(values: list[Any]) -> list[str]:
        """过滤非字符串和空白项目。"""
        return [value.strip() for value in values if isinstance(value, str) and value.strip()]

    @staticmethod
    def _compact(value: str, limit: int) -> str:
        """压缩空白并限制发送给模型的上下文长度。"""
        return re.sub(r"\s+", " ", value).strip()[:limit]

    @staticmethod
    def _clean_question(value: str) -> str:
        """清理模型可能附带的编号和引号，并补全问号。"""
        cleaned = re.sub(r"^\s*\d+[.、)]\s*", "", value).strip(" \t\r\n\"'“”")
        cleaned = cleaned[:48]
        if cleaned and cleaned[-1] not in "？?！!。":
            cleaned += "？"
        return cleaned

    @staticmethod
    def _comparison_key(value: str) -> str:
        """生成忽略空白和标点的去重键。"""
        return re.sub(r"[\s，。！？、,.!?：:；;‘’“”\"']+", "", value).lower()
