/** 在浏览器本地维护访客自己的会话 ID 索引，不保存完整聊天正文。 */

import type { LocalConversation } from "./types";

const INDEX_KEY = "zyw_conversation_index_v1";
const ACTIVE_KEY = "zyw_active_conversation_v1";
const MAX_LOCAL_CONVERSATIONS = 30;

function isConversation(value: unknown): value is LocalConversation {
  if (!value || typeof value !== "object") return false;
  const item = value as Record<string, unknown>;
  return (
    typeof item.id === "string" &&
    typeof item.title === "string" &&
    typeof item.updatedAt === "string"
  );
}

export function readConversationIndex(): LocalConversation[] {
  if (typeof window === "undefined") return [];
  try {
    const value = JSON.parse(
      window.localStorage.getItem(INDEX_KEY) ?? "[]",
    ) as unknown;
    if (!Array.isArray(value)) return [];
    return value.filter(isConversation).slice(0, MAX_LOCAL_CONVERSATIONS);
  } catch {
    // 本地数据损坏时回到空索引，不阻止用户开启新会话。
    return [];
  }
}

export function saveConversation(item: LocalConversation): LocalConversation[] {
  const next = [
    item,
    ...readConversationIndex().filter((entry) => entry.id !== item.id),
  ]
    .sort((left, right) => right.updatedAt.localeCompare(left.updatedAt))
    .slice(0, MAX_LOCAL_CONVERSATIONS);
  window.localStorage.setItem(INDEX_KEY, JSON.stringify(next));
  return next;
}

export function removeConversation(id: string): LocalConversation[] {
  const next = readConversationIndex().filter((entry) => entry.id !== id);
  window.localStorage.setItem(INDEX_KEY, JSON.stringify(next));
  if (readActiveConversation() === id) clearActiveConversation();
  return next;
}

export function readActiveConversation(): string | undefined {
  if (typeof window === "undefined") return undefined;
  return window.localStorage.getItem(ACTIVE_KEY) ?? undefined;
}

export function saveActiveConversation(id: string): void {
  window.localStorage.setItem(ACTIVE_KEY, id);
}

export function clearActiveConversation(): void {
  if (typeof window !== "undefined") window.localStorage.removeItem(ACTIVE_KEY);
}

export function createConversationTitle(question: string): string {
  const compact = question.replace(/\s+/g, " ").trim();
  return compact.length > 28 ? `${compact.slice(0, 28)}…` : compact || "新会话";
}
