/** 验证持久化消息可以恢复聊天内 JD 报告卡片。 */

import { describe, expect, it } from "vitest";

import { mapConversationMessages } from "./conversation-mapper";
import type { ConversationResponse } from "./types";

describe("mapConversationMessages", () => {
  it("恢复 JD 分析产物引用", () => {
    const conversation = {
      id: "conversation-1",
      title: "JD 岗位匹配",
      created_at: "2026-09-15T00:00:00Z",
      updated_at: "2026-09-15T00:01:00Z",
      messages: [
        {
          id: "message-1",
          role: "assistant",
          content: "岗位匹配已完成。",
          citations_json: null,
          suggestions_json: null,
          resources_json: null,
          artifacts_json: [
            { type: "jd_analysis", analysis_id: "analysis-1" },
          ],
          created_at: "2026-09-15T00:01:00Z",
        },
      ],
    } as ConversationResponse;

    const messages = mapConversationMessages(conversation);

    expect(messages[0].artifacts).toEqual([
      {
        type: "jd_analysis",
        analysisId: "analysis-1",
        status: "completed",
        progress: "正在恢复岗位匹配报告…",
      },
    ]);
  });
});
