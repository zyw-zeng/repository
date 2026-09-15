/** 验证从创建会话到流式回答、引用、推荐追问和本地索引的完整前端链路。 */

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { apiClient } from "@/lib/api-client";
import { readEventStream } from "@/lib/stream-client";

import { ChatPanel } from "./chat-panel";
import type { SpiritStatus } from "./ai-spirit";

vi.mock("@/lib/api-client", () => ({
  apiClient: { get: vi.fn(), post: vi.fn() },
}));

vi.mock("@/lib/stream-client", () => ({
  readEventStream: vi.fn(),
}));

describe("流式聊天", () => {
  beforeEach(() => {
    window.localStorage.clear();
    vi.clearAllMocks();
    vi.mocked(apiClient.get).mockResolvedValue({
      data: {
        suggestions: [
          "介绍一下 ZYW 的技术能力",
          "这个 AI Agent 项目如何工作？",
          "项目如何保证引用可靠？",
        ],
        source: "cache",
      },
    });
  });

  it("展示完成状态、引用和推荐追问，并记录本地会话", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({
      data: {
        id: "conversation-1",
        title: "介绍一下 ZYW 的技术能力",
        messages: [],
        created_at: "2026-09-13T00:00:00Z",
        updated_at: "2026-09-13T00:00:00Z",
      },
    });
    vi.mocked(readEventStream).mockReturnValue(
      (async function* () {
        yield { event: "run_started", data: { request_id: "request-1" } };
        yield {
          event: "agent_step",
          data: { node: "classify_intent", status: "completed" },
        };
        yield {
          event: "timing",
          data: { stage: "router", duration_ms: 2 },
        };
        yield {
          event: "answer_delta",
          data: { delta: "ZYW 熟悉 AI Agent。" },
        };
        yield {
          event: "answer_final",
          data: { answer: "ZYW 熟悉 AI Agent。" },
        };
        yield {
          event: "citations",
          data: [
            {
              reference_number: 1,
              chunk_id: "chunk-1",
              document_id: "document-1",
              filename: "项目说明.md",
              quote: "项目使用可靠 RAG。",
              page_number: null,
              heading: "技术能力",
              index_version: 1,
            },
          ],
        };
        yield {
          event: "resources",
          data: [
            {
              type: "resume",
              title: "曾有为｜AI Agent 应用开发",
              description: "包含 AI Agent、RAG、全栈开发与代表项目经历",
              filename: "曾有为-AI-Agent应用开发.pdf",
              version: "2026.09",
              updated_at: "2026-09-14T00:00:00Z",
              size_bytes: 195788,
              media_type: "application/pdf",
              download_url: "/api/v1/resume/download",
              preview_url: "/api/v1/resume/preview",
            },
          ],
        };
        yield {
          event: "followup_suggestions",
          data: {
            suggestions: [
              "ZYW 还做过哪些 Agent 项目？",
              "这个项目如何验证引用？",
              "可以介绍相关技术栈吗？",
            ],
            source: "generated",
          },
        };
        yield {
          event: "completed",
          data: {
            grounded: true,
            degraded: false,
            duration_ms: 1200,
            timings: { router_ms: 2, generation_ms: 900, total_ms: 1200 },
          },
        };
      })(),
    );

    render(<ChatPanel status="idle" onStatusChange={vi.fn()} />);
    await userEvent.click(
      await screen.findByRole("button", { name: "介绍一下 ZYW 的技术能力" }),
    );

    expect(await screen.findByText("ZYW 熟悉 AI Agent。")).toBeInTheDocument();
    expect(screen.getByText("已关联引用")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "朗读" })).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "下载 PDF" }),
    ).toHaveAttribute("href", "/api/backend/resume/download");
    expect(
      screen.getByRole("link", { name: "在线查看" }),
    ).toHaveAttribute("href", "/api/backend/resume/preview");
    expect(document.querySelectorAll("time")).toHaveLength(2);
    expect(
      Array.from(document.querySelectorAll("time")).every((item) =>
        Boolean(item.getAttribute("datetime")),
      ),
    ).toBe(true);
    const sourceSummary = screen.getByText("1 个引用来源").closest("summary");
    expect(sourceSummary?.parentElement).not.toHaveAttribute("open");
    await userEvent.click(sourceSummary!);
    const processSummary = screen.getByText("回答过程").closest("summary");
    await userEvent.click(processSummary!);
    expect(screen.getByText("阶段耗时")).toBeInTheDocument();
    expect(screen.getByText("路由：2 ms")).toBeInTheDocument();
    expect(screen.getByText(/项目说明\.md/)).toBeInTheDocument();
    expect(screen.getByText("接着了解")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "这个项目如何验证引用？" }),
    ).toBeInTheDocument();
    expect(window.localStorage.getItem("zyw_active_conversation_v1")).toBe(
      "conversation-1",
    );
  });

  it("刷新后根据本地索引恢复后端持久化消息", async () => {
    window.localStorage.setItem(
      "zyw_conversation_index_v1",
      JSON.stringify([
        {
          id: "conversation-saved",
          title: "已保存的问题",
          updatedAt: "2026-09-13T00:00:00Z",
        },
      ]),
    );
    window.localStorage.setItem(
      "zyw_active_conversation_v1",
      "conversation-saved",
    );
    vi.mocked(apiClient.get).mockImplementation(async (path: string) => ({
      data:
        path === "/suggestions"
          ? { suggestions: [], source: "cache" }
          : {
              id: "conversation-saved",
              title: "已保存的问题",
              messages: [
                {
                  id: "message-user",
                  role: "user",
                  content: "介绍一下 ZYW",
                  citations_json: null,
                  created_at: "2026-09-13T00:00:00Z",
                },
                {
                  id: "message-assistant",
                  role: "assistant",
                  content: "已经恢复的回答",
                  citations_json: [],
                  suggestions_json: ["可以继续了解这个项目吗？"],
                  resources_json: [
                    {
                      type: "resume",
                      title: "曾有为｜AI Agent 应用开发",
                      description: "AI Agent 项目简历",
                      filename: "曾有为-AI-Agent应用开发.pdf",
                      version: "2026.09",
                      updated_at: "2026-09-14T00:00:00Z",
                      size_bytes: 195788,
                      media_type: "application/pdf",
                      download_url: "/api/v1/resume/download",
                      preview_url: "/api/v1/resume/preview",
                    },
                  ],
                  created_at: "2026-09-13T00:00:01Z",
                },
              ],
              created_at: "2026-09-13T00:00:00Z",
              updated_at: "2026-09-13T00:00:01Z",
            },
    }));

    render(<ChatPanel status="idle" onStatusChange={vi.fn()} />);

    expect(await screen.findByText("已经恢复的回答")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "认识一下 ZYW" }),
    ).toBeInTheDocument();
    expect(document.querySelectorAll("time")).toHaveLength(2);
    expect(
      screen.getByRole("button", { name: "可以继续了解这个项目吗？" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "下载 PDF" })).toBeInTheDocument();
    expect(apiClient.get).toHaveBeenCalledWith(
      "/conversations/conversation-saved",
    );
  });

  it("自动朗读期间立即展示已经到达的推荐问题", async () => {
    window.localStorage.setItem(
      "zyw_conversation_index_v1",
      JSON.stringify([
        {
          id: "conversation-speaking",
          title: "朗读中的会话",
          updatedAt: "2026-09-13T00:00:01Z",
        },
      ]),
    );
    window.localStorage.setItem(
      "zyw_active_conversation_v1",
      "conversation-speaking",
    );
    vi.mocked(apiClient.get).mockImplementation(async (path: string) => ({
      data:
        path === "/suggestions"
          ? { suggestions: [], source: "cache" }
          : {
              id: "conversation-speaking",
              title: "朗读中的会话",
              messages: [
                {
                  id: "message-user-speaking",
                  role: "user",
                  content: "介绍项目",
                  citations_json: null,
                  suggestions_json: null,
                  created_at: "2026-09-13T00:00:00Z",
                },
                {
                  id: "message-assistant-speaking",
                  role: "assistant",
                  content: "这是项目介绍。",
                  citations_json: [],
                  suggestions_json: ["项目还有哪些技术细节？"],
                  created_at: "2026-09-13T00:00:01Z",
                },
              ],
              created_at: "2026-09-13T00:00:00Z",
              updated_at: "2026-09-13T00:00:01Z",
            },
    }));

    render(<ChatPanel status="speaking" onStatusChange={vi.fn()} />);

    expect(
      await screen.findByRole("button", { name: "项目还有哪些技术细节？" }),
    ).toBeInTheDocument();
  });

  it("停止按钮先通知服务端取消运行，再关闭本地流", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({
      data: {
        id: "conversation-cancel",
        title: "取消测试",
        messages: [],
        created_at: "2026-09-13T00:00:00Z",
        updated_at: "2026-09-13T00:00:00Z",
      },
    });
    vi.mocked(readEventStream).mockImplementation(
      (_path, _body, signal, requestId) =>
        (async function* () {
          yield { event: "run_started", data: { request_id: requestId } };
          await new Promise<void>((_resolve, reject) => {
            signal?.addEventListener(
              "abort",
              () => reject(new DOMException("回答已停止", "AbortError")),
              { once: true },
            );
          });
        })(),
    );

    function StatefulChatPanel() {
      const [status, setStatus] = useState<SpiritStatus>("idle");
      return <ChatPanel status={status} onStatusChange={setStatus} />;
    }

    render(<StatefulChatPanel />);
    await userEvent.click(
      await screen.findByRole("button", { name: "介绍一下 ZYW 的技术能力" }),
    );
    await userEvent.click(
      await screen.findByRole("button", { name: "停止回答" }),
    );

    expect(await screen.findByText("回答已停止。")).toBeInTheDocument();
    expect(apiClient.post).toHaveBeenCalledWith(
      expect.stringMatching(
        /^\/conversations\/conversation-cancel\/runs\/.+\/cancel$/,
      ),
    );
  });
});
