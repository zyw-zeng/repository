"use client";

/** 实现会话恢复、可靠 SSE 流、Agent 进度、引用、复制和失败重试。 */

import {
  Activity,
  ArrowUpRight,
  BookOpen,
  Bot,
  BriefcaseBusiness,
  CheckCircle2,
  ChevronDown,
  CircleAlert,
  Clock3,
  Copy,
  LoaderCircle,
  Pause,
  Play,
  Plus,
  RotateCcw,
  Send,
  ShieldCheck,
  Sparkles,
  Square,
  Volume2,
  UserRound,
  WifiOff,
} from "lucide-react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import rehypeSanitize from "rehype-sanitize";
import remarkGfm from "remark-gfm";
import { toast } from "sonner";

import { BrandMark } from "@/components/brand/brand-mark";
import { JdAnalysisCard } from "@/components/jd-matching/jd-analysis-card";
import { ResumeDownloadCard } from "@/components/resume/resume-download-card";
import { ResumeEntry } from "@/components/resume/resume-entry";
import { SPIRIT_QUESTION_EVENT } from "@/components/spirit/spirit-events";
import { readSpiritAppearance } from "@/components/spirit/spirit-storage";
import { ThemeToggle } from "@/components/theme/theme-toggle";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { mapConversationMessages } from "@/features/chat/conversation-mapper";
import {
  clearActiveConversation,
  createConversationTitle,
  readActiveConversation,
  readConversationIndex,
  removeConversation,
  saveActiveConversation,
  saveConversation,
} from "@/features/chat/conversation-storage";
import type {
  AgentStep,
  ChatMessage,
  Citation,
  CompletionInfo,
  ConversationResponse,
  LocalConversation,
} from "@/features/chat/types";
import {
  isProfileIntroductionQuestion,
  profileAnswerContent,
} from "@/features/chat/presentation";
import { useSpeechPlayer } from "@/features/tts/use-speech-player";
import type { ResumeResource } from "@/features/resume/types";
import type {
  JdAnalysisArtifact,
  JdAnalysisReport,
} from "@/features/jd-matching/types";
import { apiClient } from "@/lib/api-client";
import { readEventStream } from "@/lib/stream-client";
import { cn } from "@/lib/utils";

import { ConversationDrawer } from "./conversation-drawer";
import type { SpiritStatus } from "./ai-spirit";
import type { FormEvent } from "react";

interface ChatPanelProps {
  status: SpiritStatus;
  onStatusChange: (status: SpiritStatus) => void;
  displayMode?: "desktop" | "mobile";
}

interface CompletedEvent extends CompletionInfo {
  conversation_id: string;
  request_id: string;
  run_id: string;
}

interface SuggestionPayload {
  suggestions: string[];
  source: "cache" | "generated" | "fallback" | "stored";
}

const stepLabels: Record<string, string> = {
  classify_intent: "正在理解问题意图",
  execute_tool: "正在调用知识库工具",
  rewrite_for_retry: "正在优化检索问题",
  career_plan: "正在理解求职咨询目标",
  career_tool: "正在分析岗位证据",
  career_compose: "正在整理求职建议",
};

const TYPEWRITER_BATCH_SIZE = 3;
const TYPEWRITER_INTERVAL_MS = 20;

const timingLabels: Record<string, string> = {
  router_ms: "路由",
  rewrite_ms: "改写",
  retrieval_ms: "检索",
  context_ms: "上下文",
  generation_ms: "回答",
  retry_rewrite_ms: "重试改写",
  career_tool_1_ms: "求职分析 1",
  career_tool_2_ms: "求职分析 2",
  career_tool_3_ms: "求职分析 3",
  career_tool_4_ms: "求职分析 4",
};

function createMessageId() {
  return globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random()}`;
}

function stepDescription(step: AgentStep): string {
  const base = stepLabels[step.node ?? ""] ?? "正在处理问题";
  const tool = step.tool ?? step.selected_tool;
  return tool ? `${base} · ${tool}` : base;
}

function formatMessageTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  const today = new Date();
  const isToday =
    date.getFullYear() === today.getFullYear() &&
    date.getMonth() === today.getMonth() &&
    date.getDate() === today.getDate();
  return new Intl.DateTimeFormat("zh-CN", {
    ...(isToday ? {} : { month: "numeric", day: "numeric" }),
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(date);
}

function wait(milliseconds: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) {
      reject(new DOMException("回答已停止", "AbortError"));
      return;
    }
    const timer = window.setTimeout(() => {
      signal?.removeEventListener("abort", handleAbort);
      resolve();
    }, milliseconds);
    function handleAbort() {
      window.clearTimeout(timer);
      reject(new DOMException("回答已停止", "AbortError"));
    }
    signal?.addEventListener("abort", handleAbort, { once: true });
  });
}

function AnswerMarkdown({ content }: { content: string }) {
  return (
    <div className="answer-content">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeSanitize]}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}

function ProfileIntroduction({ content }: { content: string }) {
  return (
    <div className="profile-introduction overflow-hidden rounded-[1.4rem]">
      <div className="border-border/50 relative overflow-hidden border-b px-5 py-5 sm:px-6">
        <div
          aria-hidden="true"
          className="bg-brand-indigo/20 absolute -top-16 -right-10 size-40 rounded-full blur-3xl"
        />
        <div className="relative flex items-start gap-4">
          <div className="from-brand-cyan/85 via-brand-indigo to-brand-violet grid size-12 shrink-0 place-items-center rounded-2xl bg-gradient-to-br text-white shadow-lg shadow-indigo-500/15">
            <Sparkles className="size-5" />
          </div>
          <div className="min-w-0">
            <p className="text-primary text-[11px] font-semibold tracking-[0.16em] uppercase">
              人物介绍
            </p>
            <h2 className="mt-1 text-xl font-semibold tracking-tight sm:text-2xl">
              认识一下 ZYW
            </h2>
            <p className="text-muted-foreground mt-1 text-xs leading-5 sm:text-sm">
              从职业经历、能力方向和代表项目认识曾有为
            </p>
          </div>
        </div>
      </div>
      <div className="px-5 py-5 sm:px-6 sm:py-6">
        <AnswerMarkdown content={profileAnswerContent(content)} />
      </div>
    </div>
  );
}

function CitationDisclosure({ citations }: { citations: Citation[] }) {
  return (
    <details className="source-disclosure border-border/55 mt-3 border-t pt-3">
      <summary className="group/source text-muted-foreground hover:text-foreground flex cursor-pointer list-none items-center justify-between gap-3 rounded-xl px-1 py-1.5 text-xs transition-colors [&::-webkit-details-marker]:hidden">
        <span className="flex items-center gap-2">
          <span className="bg-primary/10 text-primary grid size-7 place-items-center rounded-lg">
            <BookOpen className="size-3.5" />
          </span>
          <span>
            <strong className="text-foreground font-medium">
              {citations.length} 个引用来源
            </strong>
            <span className="ml-2">点击展开核查</span>
          </span>
        </span>
        <ChevronDown className="size-4 transition-transform group-open/source:rotate-180" />
      </summary>
      <div className="mt-2 grid gap-2">
        {citations.map((citation) => (
          <details
            key={`${citation.reference_number}-${citation.chunk_id}`}
            className="bg-background/55 border-border/40 min-w-0 overflow-hidden rounded-xl border px-3 py-2.5"
          >
            <summary className="cursor-pointer list-none text-xs font-medium [&::-webkit-details-marker]:hidden">
              <span className="flex items-center gap-2">
                <span className="bg-primary/10 text-primary rounded-md px-1.5 py-0.5 tabular-nums">
                  [{citation.reference_number}]
                </span>
                <span className="min-w-0 flex-1 truncate">
                  {citation.filename}
                </span>
                <ChevronDown className="text-muted-foreground size-3.5" />
              </span>
            </summary>
            <p className="text-muted-foreground mt-2 text-[11px]">
              {[
                citation.heading,
                citation.page_number
                  ? `第 ${citation.page_number} 页`
                  : undefined,
              ]
                .filter(Boolean)
                .join(" · ")}
            </p>
            <p className="text-muted-foreground mt-2 text-xs leading-6">
              {citation.quote}
            </p>
          </details>
        ))}
      </div>
    </details>
  );
}

function ProcessDisclosure({
  steps,
  completion,
}: {
  steps: AgentStep[];
  completion?: CompletionInfo;
}) {
  const timingEntries = Object.entries(completion?.timings ?? {}).filter(
    ([name]) => name !== "total_ms",
  );
  return (
    <details className="process-disclosure border-border/55 mt-3 border-t pt-3 text-xs">
      <summary className="group/process text-muted-foreground hover:text-foreground flex cursor-pointer list-none items-center justify-between gap-3 rounded-xl px-1 py-1.5 transition-colors [&::-webkit-details-marker]:hidden">
        <span className="flex min-w-0 items-center gap-2">
          <span className="bg-secondary text-secondary-foreground grid size-7 shrink-0 place-items-center rounded-lg">
            <Activity className="size-3.5" />
          </span>
          <span className="text-foreground font-medium">回答过程</span>
          <span className="truncate">
            {steps.length ? `${steps.length} 个步骤` : "处理完成"}
            {completion
              ? ` · ${(completion.duration_ms / 1000).toFixed(1)} 秒`
              : " · 正在执行"}
          </span>
        </span>
        <ChevronDown className="size-4 shrink-0 transition-transform group-open/process:rotate-180" />
      </summary>
      <div className="bg-background/45 border-border/35 mt-2 space-y-3 rounded-xl border p-3">
        {steps.length > 0 && (
          <ol className="space-y-2">
            {steps.map((step, index) => (
              <li key={index} className="flex items-start gap-2">
                <span className="bg-primary/10 text-primary mt-0.5 grid size-5 shrink-0 place-items-center rounded-full text-[10px] tabular-nums">
                  {index + 1}
                </span>
                <span className="text-muted-foreground leading-5">
                  {stepDescription(step)}
                </span>
              </li>
            ))}
          </ol>
        )}
        {completion && (
          <div className="border-border/40 flex flex-wrap items-center gap-2 border-t pt-3 first:border-t-0 first:pt-0">
            <Badge variant="outline" className="rounded-full">
              {completion.degraded ? (
                <>
                  <CircleAlert /> 已降级完成
                </>
              ) : completion.grounded ? (
                <>
                  <ShieldCheck /> 已关联引用
                </>
              ) : (
                <>
                  <CheckCircle2 /> 已完成
                </>
              )}
            </Badge>
            {timingEntries.length > 0 && (
              <div className="text-muted-foreground flex flex-wrap gap-x-3 gap-y-1">
                <span className="flex items-center gap-1 font-medium">
                  <Clock3 className="size-3" /> 阶段耗时
                </span>
                {timingEntries.map(([name, value]) => (
                  <span key={name}>
                    {timingLabels[name] ?? name}：{value} ms
                  </span>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </details>
  );
}

function SuggestionChips({
  suggestions,
  onSelect,
  reduceMotion,
}: {
  suggestions: string[];
  onSelect: (suggestion: string) => void;
  reduceMotion: boolean | null;
}) {
  return (
    <div className="flex max-w-full flex-wrap gap-2">
      {suggestions.map((suggestion, index) => (
        <motion.button
          key={suggestion}
          type="button"
          initial={reduceMotion ? false : { opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: index * 0.06 }}
          whileHover={reduceMotion ? undefined : { y: -2 }}
          onClick={() => onSelect(suggestion)}
          className="group/suggestion bg-background/55 hover:border-primary/45 hover:bg-primary/8 inline-flex max-w-full items-center gap-2 rounded-full border px-3 py-2 text-left text-xs leading-5 shadow-sm transition-colors"
        >
          <Sparkles className="text-primary size-3.5 shrink-0" />
          <span className="truncate sm:whitespace-normal">{suggestion}</span>
          <ArrowUpRight className="text-muted-foreground group-hover/suggestion:text-primary size-3.5 shrink-0 transition-colors" />
        </motion.button>
      ))}
    </div>
  );
}

export function ChatPanel({
  status,
  onStatusChange,
  displayMode = "desktop",
}: ChatPanelProps) {
  const isMobile = displayMode === "mobile";
  const reduceMotion = useReducedMotion();
  const [conversationId, setConversationId] = useState<string>();
  const [conversations, setConversations] = useState<LocalConversation[]>(() =>
    readConversationIndex(),
  );
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [question, setQuestion] = useState("");
  const [inputMode, setInputMode] = useState<"chat" | "jd">("chat");
  const [runProgress, setRunProgress] = useState<string>();
  const [connectionError, setConnectionError] = useState<string>();
  const [emptySuggestions, setEmptySuggestions] = useState<string[]>([]);
  const [suggestionsLoading, setSuggestionsLoading] = useState(true);
  const [activeAssistantId, setActiveAssistantId] = useState<string>();
  const [isRestoring, setIsRestoring] = useState(false);
  const [isOnline, setIsOnline] = useState(true);
  const abortController = useRef<AbortController | null>(null);
  const activeRun = useRef<{
    kind: "chat" | "jd";
    conversationId: string;
    requestId: string;
  } | null>(null);
  const sendQuestionRef = useRef<(question: string) => void>(() => undefined);
  const messageEnd = useRef<HTMLDivElement | null>(null);
  const speech = useSpeechPlayer(onStatusChange);
  // 语音播放是回答完成后的独立体验，不应锁住聊天、推荐问题或新一轮提问。
  const isBusy = status === "thinking" || status === "answering" || isRestoring;

  const restoreConversation = useCallback(
    async (item: LocalConversation, quiet = false) => {
      setIsRestoring(true);
      setConnectionError(undefined);
      onStatusChange("thinking");
      try {
        const response = await apiClient.get<ConversationResponse>(
          `/conversations/${item.id}`,
        );
        setConversationId(response.data.id);
        setMessages(mapConversationMessages(response.data));
        saveActiveConversation(response.data.id);
        setConversations(
          saveConversation({
            id: response.data.id,
            title: item.title || response.data.title,
            updatedAt: response.data.updated_at,
          }),
        );
        onStatusChange("idle");
      } catch {
        setConversations(removeConversation(item.id));
        setConversationId(undefined);
        setMessages([]);
        onStatusChange(quiet ? "idle" : "error");
        if (!quiet) toast.error("这个会话已无法恢复，已从本机列表移除。");
      } finally {
        setIsRestoring(false);
      }
    },
    [onStatusChange],
  );

  // 页面刷新后只恢复当前浏览器记录的会话，不读取其他访客的全局会话。
  useEffect(() => {
    const localIndex = readConversationIndex();
    const activeId = readActiveConversation();
    const activeItem = localIndex.find((item) => item.id === activeId);
    // 延后一拍执行远程恢复，让首次客户端渲染先稳定下来。
    const restoreTimer = activeItem
      ? window.setTimeout(() => void restoreConversation(activeItem, true), 0)
      : undefined;
    return () => {
      if (restoreTimer !== undefined) window.clearTimeout(restoreTimer);
    };
  }, [restoreConversation]);

  // 监听浏览器网络状态，离线时保留输入内容并阻止无效请求。
  useEffect(() => {
    const updateOnlineState = () => setIsOnline(window.navigator.onLine);
    updateOnlineState();
    window.addEventListener("online", updateOnlineState);
    window.addEventListener("offline", updateOnlineState);
    return () => {
      window.removeEventListener("online", updateOnlineState);
      window.removeEventListener("offline", updateOnlineState);
    };
  }, []);

  // 空状态推荐由公开知识库主题生成；读取失败不影响用户直接输入问题。
  useEffect(() => {
    let active = true;
    void apiClient
      .get<SuggestionPayload>("/suggestions")
      .then((response) => {
        if (active) setEmptySuggestions(response.data.suggestions);
      })
      .catch(() => {
        if (active) setEmptySuggestions([]);
      })
      .finally(() => {
        if (active) setSuggestionsLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  // 桌面端与移动端切换导致组件卸载时，同时停止浏览器流和服务端任务。
  useEffect(
    () => () => {
      const run = activeRun.current;
      if (run) {
        const cancelPath =
          run.kind === "jd"
            ? `/jd-analyses/runs/${run.requestId}/cancel`
            : `/conversations/${run.conversationId}/runs/${run.requestId}/cancel`;
        void apiClient.post(cancelPath).catch(() => undefined);
      }
      abortController.current?.abort();
    },
    [],
  );

  // 流式文本增长时保持最新内容可见，减少动态效果时取消平滑滚动。
  useEffect(() => {
    messageEnd.current?.scrollIntoView({
      behavior: reduceMotion ? "auto" : "smooth",
      block: "end",
    });
  }, [messages, reduceMotion, runProgress]);

  async function appendAnswerWithTypewriter(
    messageId: string,
    delta: string,
    signal: AbortSignal,
  ) {
    const characters = Array.from(delta);
    const batchSize = reduceMotion
      ? characters.length || 1
      : TYPEWRITER_BATCH_SIZE;
    for (let start = 0; start < characters.length; start += batchSize) {
      if (signal.aborted) throw new DOMException("回答已停止", "AbortError");
      const text = characters.slice(start, start + batchSize).join("");
      setMessages((current) =>
        current.map((message) =>
          message.id === messageId
            ? { ...message, content: message.content + text }
            : message,
        ),
      );
      if (!reduceMotion && start + batchSize < characters.length) {
        await wait(TYPEWRITER_INTERVAL_MS, signal);
      }
    }
  }

  async function sendQuestion(nextQuestion: string) {
    const normalized = nextQuestion.trim();
    if (!normalized || isBusy) return;
    if (!isOnline) {
      setConnectionError("当前处于离线状态，恢复网络后可以继续发送。");
      toast.error("网络未连接");
      return;
    }
    // 新问题开始前停止上一条朗读，避免语音和 Agent 状态相互覆盖。
    speech.stop();

    const previousPersistedCount = messages.length;
    const userMessage: ChatMessage = {
      id: createMessageId(),
      role: "user",
      content: normalized,
      createdAt: new Date().toISOString(),
    };
    const assistantId = createMessageId();
    setMessages((current) => [
      ...current,
      userMessage,
      {
        id: assistantId,
        role: "assistant",
        content: "",
        createdAt: new Date().toISOString(),
        retryQuestion: normalized,
        presentation: isProfileIntroductionQuestion(normalized)
          ? "profile"
          : undefined,
      },
    ]);
    setQuestion("");
    setConnectionError(undefined);
    setRunProgress("正在连接 Agent…");
    setActiveAssistantId(assistantId);
    onStatusChange("thinking");
    abortController.current = new AbortController();

    let activeConversationId = conversationId;
    let activeTitle = conversations.find(
      (item) => item.id === conversationId,
    )?.title;
    let completed = false;
    let answerStarted = false;
    let finalAnswer = "";
    let automaticSpeechEnabled = false;
    const liveTimings: Record<string, number> = {};

    try {
      if (!activeConversationId) {
        activeTitle = createConversationTitle(normalized);
        const response = await apiClient.post<ConversationResponse>(
          "/conversations",
          {
            title: activeTitle,
          },
        );
        activeConversationId = response.data.id;
        setConversationId(activeConversationId);
        saveActiveConversation(activeConversationId);
        setConversations(
          saveConversation({
            id: activeConversationId,
            title: activeTitle,
            updatedAt: response.data.updated_at,
          }),
        );
      }

      const requestId = createMessageId();
      activeRun.current = {
        kind: "chat",
        conversationId: activeConversationId,
        requestId,
      };
      automaticSpeechEnabled = await speech.startRealtime(
        assistantId,
        readSpiritAppearance().characterId,
      );

      for await (const event of readEventStream(
        `/conversations/${activeConversationId}/messages/stream`,
        { question: normalized, filters: { document_ids: [], filenames: [] } },
        abortController.current.signal,
        requestId,
      )) {
        if (event.event === "run_started")
          setRunProgress("Agent 已启动，正在分析问题…");
        if (event.event === "heartbeat")
          setRunProgress("Agent 正在处理，连接保持正常…");
        if (event.event === "error") {
          const payload = event.data as { message?: string };
          throw new Error(payload.message || "Agent 流式回答失败");
        }
        if (event.event === "agent_step") {
          const step = event.data as AgentStep;
          setRunProgress(stepDescription(step));
          setMessages((current) =>
            current.map((message) =>
              message.id === assistantId
                ? { ...message, steps: [...(message.steps ?? []), step] }
                : message,
            ),
          );
        }
        if (event.event === "timing") {
          const timing = event.data as { stage: string; duration_ms: number };
          liveTimings[`${timing.stage}_ms`] = timing.duration_ms;
        }
        if (event.event === "answer_final") {
          setRunProgress("最终回答已经确认。");
          const answer = (event.data as { answer: string }).answer;
          finalAnswer = answer;
          // 最终文本用于校正流式拼接结果，不再等待额外模型核验。
          setMessages((current) =>
            current.map((message) =>
              message.id === assistantId
                ? { ...message, content: answer }
                : message,
            ),
          );
        }
        if (event.event === "cancelled") {
          throw new DOMException("回答已停止", "AbortError");
        }
        if (event.event === "answer_delta") {
          if (!answerStarted) {
            answerStarted = true;
            onStatusChange("answering");
          }
          setRunProgress("依据已经核验，正在生成回答…");
          const delta = (event.data as { delta: string }).delta;
          // 语音队列先接收模型增量，不等待打字机效果播放完毕。
          speech.appendRealtime(delta);
          await appendAnswerWithTypewriter(
            assistantId,
            delta,
            abortController.current.signal,
          );
        }
        if (event.event === "citations") {
          setMessages((current) =>
            current.map((message) =>
              message.id === assistantId
                ? { ...message, citations: event.data as Citation[] }
                : message,
            ),
          );
        }
        if (event.event === "resources") {
          const resources = (event.data as ResumeResource[]).filter(
            (resource) => resource.type === "resume",
          );
          setMessages((current) =>
            current.map((message) =>
              message.id === assistantId
                ? { ...message, resources }
                : message,
            ),
          );
        }
        if (event.event === "followup_suggestions") {
          const payload = event.data as SuggestionPayload;
          const suggestions = payload.suggestions.filter(
            (item): item is string =>
              typeof item === "string" && Boolean(item.trim()),
          );
          setMessages((current) =>
            current.map((message) =>
              message.id === assistantId
                ? { ...message, suggestions }
                : message,
            ),
          );
        }
        if (event.event === "completed") {
          completed = true;
          const result = event.data as CompletedEvent;
          setMessages((current) =>
            current.map((message) =>
              message.id === assistantId
                ? {
                    ...message,
                    completion: {
                      grounded: result.grounded,
                      degraded: result.degraded,
                      duration_ms: result.duration_ms,
                      timings: result.timings ?? liveTimings,
                    },
                  }
                : message,
            ),
          );
          setConversations(
            saveConversation({
              id: activeConversationId,
              title: activeTitle ?? createConversationTitle(normalized),
              updatedAt: new Date().toISOString(),
            }),
          );
        }
      }
      if (!completed) throw new Error("SSE 流在完成事件前中断");
      // 不等待音频队列播放完毕；推荐问题和下一轮对话应立即可用。
      void speech.finishRealtime(finalAnswer);
      if (!automaticSpeechEnabled) onStatusChange("idle");
    } catch (error) {
      if ((error as Error).name === "AbortError") {
        setMessages((current) =>
          current.map((message) =>
            message.id === assistantId
              ? {
                  ...message,
                  content: message.content || "回答已停止。",
                  stopped: true,
                }
              : message,
          ),
        );
        onStatusChange("idle");
      } else {
        speech.stop();
        // POST 流断开后先读取持久化会话；若后端已经完成，直接恢复完整回答。
        let recovered = false;
        if (activeConversationId) {
          // 代理刚断开时连接池可能尚未恢复，短间隔重试只读取权威消息。
          for (const delay of [0, 350, 1000]) {
            if (delay) await wait(delay);
            try {
              const response = await apiClient.get<ConversationResponse>(
                `/conversations/${activeConversationId}`,
              );
              if (response.data.messages.length > previousPersistedCount) {
                setMessages(mapConversationMessages(response.data));
                recovered = true;
                toast.success("连接曾短暂中断，完整回答已从服务器恢复。");
                break;
              }
            } catch {
              // 单次读取失败时继续有限重试，不会重复触发 Agent。
            }
          }
        }
        if (!recovered) {
          setMessages((current) =>
            current.map((message) =>
              message.id === assistantId
                ? {
                    ...message,
                    content:
                      message.content ||
                      "暂时无法连接知识库，请确认 FastAPI 和网络状态后重试。",
                    failed: true,
                  }
                : message,
            ),
          );
          setConnectionError("连接中断，当前问题可以安全重试。");
          onStatusChange("error");
        } else {
          onStatusChange("idle");
        }
      }
    } finally {
      abortController.current = null;
      activeRun.current = null;
      setActiveAssistantId(undefined);
      setRunProgress(undefined);
    }
  }

  function updateJdArtifact(
    messageId: string,
    updater: (artifact: JdAnalysisArtifact) => JdAnalysisArtifact,
  ) {
    setMessages((current) =>
      current.map((message) =>
        message.id === messageId
          ? {
              ...message,
              artifacts: (message.artifacts ?? []).map((artifact) =>
                artifact.type === "jd_analysis" ? updater(artifact) : artifact,
              ),
            }
          : message,
      ),
    );
  }

  async function sendJdAnalysis(jdText: string) {
    const normalized = jdText.trim();
    if (normalized.length < 30 || isBusy) {
      if (normalized.length < 30) toast.error("请粘贴至少 30 个字符的完整岗位描述。");
      return;
    }
    if (!isOnline) {
      toast.error("网络未连接");
      return;
    }

    speech.stop();
    const userId = createMessageId();
    const assistantId = createMessageId();
    const artifact: JdAnalysisArtifact = {
      type: "jd_analysis",
      status: "running",
      progress: "正在启动岗位匹配 Agent…",
      evaluatedCount: 0,
    };
    setMessages((current) => [
      ...current,
      {
        id: userId,
        role: "user",
        content: `岗位匹配：已提交一份岗位描述（${normalized.length} 字）`,
        createdAt: new Date().toISOString(),
      },
      {
        id: assistantId,
        role: "assistant",
        content: "",
        createdAt: new Date().toISOString(),
        artifacts: [artifact],
      },
    ]);
    setQuestion("");
    setConnectionError(undefined);
    setActiveAssistantId(assistantId);
    setRunProgress("正在启动岗位匹配 Agent…");
    onStatusChange("thinking");
    abortController.current = new AbortController();

    let activeConversationId = conversationId;
    let activeTitle = conversations.find((item) => item.id === conversationId)?.title;
    let completed = false;
    try {
      if (!activeConversationId) {
        activeTitle = "JD 岗位匹配";
        const response = await apiClient.post<ConversationResponse>("/conversations", {
          title: activeTitle,
        });
        activeConversationId = response.data.id;
        setConversationId(activeConversationId);
        saveActiveConversation(activeConversationId);
        setConversations(
          saveConversation({
            id: activeConversationId,
            title: activeTitle,
            updatedAt: response.data.updated_at,
          }),
        );
      }

      const requestId = createMessageId();
      activeRun.current = {
        kind: "jd",
        conversationId: activeConversationId,
        requestId,
      };
      for await (const event of readEventStream(
        "/jd-analyses/stream",
        { jd_text: normalized, conversation_id: activeConversationId },
        abortController.current.signal,
        requestId,
      )) {
        if (event.event === "heartbeat") {
          updateJdArtifact(assistantId, (current) => ({
            ...current,
            progress: "岗位匹配 Agent 正在处理，连接保持正常…",
          }));
        }
        if (event.event === "jd_parsed") {
          const data = event.data as {
            company_name: string | null;
            job_title: string | null;
            requirements: unknown[];
          };
          updateJdArtifact(assistantId, (current) => ({
            ...current,
            jobTitle: data.job_title,
            companyName: data.company_name,
            requirementCount: data.requirements.length,
            progress: `已解析 ${data.requirements.length} 项要求，正在检索知识库证据`,
          }));
        }
        if (event.event === "requirement_started") {
          const data = event.data as { requirement: string };
          updateJdArtifact(assistantId, (current) => ({
            ...current,
            progress: `正在核对：${data.requirement}`,
          }));
        }
        if (event.event === "evaluation_batch_started") {
          const data = event.data as { batch: number; total_batches: number };
          updateJdArtifact(assistantId, (current) => ({
            ...current,
            progress: `正在判断证据：第 ${data.batch}/${data.total_batches} 批`,
          }));
        }
        if (event.event === "requirement_evaluated") {
          updateJdArtifact(assistantId, (current) => ({
            ...current,
            evaluatedCount: (current.evaluatedCount ?? 0) + 1,
            progress: "正在验证引用并计算确定性分数",
          }));
        }
        if (event.event === "report_ready") {
          const report = event.data as JdAnalysisReport;
          updateJdArtifact(assistantId, (current) => ({
            ...current,
            analysisId: report.id,
            status: "completed",
            progress: "岗位匹配报告已完成",
            report,
          }));
        }
        if (event.event === "cancelled") {
          throw new DOMException("岗位匹配已停止", "AbortError");
        }
        if (event.event === "error") {
          const data = event.data as { message?: string };
          throw new Error(data.message ?? "岗位匹配失败");
        }
        if (event.event === "completed") {
          completed = true;
          setConversations(
            saveConversation({
              id: activeConversationId,
              title: activeTitle ?? "JD 岗位匹配",
              updatedAt: new Date().toISOString(),
            }),
          );
        }
      }
      if (!completed) throw new Error("岗位匹配流在完成事件前中断");
      onStatusChange("idle");
    } catch (error) {
      const stopped = error instanceof DOMException && error.name === "AbortError";
      updateJdArtifact(assistantId, (current) => ({
        ...current,
        status: stopped ? "cancelled" : "failed",
        progress: stopped ? "岗位匹配已停止" : "岗位匹配失败，可以重新提交",
      }));
      onStatusChange(stopped ? "idle" : "error");
      if (!stopped) toast.error(error instanceof Error ? error.message : "岗位匹配失败");
    } finally {
      abortController.current = null;
      activeRun.current = null;
      setActiveAssistantId(undefined);
      setRunProgress(undefined);
      setInputMode("chat");
    }
  }

  // 精灵快捷问题通过轻量浏览器事件进入同一发送链路，不复制会话逻辑。
  useEffect(() => {
    sendQuestionRef.current = (nextQuestion) => void sendQuestion(nextQuestion);
  });

  useEffect(() => {
    const handleSpiritQuestion = (event: Event) => {
      const questionFromSpirit = (event as CustomEvent<unknown>).detail;
      if (typeof questionFromSpirit === "string" && questionFromSpirit.trim()) {
        sendQuestionRef.current(questionFromSpirit);
      }
    };
    window.addEventListener(SPIRIT_QUESTION_EVENT, handleSpiritQuestion);
    return () =>
      window.removeEventListener(SPIRIT_QUESTION_EVENT, handleSpiritQuestion);
  }, []);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (inputMode === "jd") void sendJdAnalysis(question);
    else void sendQuestion(question);
  }

  function stopGeneration() {
    speech.stop();
    const run = activeRun.current;
    if (run) {
      // 先发出服务端取消请求，但不等待网络响应，以保证停止按钮立即生效。
      const cancelPath =
        run.kind === "jd"
          ? `/jd-analyses/runs/${run.requestId}/cancel`
          : `/conversations/${run.conversationId}/runs/${run.requestId}/cancel`;
      void apiClient
        .post(cancelPath)
        .catch(() => {
          // 运行可能恰好已经结束；SSE 断开也会在后端触发相同取消信号。
        });
    }
    abortController.current?.abort();
  }

  function newConversation() {
    speech.stop();
    abortController.current?.abort();
    clearActiveConversation();
    setConversationId(undefined);
    setMessages([]);
    setQuestion("");
    setInputMode("chat");
    setConnectionError(undefined);
    setRunProgress(undefined);
    onStatusChange("idle");
  }

  function selectConversation(item: LocalConversation) {
    if (item.id !== conversationId) void restoreConversation(item);
  }

  function removeLocalConversation(id: string) {
    setConversations(removeConversation(id));
    if (id === conversationId) newConversation();
  }

  async function copyAnswer(message: ChatMessage) {
    try {
      await window.navigator.clipboard.writeText(message.content);
      toast.success("回答已复制");
    } catch {
      toast.error("复制失败，请手动选择文本。");
    }
  }

  const lastMessage = messages.at(-1);
  const showFollowUps =
    lastMessage?.role === "assistant" &&
    !lastMessage.failed &&
    Boolean(lastMessage.suggestions?.length);

  return (
    <section className="bg-card/45 flex h-full min-h-0 w-full flex-col backdrop-blur-xl">
      <header
        className={cn(
          "border-border/60 bg-card/55 flex shrink-0 items-center justify-between gap-2 overflow-hidden border-b backdrop-blur-xl",
          isMobile ? "h-14 px-3" : "h-16 px-6 2xl:h-20 2xl:px-10",
        )}
      >
        {isMobile ? (
          <div className="min-w-0">
            <p className="truncate text-xs font-semibold">当前对话</p>
            <p className="text-muted-foreground truncate text-[10px]">
              {conversationId ? "已自动保存" : "公开知识库"}
            </p>
          </div>
        ) : (
          <div className="flex min-w-0 items-center gap-3">
            <BrandMark className="size-8 shrink-0" />
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold">ZYW 的 AI 小助理</p>
              <p className="text-muted-foreground truncate text-[11px]">
                {conversationId
                  ? "会话已保存，可刷新后继续"
                  : "基于公开知识库回答"}
              </p>
            </div>
          </div>
        )}
        <div className="flex shrink-0 items-center gap-0.5 sm:gap-1">
          <ConversationDrawer
            conversations={conversations}
            activeId={conversationId}
            disabled={isBusy}
            onSelect={selectConversation}
            onRemove={removeLocalConversation}
            onCreate={newConversation}
          />
          <ThemeToggle />
          <ResumeEntry compact={isMobile} />
          <Link
            href="/admin"
            aria-label="进入知识库管理端"
            className={buttonVariants({
              variant: "ghost",
              size: isMobile ? "icon" : "sm",
            })}
          >
            <ShieldCheck data-icon="inline-start" />
            {!isMobile && <span>管理端</span>}
          </Link>
          <Button
            variant="ghost"
            size={isMobile ? "icon" : "sm"}
            aria-label="开始新对话"
            onClick={newConversation}
            disabled={isBusy}
          >
            <Plus data-icon="inline-start" />
            {!isMobile && <span>新对话</span>}
          </Button>
        </div>
      </header>

      {(!isOnline || connectionError) && (
        <div className="border-border/60 bg-destructive/8 text-destructive flex shrink-0 items-center gap-2 border-b px-4 py-2 text-xs sm:px-7">
          {!isOnline ? (
            <WifiOff className="size-4" />
          ) : (
            <CircleAlert className="size-4" />
          )}
          <span>
            {!isOnline ? "网络已断开，输入内容会保留。" : connectionError}
          </span>
        </div>
      )}

      <div
        className={cn(
          "min-h-0 flex-1 overflow-y-auto",
          isMobile ? "px-3 py-4" : "px-7 py-6",
        )}
        aria-live="polite"
      >
        {messages.length === 0 ? (
          <div
            className={cn(
              "mx-auto flex h-full w-full flex-col",
              isMobile
                ? "max-w-none justify-start py-5"
                : "max-w-2xl justify-center py-8 xl:max-w-3xl 2xl:max-w-5xl",
            )}
          >
            {isRestoring ? (
              <div className="text-muted-foreground flex items-center gap-2">
                <LoaderCircle className="size-5 animate-spin" /> 正在恢复会话…
              </div>
            ) : (
              <>
                <Badge variant="outline" className="mb-4 w-fit rounded-full">
                  可以问我
                </Badge>
                <h1
                  className={cn(
                    "font-semibold tracking-tight",
                    isMobile ? "text-xl" : "text-3xl 2xl:text-4xl",
                  )}
                >
                  从一个问题开始了解 ZYW
                </h1>
                <p className="text-muted-foreground mt-3 leading-7">
                  我会自动检索公开资料，并在回答中提供可以展开核查的来源。
                </p>
                <div className={cn(isMobile ? "mt-5" : "mt-7")}>
                  {suggestionsLoading && (
                    <div className="text-muted-foreground flex items-center gap-2 px-1 py-3 text-sm">
                      <LoaderCircle className="size-4 animate-spin" />
                      正在根据公开资料准备推荐问题…
                    </div>
                  )}
                  <SuggestionChips
                    suggestions={emptySuggestions}
                    onSelect={(suggestion) => void sendQuestion(suggestion)}
                    reduceMotion={reduceMotion}
                  />
                </div>
              </>
            )}
          </div>
        ) : (
          <div
            className={cn(
              "mx-auto w-full",
              isMobile
                ? "max-w-none space-y-4"
                : "max-w-3xl space-y-6 xl:max-w-4xl",
            )}
          >
            <AnimatePresence initial={false}>
              {messages.map((message) => (
                <motion.article
                  key={message.id}
                  initial={reduceMotion ? false : { opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className={cn(
                    "flex",
                    isMobile ? "gap-2" : "gap-3",
                    message.role === "user" ? "justify-end" : "justify-start",
                  )}
                >
                  {message.role === "assistant" && (
                    <span className="bg-primary/10 text-primary grid size-8 shrink-0 place-items-center rounded-xl">
                      <Bot className="size-4" />
                    </span>
                  )}
                  <div
                    className={cn(
                      "min-w-0 rounded-2xl text-sm leading-7 break-words [&_a]:break-all [&_pre]:max-w-full [&_pre]:overflow-x-auto [&_table]:block [&_table]:max-w-full [&_table]:overflow-x-auto",
                      isMobile
                        ? "max-w-[calc(100%_-_2.5rem)] px-3 py-2.5"
                        : message.presentation === "profile"
                          ? "max-w-[min(52rem,calc(100%_-_3rem))] px-4 py-4"
                          : "max-w-[min(46rem,calc(100%_-_3rem))] px-4 py-3",
                      message.role === "user"
                        ? "bg-primary text-primary-foreground"
                        : "glass-panel",
                    )}
                  >
                    {!!message.artifacts?.length ? (
                      <div className="space-y-3">
                        {message.artifacts.map((artifact) => (
                          <JdAnalysisCard
                            key={artifact.analysisId ?? message.id}
                            artifact={artifact}
                            onAsk={(question) => void sendQuestion(question)}
                            reportDownloadUrl={
                              conversationId
                                ? `/api/backend/career/conversations/${conversationId}/report`
                                : undefined
                            }
                          />
                        ))}
                      </div>
                    ) : message.content ? (
                      <>
                        {message.role === "assistant" &&
                        message.presentation === "profile" ? (
                          <ProfileIntroduction content={message.content} />
                        ) : (
                          <AnswerMarkdown content={message.content} />
                        )}
                        {message.id === activeAssistantId && (
                          <span
                            aria-hidden="true"
                            className="bg-primary ml-0.5 inline-block h-4 w-0.5 animate-pulse align-middle"
                          />
                        )}
                      </>
                    ) : (
                      <span className="text-muted-foreground flex items-center gap-2">
                        <LoaderCircle className="size-4 animate-spin" />
                        {message.id === activeAssistantId
                          ? (runProgress ?? "正在寻找依据…")
                          : "正在加载…"}
                      </span>
                    )}
                    {!!message.citations?.length && (
                      <CitationDisclosure citations={message.citations} />
                    )}
                    {message.resources?.map((resource) => (
                      <ResumeDownloadCard
                        key={`${resource.type}-${resource.version}`}
                        resource={resource}
                      />
                    ))}
                    {message.role === "assistant" &&
                      (!!message.steps?.length || message.completion) && (
                        <ProcessDisclosure
                          steps={message.steps ?? []}
                          completion={message.completion}
                        />
                      )}
                    {message.role === "assistant" &&
                      message.content &&
                      !message.artifacts?.length &&
                      message.id !== activeAssistantId && (
                        <div
                          className={cn(
                            "mt-2 flex items-center gap-1",
                            isMobile && "flex-wrap",
                          )}
                        >
                          <Button
                            variant="ghost"
                            size="xs"
                            onClick={() => void copyAnswer(message)}
                          >
                            <Copy data-icon="inline-start" />
                            复制
                          </Button>
                          {speech.state.messageId === message.id ? (
                            <>
                              <Button
                                variant="ghost"
                                size="xs"
                                disabled={speech.state.phase === "loading"}
                                onClick={() =>
                                  void speech.speak(
                                    message.id,
                                    message.content,
                                    readSpiritAppearance().characterId,
                                  )
                                }
                                aria-label={
                                  speech.state.phase === "playing"
                                    ? "暂停朗读"
                                    : "继续朗读"
                                }
                              >
                                {speech.state.phase === "loading" ? (
                                  <LoaderCircle className="animate-spin" />
                                ) : speech.state.phase === "playing" ? (
                                  <Pause />
                                ) : (
                                  <Play />
                                )}
                                {speech.state.phase === "loading"
                                  ? "合成中"
                                  : speech.state.phase === "playing"
                                    ? "暂停"
                                    : "继续"}
                              </Button>
                              <Button
                                variant="ghost"
                                size="xs"
                                onClick={() => speech.stop()}
                              >
                                <Square className="size-3 fill-current" />
                                停止
                              </Button>
                            </>
                          ) : (
                            <Button
                              variant="ghost"
                              size="xs"
                              onClick={() =>
                                void speech.speak(
                                  message.id,
                                  message.content,
                                  readSpiritAppearance().characterId,
                                )
                              }
                            >
                              <Volume2 />
                              朗读
                            </Button>
                          )}
                          <Button
                            variant="ghost"
                            size="xs"
                            onClick={speech.changeSpeed}
                            aria-label={`切换朗读速度，当前 ${speech.state.speed} 倍`}
                          >
                            {speech.state.speed}×
                          </Button>
                          {message.retryQuestion && (
                            <Button
                              variant="ghost"
                              size="xs"
                              onClick={() =>
                                void sendQuestion(message.retryQuestion!)
                              }
                            >
                              <RotateCcw data-icon="inline-start" />
                              重试
                            </Button>
                          )}
                          {message.stopped && (
                            <span className="text-muted-foreground ml-1 text-xs">
                              已停止
                            </span>
                          )}
                        </div>
                      )}
                    <time
                      dateTime={message.createdAt}
                      title={new Date(message.createdAt).toLocaleString(
                        "zh-CN",
                      )}
                      className={cn(
                        "mt-1 block text-[10px] leading-4 tabular-nums",
                        message.role === "user"
                          ? "text-primary-foreground/65 text-right"
                          : "text-muted-foreground",
                      )}
                    >
                      {formatMessageTime(message.createdAt)}
                    </time>
                  </div>
                  {message.role === "user" && (
                    <span className="bg-secondary grid size-8 shrink-0 place-items-center rounded-xl">
                      <UserRound className="size-4" />
                    </span>
                  )}
                </motion.article>
              ))}
            </AnimatePresence>

            {showFollowUps && (
              <div className={cn(!isMobile && "pl-11")}>
                <p className="text-muted-foreground mb-2 flex items-center gap-1.5 text-xs">
                  <Sparkles className="text-primary size-3.5" />
                  接着了解
                </p>
                <SuggestionChips
                  suggestions={lastMessage.suggestions ?? []}
                  onSelect={(suggestion) => void sendQuestion(suggestion)}
                  reduceMotion={reduceMotion}
                />
              </div>
            )}
            <div ref={messageEnd} aria-hidden="true" />
          </div>
        )}
      </div>

      <footer
        className={cn(
          "border-border/60 bg-card/70 shrink-0 border-t backdrop-blur-xl",
          isMobile
            ? "p-3 pb-[max(0.75rem,env(safe-area-inset-bottom))]"
            : "p-5",
        )}
      >
        {inputMode === "jd" && (
          <div className="mx-auto mb-2 flex w-full max-w-3xl items-center justify-between px-1 text-xs xl:max-w-4xl">
            <span className="bg-primary/10 text-primary inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 font-medium">
              <BriefcaseBusiness className="size-3.5" /> JD 岗位匹配模式
            </span>
            <button
              type="button"
              className="text-muted-foreground hover:text-foreground"
              onClick={() => setInputMode("chat")}
              disabled={isBusy}
            >
              退出岗位模式
            </button>
          </div>
        )}
        <form
          onSubmit={submit}
          className="bg-background/70 shadow-primary/5 focus-within:border-primary/50 focus-within:ring-primary/10 mx-auto flex w-full max-w-3xl items-end gap-2 rounded-2xl border p-2 shadow-lg focus-within:ring-3 xl:max-w-4xl"
        >
          <Button
            type="button"
            size="icon"
            variant={inputMode === "jd" ? "secondary" : "ghost"}
            aria-label={inputMode === "jd" ? "退出岗位匹配模式" : "进入岗位匹配模式"}
            title="JD 岗位匹配"
            disabled={isBusy || isRestoring}
            onClick={() => setInputMode((current) => (current === "jd" ? "chat" : "jd"))}
          >
            <BriefcaseBusiness />
          </Button>
          <textarea
            aria-label="向 ZYW 的 AI 小助理提问"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                event.currentTarget.form?.requestSubmit();
              }
            }}
            placeholder={
              inputMode === "jd"
                ? "粘贴完整岗位职责、任职要求和加分项…"
                : "问问 ZYW 的技术、经历或这个项目…"
            }
            rows={1}
            disabled={isRestoring}
            className={cn(
              "placeholder:text-muted-foreground max-h-40 flex-1 resize-none bg-transparent px-3 py-2 text-sm outline-none disabled:opacity-60",
              inputMode === "jd" ? "min-h-20" : "min-h-9",
            )}
          />
          {status === "thinking" || status === "answering" ? (
            <Button
              type="button"
              size="icon"
              variant="outline"
              aria-label="停止回答"
              onClick={stopGeneration}
            >
              <Square className="size-3.5 fill-current" />
            </Button>
          ) : (
            <Button
              type="submit"
              size="icon"
              aria-label="发送问题"
              disabled={!question.trim() || !isOnline || isRestoring}
            >
              <Send />
            </Button>
          )}
        </form>
        <p className="text-muted-foreground mt-2 text-center text-[11px]">
          AI 可能出错，请通过引用核查重要信息。
        </p>
      </footer>
    </section>
  );
}
