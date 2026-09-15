/** 将后端持久化会话安全转换为前端消息，恢复重试问题和引用。 */

import type { ChatMessage, Citation, ConversationResponse } from "./types";
import { isProfileIntroductionQuestion } from "./presentation";
import type { ResumeResource } from "@/features/resume/types";
import type { JdAnalysisArtifact } from "@/features/jd-matching/types";

function isCitation(value: unknown): value is Citation {
  if (!value || typeof value !== "object") return false;
  const item = value as Record<string, unknown>;
  return (
    typeof item.reference_number === "number" &&
    typeof item.chunk_id === "string" &&
    typeof item.document_id === "string" &&
    typeof item.filename === "string" &&
    typeof item.quote === "string" &&
    typeof item.index_version === "number"
  );
}

function isResumeResource(value: unknown): value is ResumeResource {
  if (!value || typeof value !== "object") return false;
  const item = value as Record<string, unknown>;
  return (
    item.type === "resume" &&
    typeof item.title === "string" &&
    typeof item.filename === "string" &&
    typeof item.download_url === "string" &&
    typeof item.preview_url === "string"
  );
}

function isJdArtifactReference(
  value: unknown,
): value is { type: "jd_analysis"; analysis_id: string } {
  if (!value || typeof value !== "object") return false;
  const item = value as Record<string, unknown>;
  return item.type === "jd_analysis" && typeof item.analysis_id === "string";
}

export function mapConversationMessages(
  conversation: ConversationResponse,
): ChatMessage[] {
  let latestQuestion: string | undefined;
  return conversation.messages.flatMap((message) => {
    if (message.role !== "user" && message.role !== "assistant") return [];
    if (message.role === "user") latestQuestion = message.content;
    const artifacts: JdAnalysisArtifact[] = (
      message.artifacts_json ?? []
    )
      .filter(isJdArtifactReference)
      .map((item) => ({
        type: "jd_analysis",
        analysisId: item.analysis_id,
        status: "completed",
        progress: "正在恢复岗位匹配报告…",
      }));
    return [
      {
        id: message.id,
        role: message.role,
        content: message.content,
        createdAt: message.created_at,
        citations: (message.citations_json ?? []).filter(isCitation),
        resources: (message.resources_json ?? []).filter(isResumeResource),
        artifacts,
        suggestions: (message.suggestions_json ?? []).filter(
          (item): item is string =>
            typeof item === "string" && Boolean(item.trim()),
        ),
        retryQuestion:
          message.role === "assistant" ? latestQuestion : undefined,
        presentation:
          message.role === "assistant" &&
          latestQuestion &&
          isProfileIntroductionQuestion(latestQuestion)
            ? "profile"
            : undefined,
      },
    ];
  });
}
