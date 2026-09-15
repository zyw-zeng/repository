"use client";

/** 桌面端专用双栏工作区，不承担移动端布局适配。 */

import { useState } from "react";

import { AiSpirit, type SpiritStatus } from "./ai-spirit";
import { ChatPanel } from "./chat-panel";

export function DesktopAssistantWorkspace() {
  const [status, setStatus] = useState<SpiritStatus>("idle");

  return (
    <main className="h-dvh overflow-hidden">
      <div
        data-testid="assistant-shell"
        data-layout="desktop"
        className="bg-background/50 grid h-dvh w-full grid-cols-[42%_58%] overflow-hidden 2xl:grid-cols-[40%_60%]"
      >
        <AiSpirit status={status} />
        <ChatPanel
          status={status}
          onStatusChange={setStatus}
          displayMode="desktop"
        />
      </div>
    </main>
  );
}
