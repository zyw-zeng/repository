"use client";

/** 移动端专用聊天入口，使用独立展示模式并复用统一会话协议。 */

import { ChatPanel } from "./chat-panel";
import type { SpiritStatus } from "./ai-spirit";

interface MobileChatPanelProps {
  status: SpiritStatus;
  onStatusChange: (status: SpiritStatus) => void;
}

export function MobileChatPanel({
  status,
  onStatusChange,
}: MobileChatPanelProps) {
  return (
    <ChatPanel
      status={status}
      onStatusChange={onStatusChange}
      displayMode="mobile"
    />
  );
}
