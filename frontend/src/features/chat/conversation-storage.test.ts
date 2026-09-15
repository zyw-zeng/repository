/** 验证本地会话索引排序、去重、标题截断和损坏数据恢复。 */

import { beforeEach, describe, expect, it } from "vitest";

import {
  createConversationTitle,
  readConversationIndex,
  removeConversation,
  saveConversation,
} from "./conversation-storage";

describe("本地会话索引", () => {
  beforeEach(() => window.localStorage.clear());

  it("按更新时间保存并去重", () => {
    saveConversation({ id: "old", title: "旧会话", updatedAt: "2026-01-01" });
    saveConversation({ id: "new", title: "新会话", updatedAt: "2026-02-01" });
    saveConversation({
      id: "old",
      title: "更新后的旧会话",
      updatedAt: "2026-03-01",
    });

    expect(readConversationIndex().map((item) => item.id)).toEqual([
      "old",
      "new",
    ]);
    expect(removeConversation("old")).toHaveLength(1);
  });

  it("损坏数据安全回退并限制标题长度", () => {
    window.localStorage.setItem("zyw_conversation_index_v1", "{broken");
    expect(readConversationIndex()).toEqual([]);
    expect(
      createConversationTitle(
        "这是一个非常长的提问，用来验证会话标题不会在历史列表中无限增长并破坏页面布局",
      ),
    ).toHaveLength(29);
  });
});
