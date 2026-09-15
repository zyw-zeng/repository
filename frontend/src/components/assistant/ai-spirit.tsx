"use client";

/** 桌面端精灵舞台：组合角色场景、运行反馈、快捷互动和换装入口。 */

import {
  AudioLines,
  BrainCircuit,
  Check,
  MessageCircleMore,
  Settings2,
  Sparkles,
  WifiOff,
} from "lucide-react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { useEffect, useRef, useState } from "react";

import {
  getAccessory,
  getCharacter,
  getOutfit,
} from "@/components/spirit/appearances";
import { SpiritAvatar } from "@/components/spirit/spirit-avatar";
import { SpiritCustomizer } from "@/components/spirit/spirit-customizer";
import {
  askFromSpirit,
  SPIRIT_SPEECH_LEVEL_EVENT,
} from "@/components/spirit/spirit-events";
import { useSpiritAppearance } from "@/components/spirit/spirit-storage";
import type {
  SpiritCharacterId,
  SpiritStatus,
} from "@/components/spirit/types";
import { cn } from "@/lib/utils";

export type { SpiritStatus } from "@/components/spirit/types";

const statusCopy: Record<
  SpiritStatus,
  { label: string; title: string; detail: string }
> = {
  idle: {
    label: "待机中",
    title: "你好呀，想了解 ZYW 的什么？",
    detail: "公开知识库已就绪",
  },
  thinking: {
    label: "检索中",
    title: "我正在知识库里寻找可靠依据…",
    detail: "理解问题 · 检索公开资料",
  },
  answering: {
    label: "回答中",
    title: "找到资料了，正在组织回答。",
    detail: "依据已找到 · 正在生成内容",
  },
  speaking: {
    label: "朗读中",
    title: "我来把这段回答读给你听。",
    detail: "CosyVoice 实时语音播放",
  },
  error: {
    label: "需要重试",
    title: "连接好像走神了，再试一次吧。",
    detail: "对话内容仍然安全保留",
  },
};

const statusIcon: Record<SpiritStatus, typeof MessageCircleMore> = {
  idle: MessageCircleMore,
  thinking: BrainCircuit,
  answering: MessageCircleMore,
  speaking: AudioLines,
  error: WifiOff,
};

const characterPrompts: Record<SpiritCharacterId, string[]> = {
  nova: [
    "介绍一下 ZYW",
    "ZYW 做过哪些有代表性的项目？",
    "这个 AI 小助理是怎么工作的？",
  ],
  byte: [
    "ZYW 的核心技术能力有哪些？",
    "这个项目如何保证引用可靠？",
    "ZYW 有哪些 AI Agent 实践？",
  ],
  momo: [
    "用轻松一点的方式介绍 ZYW",
    "ZYW 最近在研究什么？",
    "我还能继续了解哪些内容？",
  ],
};

const interactionCopy: Record<SpiritCharacterId, string[]> = {
  nova: ["捕捉到一颗新问题！", "星云频道已连接。", "想从哪里认识 ZYW？"],
  byte: [
    "比特已就位，开始解析！",
    "数据节点全部在线。",
    "要不要看看技术细节？",
  ],
  momo: ["沫沫冒个泡～", "今天也适合发现新故事。", "点一个问题继续吧！"],
};

function SpiritScene({ characterId }: { characterId: SpiritCharacterId }) {
  if (characterId === "byte") {
    return (
      <div aria-hidden="true" className="absolute inset-0 overflow-hidden">
        <div className="spirit-byte-grid absolute inset-[10%] opacity-45" />
        {[18, 34, 57, 76].map((left, index) => (
          <motion.span
            key={left}
            className="bg-brand-cyan/70 absolute size-1.5 rounded-sm shadow-[0_0_14px_var(--brand-cyan)]"
            style={{ left: `${left}%`, top: `${22 + index * 15}%` }}
            animate={{ opacity: [0.2, 1, 0.2], scale: [0.75, 1.2, 0.75] }}
            transition={{
              duration: 2.4,
              delay: index * 0.35,
              repeat: Infinity,
            }}
          />
        ))}
      </div>
    );
  }
  if (characterId === "momo") {
    return (
      <div aria-hidden="true" className="absolute inset-0 overflow-hidden">
        {[16, 28, 61, 78, 86].map((left, index) => (
          <motion.span
            key={left}
            className="border-brand-violet/25 bg-brand-cyan/5 absolute rounded-full border backdrop-blur-sm"
            style={{
              left: `${left}%`,
              bottom: `${12 + (index % 3) * 18}%`,
              width: `${18 + index * 5}px`,
              height: `${18 + index * 5}px`,
            }}
            animate={{ y: [18, -30], opacity: [0, 0.7, 0] }}
            transition={{
              duration: 4 + index * 0.4,
              delay: index * 0.5,
              repeat: Infinity,
            }}
          />
        ))}
      </div>
    );
  }
  return (
    <div aria-hidden="true" className="absolute inset-0 overflow-hidden">
      <motion.span
        className="border-brand-indigo/25 absolute top-[20%] left-[14%] h-[48%] w-[72%] rounded-[50%] border"
        animate={{ rotate: 360 }}
        transition={{ duration: 28, repeat: Infinity, ease: "linear" }}
      />
      <motion.span
        className="border-brand-cyan/18 absolute top-[26%] left-[22%] h-[36%] w-[56%] rounded-[50%] border"
        animate={{ rotate: -360 }}
        transition={{ duration: 22, repeat: Infinity, ease: "linear" }}
      />
      {[18, 31, 68, 81].map((left, index) => (
        <motion.span
          key={left}
          className="bg-foreground/60 absolute size-1 rounded-full"
          style={{ left: `${left}%`, top: `${18 + (index % 2) * 46}%` }}
          animate={{ opacity: [0.15, 0.85, 0.15] }}
          transition={{ duration: 2.8, delay: index * 0.55, repeat: Infinity }}
        />
      ))}
    </div>
  );
}

function SpeakingWaves({ level }: { level: number }) {
  return (
    <div
      aria-label="精灵正在朗读"
      className="bg-background/55 border-border/45 absolute top-1/2 right-[5%] z-20 flex h-11 items-center gap-1 rounded-full border px-3 backdrop-blur-md"
    >
      {[0, 1, 2, 3, 4].map((index) => (
        <motion.span
          key={index}
          className="from-brand-cyan to-brand-violet block w-1 rounded-full bg-gradient-to-t"
          animate={{
            height:
              level > 0
                ? 8 + level * (22 - Math.abs(2 - index) * 3)
                : [8, 25 - Math.abs(2 - index) * 4, 8],
          }}
          transition={{ duration: 0.55, delay: index * 0.08, repeat: Infinity }}
        />
      ))}
    </div>
  );
}

export function AiSpirit({ status }: { status: SpiritStatus }) {
  const reduceMotion = useReducedMotion();
  const [appearance, setAppearance] = useSpiritAppearance();
  const [customizerOpen, setCustomizerOpen] = useState(false);
  const [interactionIndex, setInteractionIndex] = useState<number>();
  const [speechLevel, setSpeechLevel] = useState(0);
  const interactionTimer = useRef<number | undefined>(undefined);
  const character = getCharacter(appearance.characterId);
  const outfit = getOutfit(appearance.outfitId);
  const accessory = getAccessory(appearance.accessoryId);
  const currentStatus = statusCopy[status];
  const StatusIcon = statusIcon[status];

  useEffect(
    () => () => {
      if (interactionTimer.current)
        window.clearTimeout(interactionTimer.current);
    },
    [],
  );

  useEffect(() => {
    const updateSpeechLevel = (event: Event) => {
      const level = (event as CustomEvent<unknown>).detail;
      if (typeof level === "number") setSpeechLevel(level);
    };
    window.addEventListener(SPIRIT_SPEECH_LEVEL_EVENT, updateSpeechLevel);
    return () =>
      window.removeEventListener(SPIRIT_SPEECH_LEVEL_EVENT, updateSpeechLevel);
  }, []);

  function interact() {
    setInteractionIndex((current) =>
      current === undefined
        ? 0
        : (current + 1) % interactionCopy[appearance.characterId].length,
    );
    if (interactionTimer.current) window.clearTimeout(interactionTimer.current);
    interactionTimer.current = window.setTimeout(
      () => setInteractionIndex(undefined),
      6500,
    );
  }

  return (
    <section
      data-spirit-status={status}
      data-spirit-character={appearance.characterId}
      className="border-border/60 relative grid min-h-0 grid-rows-[auto_1fr_auto] overflow-hidden border-r px-[clamp(1rem,2.4vw,2.5rem)] py-[clamp(1rem,2.5vh,2rem)]"
    >
      <div
        aria-hidden="true"
        className="subtle-grid absolute inset-0 opacity-55"
      />
      <div
        aria-hidden="true"
        className={cn(
          "absolute inset-0 transition-colors duration-700",
          appearance.characterId === "nova" &&
            "bg-[radial-gradient(circle_at_50%_44%,color-mix(in_oklch,var(--brand-indigo)_17%,transparent),transparent_42%)]",
          appearance.characterId === "byte" &&
            "bg-[radial-gradient(circle_at_50%_44%,color-mix(in_oklch,var(--brand-cyan)_15%,transparent),transparent_44%)]",
          appearance.characterId === "momo" &&
            "bg-[radial-gradient(circle_at_50%_44%,color-mix(in_oklch,var(--brand-violet)_15%,transparent),transparent_44%)]",
        )}
      />

      <header className="glass-panel relative z-30 flex min-w-0 items-center justify-between gap-3 rounded-2xl px-3.5 py-3">
        <div className="flex min-w-0 items-center gap-2.5">
          <span
            className="size-2.5 shrink-0 rounded-full shadow-[0_0_12px_currentColor]"
            style={{
              color: character.colors[0],
              backgroundColor: character.colors[0],
            }}
          />
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold">
              {character.name}
              <span className="text-muted-foreground ml-1.5 text-[10px] font-normal tracking-wider uppercase">
                在线
              </span>
            </p>
            <p className="text-muted-foreground truncate text-[10px]">
              {outfit.name}装扮
              {accessory.id !== "none" ? ` · ${accessory.name}` : ""}
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={() => setCustomizerOpen(true)}
          aria-label="打开精灵换装间"
          className="hover:bg-primary/10 hover:text-primary flex shrink-0 items-center gap-1.5 rounded-xl px-2.5 py-2 text-xs transition-colors"
        >
          <Settings2 className="size-3.5" /> 换装
        </button>
      </header>

      <div className="relative z-10 flex min-h-0 items-center justify-center">
        <SpiritScene characterId={appearance.characterId} />
        <motion.div
          aria-hidden="true"
          className={cn(
            "absolute size-[min(76%,32rem)] rounded-full blur-3xl transition-colors duration-500",
            status === "thinking" && "bg-brand-cyan/24",
            status === "answering" && "bg-brand-indigo/26",
            status === "speaking" && "bg-brand-violet/28",
            status === "error" && "bg-destructive/18",
            status === "idle" && "bg-brand-indigo/17",
          )}
          animate={
            reduceMotion
              ? undefined
              : { scale: [0.88, 1.06, 0.88], opacity: [0.4, 0.72, 0.4] }
          }
          transition={{ duration: 5, repeat: Infinity, ease: "easeInOut" }}
        />

        <AnimatePresence>
          {interactionIndex !== undefined && (
            <motion.div
              initial={
                reduceMotion ? false : { opacity: 0, y: 10, scale: 0.96 }
              }
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 6, scale: 0.98 }}
              className="glass-panel absolute top-[7%] left-1/2 z-30 w-[min(92%,27rem)] -translate-x-1/2 rounded-2xl p-3.5"
            >
              <p className="flex items-center gap-2 text-sm font-medium">
                <Sparkles className="text-primary size-4" />
                {interactionCopy[appearance.characterId][interactionIndex]}
              </p>
              <div className="mt-3 flex flex-wrap gap-1.5">
                {characterPrompts[appearance.characterId].map((prompt) => (
                  <button
                    key={prompt}
                    type="button"
                    onClick={() => {
                      askFromSpirit(prompt);
                      setInteractionIndex(undefined);
                    }}
                    className="bg-background/55 hover:border-primary/45 hover:bg-primary/8 rounded-full border px-2.5 py-1.5 text-[10px] leading-4 transition-colors"
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        <button
          type="button"
          onClick={interact}
          aria-label={`和${character.name}互动`}
          className="group relative z-20 rounded-[30%] outline-none focus-visible:ring-4 focus-visible:ring-indigo-400/40"
        >
          <motion.span
            aria-hidden="true"
            className={cn(
              "absolute inset-[12%] rounded-full border opacity-60",
              status === "error"
                ? "border-destructive/50"
                : "border-primary/35",
            )}
            animate={
              reduceMotion || status === "idle"
                ? undefined
                : { scale: [0.92, 1.09], opacity: [0.55, 0] }
            }
            transition={{ duration: 1.4, repeat: Infinity, ease: "easeOut" }}
          />
          <motion.div
            key={`${appearance.characterId}-${interactionIndex ?? "rest"}`}
            animate={
              reduceMotion || interactionIndex === undefined
                ? undefined
                : { rotate: [0, -2.5, 3, -1.5, 0], y: [0, -5, 0] }
            }
            transition={{ duration: 0.65 }}
            className="spirit-stage-avatar transition-transform duration-300 group-hover:scale-[1.025]"
          >
            <SpiritAvatar
              appearance={appearance}
              status={status}
              speechLevel={speechLevel}
            />
          </motion.div>
        </button>

        <div
          aria-hidden="true"
          className="absolute bottom-[17%] left-1/2 h-16 w-[68%] max-w-sm -translate-x-1/2"
        >
          <motion.div
            className="border-primary/22 absolute inset-x-[9%] bottom-2 h-12 rounded-[50%] border"
            animate={
              reduceMotion
                ? undefined
                : { scaleX: [0.9, 1.04, 0.9], opacity: [0.45, 0.8, 0.45] }
            }
            transition={{ duration: 3.2, repeat: Infinity, ease: "easeInOut" }}
          />
          <div className="bg-primary/16 absolute inset-x-[18%] bottom-0 h-4 rounded-[50%] blur-md" />
          <div className="border-brand-cyan/20 absolute inset-x-[26%] bottom-4 h-5 rounded-[50%] border" />
        </div>
        {status === "speaking" && <SpeakingWaves level={speechLevel} />}
      </div>

      <motion.div
        key={status}
        role="status"
        initial={reduceMotion ? false : { opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass-panel relative z-30 mx-auto w-full max-w-md rounded-2xl px-4 py-3.5"
      >
        <div className="flex items-start gap-3">
          <span className="bg-primary/10 text-primary grid size-9 shrink-0 place-items-center rounded-xl">
            <StatusIcon className="size-4" />
          </span>
          <div className="min-w-0 flex-1">
            <div className="flex items-center justify-between gap-2">
              <p className="text-sm font-medium">{currentStatus.title}</p>
              <span className="text-primary shrink-0 text-[9px] font-semibold tracking-[0.12em] uppercase">
                {currentStatus.label}
              </span>
            </div>
            <p className="text-muted-foreground mt-1 flex items-center gap-1.5 text-[10px]">
              {status === "idle" ? (
                <Check className="size-3" />
              ) : (
                <Sparkles className="size-3" />
              )}
              {currentStatus.detail}
            </p>
          </div>
        </div>
      </motion.div>

      <SpiritCustomizer
        open={customizerOpen}
        onOpenChange={setCustomizerOpen}
        appearance={appearance}
        onAppearanceChange={setAppearance}
      />
    </section>
  );
}
