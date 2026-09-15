"use client";

/** 移动端专用全高聊天区，并叠加可拖拽悬浮精灵。 */

import { useState } from "react";

import type { SpiritStatus } from "./ai-spirit";
import { MobileAiSpirit } from "./mobile-ai-spirit";
import { MobileChatPanel } from "./mobile-chat-panel";

export function MobileAssistantWorkspace() {
  const [status, setStatus] = useState<SpiritStatus>("idle");

  return (
    <main className="h-dvh overflow-hidden">
      <div
        data-testid="assistant-shell"
        data-layout="mobile"
        className="bg-background/50 relative h-dvh w-full overflow-hidden"
      >
        <MobileChatPanel status={status} onStatusChange={setStatus} />
        <MobileAiSpirit status={status} />
      </div>
    </main>
  );
}
