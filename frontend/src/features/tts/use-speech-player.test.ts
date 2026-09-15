/** 验证实时朗读分句不会逐 Token 请求 CosyVoice。 */

import { describe, expect, it } from "vitest";

import { splitReadySpeechSegments } from "./use-speech-player";

describe("实时朗读分句", () => {
  it("保留未完成短句，并在完整标点到达后输出", () => {
    const pending = splitReadySpeechSegments("ZYW 正在开发一个");
    const completed = splitReadySpeechSegments(
      `${pending.remainder}可靠的个人知识库。后一句还没有完成`,
    );

    expect(pending.segments).toEqual([]);
    expect(completed.segments).toEqual(["ZYW 正在开发一个可靠的个人知识库。"]);
    expect(completed.remainder).toBe("后一句还没有完成");
  });

  it("超长句优先在逗号附近切分", () => {
    const result = splitReadySpeechSegments(
      `这是一个用于验证长句切分的前半部分，${"内容".repeat(40)}`,
    );

    expect(result.segments[0]).toBe("这是一个用于验证长句切分的前半部分，");
    expect(result.remainder.length).toBeLessThan(72);
  });
});
