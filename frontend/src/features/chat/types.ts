/** 集中定义访客聊天、会话索引和 SSE 完成状态的数据结构。 */

import type { components } from "@/types/api.generated";
import type { ResumeResource } from "@/features/resume/types";
import type { JdAnalysisArtifact } from "@/features/jd-matching/types";

export type Citation = components["schemas"]["CitationResponse"];
export type ConversationResponse =
  components["schemas"]["ConversationResponse"];

export interface AgentStep {
  node?: string;
  status?: string;
  tool?: string;
  selected_tool?: string;
  attempt?: number;
  [key: string]: unknown;
}

export interface CompletionInfo {
  grounded: boolean;
  degraded: boolean;
  duration_ms: number;
  timings?: Record<string, number>;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  createdAt: string;
  citations?: Citation[];
  resources?: ResumeResource[];
  artifacts?: JdAnalysisArtifact[];
  suggestions?: string[];
  steps?: AgentStep[];
  completion?: CompletionInfo;
  retryQuestion?: string;
  failed?: boolean;
  stopped?: boolean;
  presentation?: "profile";
}

export interface LocalConversation {
  id: string;
  title: string;
  updatedAt: string;
}
