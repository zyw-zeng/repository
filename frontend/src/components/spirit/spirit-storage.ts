"use client";

/** 保存精灵外观和移动端停靠位置，不把个性化数据发送到服务端。 */

import { useEffect, useState } from "react";

import { DEFAULT_SPIRIT_APPEARANCE } from "./appearances";
import type { SpiritAppearance, SpiritDockPosition } from "./types";

// 新主形象使用独立版本，避免恢复旧幽灵的默认穿搭。
const APPEARANCE_KEY = "zyw_spirit_appearance_v2";
// 新版本默认停靠在内容稀疏的下半区，避免首次进入时遮挡推荐问题。
const POSITION_KEY = "zyw_spirit_position_v2";

function readJson<T>(key: string, fallback: T): T {
  if (typeof window === "undefined") return fallback;
  try {
    return {
      ...fallback,
      ...JSON.parse(window.localStorage.getItem(key) ?? "{}"),
    };
  } catch {
    return fallback;
  }
}

export function useSpiritAppearance() {
  const [appearance, setAppearance] = useState<SpiritAppearance>(() =>
    readSpiritAppearance(),
  );

  useEffect(() => {
    window.localStorage.setItem(APPEARANCE_KEY, JSON.stringify(appearance));
  }, [appearance]);

  return [appearance, setAppearance] as const;
}

export function readSpiritAppearance(): SpiritAppearance {
  /** 读取当前角色供聊天与实时语音使用。 */
  const appearance = readJson(APPEARANCE_KEY, DEFAULT_SPIRIT_APPEARANCE);
  return {
    characterId: ["nova", "byte", "momo"].includes(appearance.characterId)
      ? appearance.characterId
      : DEFAULT_SPIRIT_APPEARANCE.characterId,
    outfitId: appearance.outfitId,
    accessoryId: appearance.accessoryId,
  };
}

export function readSpiritDockPosition(): SpiritDockPosition {
  const position = readJson<SpiritDockPosition>(POSITION_KEY, {
    side: "right",
    yRatio: 0.72,
  });
  return {
    side: position.side === "left" ? "left" : "right",
    yRatio: Math.min(0.85, Math.max(0.08, Number(position.yRatio) || 0.72)),
  };
}

export function saveSpiritDockPosition(position: SpiritDockPosition) {
  window.localStorage.setItem(POSITION_KEY, JSON.stringify(position));
}
