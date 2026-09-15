/** 验证精灵外观和移动端停靠位置只保存在当前浏览器。 */

import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";

import {
  readSpiritDockPosition,
  saveSpiritDockPosition,
  useSpiritAppearance,
} from "./spirit-storage";

describe("精灵个性化存储", () => {
  beforeEach(() => window.localStorage.clear());

  it("保存并恢复用户选择的形象、服装和配饰", () => {
    const first = renderHook(() => useSpiritAppearance());
    act(() => {
      first.result.current[1]({
        characterId: "byte",
        outfitId: "explorer",
        accessoryId: "cap",
      });
    });
    first.unmount();

    const restored = renderHook(() => useSpiritAppearance());
    expect(restored.result.current[0]).toEqual({
      characterId: "byte",
      outfitId: "explorer",
      accessoryId: "cap",
    });
  });

  it("保存移动端吸附边和相对高度", () => {
    saveSpiritDockPosition({ side: "left", yRatio: 0.62 });

    expect(readSpiritDockPosition()).toEqual({ side: "left", yRatio: 0.62 });
  });
});
