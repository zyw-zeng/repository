/** 定义精灵形象、装扮、位置和运行状态。 */

export type SpiritStatus =
  | "idle"
  | "thinking"
  | "answering"
  | "speaking"
  | "error";
export type SpiritCharacterId = "nova" | "byte" | "momo";
export type SpiritOutfitId = "classic" | "coder" | "explorer";
export type SpiritAccessoryId = "none" | "headphones" | "cap";

export interface SpiritAppearance {
  characterId: SpiritCharacterId;
  outfitId: SpiritOutfitId;
  accessoryId: SpiritAccessoryId;
}

export interface SpiritDockPosition {
  side: "left" | "right";
  yRatio: number;
}
