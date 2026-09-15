/** 集中配置可选精灵、服装和配饰，新增外观时无需修改页面逻辑。 */

import type {
  SpiritAccessoryId,
  SpiritAppearance,
  SpiritCharacterId,
  SpiritOutfitId,
} from "./types";

export const DEFAULT_SPIRIT_APPEARANCE: SpiritAppearance = {
  characterId: "nova",
  outfitId: "classic",
  accessoryId: "none",
};

export const spiritCharacters: Array<{
  id: SpiritCharacterId;
  name: string;
  description: string;
  colors: [string, string];
}> = [
  {
    id: "nova",
    name: "星云",
    description: "柔和、聪明的默认形象",
    colors: ["#67e8f9", "#a855f7"],
  },
  {
    id: "byte",
    name: "比特",
    description: "由切角轮廓与数据节点构成的理性精灵",
    colors: ["#34d399", "#2563eb"],
  },
  {
    id: "momo",
    name: "沫沫",
    description: "带着泡泡尾巴、柔软活泼的月滴精灵",
    colors: ["#fbbf24", "#fb7185"],
  },
];

export const spiritOutfits: Array<{
  id: SpiritOutfitId;
  name: string;
  description: string;
}> = [
  { id: "classic", name: "经典", description: "保留精灵本体的简洁轮廓" },
  { id: "coder", name: "程序员", description: "深色连帽衫与代码徽章" },
  { id: "explorer", name: "探索者", description: "亮色围巾与探索徽章" },
];

export const spiritAccessories: Array<{
  id: SpiritAccessoryId;
  name: string;
}> = [
  { id: "none", name: "无配饰" },
  { id: "headphones", name: "未来耳机" },
  { id: "cap", name: "灵感帽" },
];

export function getCharacter(characterId: SpiritCharacterId) {
  return (
    spiritCharacters.find((character) => character.id === characterId) ??
    spiritCharacters[0]
  );
}

export function getOutfit(outfitId: SpiritOutfitId) {
  /** 返回当前服装信息，旧版存储出现未知值时安全回退到经典服装。 */
  return (
    spiritOutfits.find((outfit) => outfit.id === outfitId) ?? spiritOutfits[0]
  );
}

export function getAccessory(accessoryId: SpiritAccessoryId) {
  /** 返回当前配饰信息，旧版存储出现未知值时安全回退到无配饰。 */
  return (
    spiritAccessories.find((accessory) => accessory.id === accessoryId) ??
    spiritAccessories[0]
  );
}
