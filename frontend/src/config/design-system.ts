/** 集中声明需要在组件逻辑中复用的品牌和动效规范。 */

export const brand = {
  name: "ZYW 的 AI 小助理",
  shortName: "ZYW AI",
  description: "通过可靠引用，帮助你了解 ZYW 与这个 AI Agent 项目。",
} as const;

export const motionDurations = {
  instant: 0.12,
  fast: 0.2,
  normal: 0.35,
  slow: 0.6,
} as const;

export const motionEase = [0.22, 1, 0.36, 1] as const;
