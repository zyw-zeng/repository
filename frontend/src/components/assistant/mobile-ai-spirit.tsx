"use client";

/** 移动端可拖拽精灵：限制活动范围、自动吸附边缘并记住停靠位置。 */

import { useEffect, useRef, useState } from "react";

import { SpiritAvatar } from "@/components/spirit/spirit-avatar";
import { SpiritCustomizer } from "@/components/spirit/spirit-customizer";
import {
  readSpiritDockPosition,
  saveSpiritDockPosition,
  useSpiritAppearance,
} from "@/components/spirit/spirit-storage";
import type { SpiritStatus } from "@/components/spirit/types";
import { cn } from "@/lib/utils";

const SPIRIT_SIZE = 76;
const EDGE_GAP = 10;
const TOP_GAP = 72;
const BOTTOM_RESERVED = 150;

const mobileStatusCopy: Record<SpiritStatus, string> = {
  idle: "准备好啦，问我关于 ZYW 的事",
  thinking: "正在知识库中搜索…",
  answering: "正在回答你…",
  speaking: "正在读给你听…",
  error: "连接走神了，请再试一次",
};

interface Point {
  x: number;
  y: number;
}

interface DragState extends Point {
  pointerId: number;
  pointerX: number;
  pointerY: number;
  moved: boolean;
}

function bounds() {
  const viewport = window.visualViewport;
  const viewportWidth = viewport?.width ?? document.documentElement.clientWidth;
  const viewportHeight = viewport?.height ?? window.innerHeight;
  const viewportTop = viewport?.offsetTop ?? 0;
  const minimumY = Math.max(TOP_GAP, viewportTop + TOP_GAP);
  return {
    viewportWidth,
    minY: minimumY,
    maxX: Math.max(EDGE_GAP, viewportWidth - SPIRIT_SIZE - EDGE_GAP),
    maxY: Math.max(
      minimumY,
      viewportTop + viewportHeight - SPIRIT_SIZE - BOTTOM_RESERVED,
    ),
  };
}

function pointFromStorage(): Point {
  const dock = readSpiritDockPosition();
  const { minY, maxX, maxY } = bounds();
  return {
    x: dock.side === "left" ? EDGE_GAP : maxX,
    y: minY + (maxY - minY) * dock.yRatio,
  };
}

export function MobileAiSpirit({ status }: { status: SpiritStatus }) {
  const [appearance, setAppearance] = useSpiritAppearance();
  const [customizerOpen, setCustomizerOpen] = useState(false);
  const [position, setPosition] = useState<Point>({ x: -100, y: TOP_GAP });
  const [ready, setReady] = useState(false);
  const drag = useRef<DragState | null>(null);

  useEffect(() => {
    const restorePosition = () => {
      setPosition(pointFromStorage());
      setReady(true);
    };
    restorePosition();
    window.addEventListener("resize", restorePosition);
    window.visualViewport?.addEventListener("resize", restorePosition);
    window.visualViewport?.addEventListener("scroll", restorePosition);
    return () => {
      window.removeEventListener("resize", restorePosition);
      window.visualViewport?.removeEventListener("resize", restorePosition);
      window.visualViewport?.removeEventListener("scroll", restorePosition);
    };
  }, []);

  function handlePointerDown(event: React.PointerEvent<HTMLDivElement>) {
    event.currentTarget.setPointerCapture(event.pointerId);
    drag.current = {
      pointerId: event.pointerId,
      pointerX: event.clientX,
      pointerY: event.clientY,
      x: position.x,
      y: position.y,
      moved: false,
    };
  }

  function handlePointerMove(event: React.PointerEvent<HTMLDivElement>) {
    const active = drag.current;
    if (!active || active.pointerId !== event.pointerId) return;
    const deltaX = event.clientX - active.pointerX;
    const deltaY = event.clientY - active.pointerY;
    if (Math.abs(deltaX) + Math.abs(deltaY) > 5) active.moved = true;
    const { minY, maxX, maxY } = bounds();
    setPosition({
      x: Math.min(maxX, Math.max(EDGE_GAP, active.x + deltaX)),
      y: Math.min(maxY, Math.max(minY, active.y + deltaY)),
    });
  }

  function handlePointerUp(event: React.PointerEvent<HTMLDivElement>) {
    const active = drag.current;
    if (!active || active.pointerId !== event.pointerId) return;
    drag.current = null;
    if (!active.moved) {
      setCustomizerOpen(true);
      return;
    }
    const { viewportWidth, minY, maxX, maxY } = bounds();
    const releasedX = Math.min(
      maxX,
      Math.max(EDGE_GAP, active.x + event.clientX - active.pointerX),
    );
    const releasedY = Math.min(
      maxY,
      Math.max(minY, active.y + event.clientY - active.pointerY),
    );
    const side =
      releasedX + SPIRIT_SIZE / 2 < viewportWidth / 2 ? "left" : "right";
    const snapped = {
      x: side === "left" ? EDGE_GAP : maxX,
      y: releasedY,
    };
    setPosition(snapped);
    saveSpiritDockPosition({
      side,
      yRatio: maxY === minY ? 0 : (snapped.y - minY) / (maxY - minY),
    });
  }

  const dockedLeft =
    position.x + SPIRIT_SIZE / 2 < windowWidthCenter();

  return (
    <>
      <div
        role="button"
        tabIndex={0}
        aria-label="拖动精灵或点击打开换装间"
        onKeyDown={(event) => {
          if (event.key === "Enter" || event.key === " ")
            setCustomizerOpen(true);
        }}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerCancel={() => {
          drag.current = null;
        }}
        className={cn(
          "fixed top-0 left-0 z-40 touch-none transition-opacity duration-200 select-none will-change-transform",
          ready ? "opacity-100" : "pointer-events-none opacity-0",
        )}
        style={{
          width: SPIRIT_SIZE,
          height: SPIRIT_SIZE,
          transform: `translate3d(${position.x}px, ${position.y}px, 0)`,
        }}
      >
        <div className="bg-background/65 size-full rounded-[42%] p-1 shadow-xl ring-1 ring-white/15 backdrop-blur-md">
          <SpiritAvatar appearance={appearance} status={status} decorative />
        </div>
        <p
          role="status"
          className={cn(
            "border-border/70 bg-background/90 pointer-events-none absolute top-1/2 w-max max-w-44 -translate-y-1/2 rounded-xl border px-2.5 py-1.5 text-[11px] shadow-lg backdrop-blur-md",
            dockedLeft
              ? "left-[calc(100%+0.5rem)]"
              : "right-[calc(100%+0.5rem)]",
            status === "idle" && "sr-only",
          )}
        >
          {mobileStatusCopy[status]}
        </p>
      </div>

      <SpiritCustomizer
        open={customizerOpen}
        onOpenChange={setCustomizerOpen}
        appearance={appearance}
        onAppearanceChange={setAppearance}
        mobile
      />
    </>
  );
}

function windowWidthCenter() {
  return typeof window === "undefined" ? 0 : window.innerWidth / 2;
}
