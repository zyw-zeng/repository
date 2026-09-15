"use client";

/** 按设备宽度选择独立的桌面端或移动端实现。 */

import { useSyncExternalStore } from "react";

import { DesktopAssistantWorkspace } from "./desktop-assistant-workspace";
import { MobileAssistantWorkspace } from "./mobile-assistant-workspace";

const MOBILE_QUERY = "(max-width: 767px)";

function subscribeToViewport(onStoreChange: () => void) {
  const media = window.matchMedia(MOBILE_QUERY);
  media.addEventListener("change", onStoreChange);
  return () => media.removeEventListener("change", onStoreChange);
}

function getViewportSnapshot() {
  return window.matchMedia(MOBILE_QUERY).matches;
}

function getServerSnapshot() {
  return false;
}

function subscribeToHydration() {
  return () => undefined;
}

function getHydratedSnapshot() {
  return true;
}

export function AssistantWorkspace() {
  const hydrated = useSyncExternalStore(
    subscribeToHydration,
    getHydratedSnapshot,
    getServerSnapshot,
  );
  const isMobile = useSyncExternalStore(
    subscribeToViewport,
    getViewportSnapshot,
    getServerSnapshot,
  );

  // 服务端无法获知真实视口；确认设备分支前不挂载可交互聊天，避免水合切换丢请求。
  if (!hydrated) {
    return (
      <main
        className="bg-background grid h-dvh place-items-center"
        aria-busy="true"
      >
        <div className="from-brand-cyan via-brand-indigo to-brand-violet size-12 animate-pulse rounded-[42%] bg-gradient-to-br" />
        <span className="sr-only">正在准备 AI 小助理</span>
      </main>
    );
  }

  return isMobile ? (
    <MobileAssistantWorkspace />
  ) : (
    <DesktopAssistantWorkspace />
  );
}
