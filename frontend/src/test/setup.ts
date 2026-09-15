/** 为组件测试补齐 DOM 匹配器和浏览器媒体查询能力。 */

import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

// 每个测试结束后卸载 React 树，避免桌面端和移动端工作区互相污染。
afterEach(() => cleanup());

Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => undefined,
    removeListener: () => undefined,
    addEventListener: () => undefined,
    removeEventListener: () => undefined,
    dispatchEvent: () => false,
  }),
});

// JSDOM 不实现滚动行为，测试中提供空实现以覆盖消息自动跟随逻辑。
Element.prototype.scrollIntoView = () => undefined;
