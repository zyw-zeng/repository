"use client";

/** 使用分层 SVG 重绘 ZYW 星核精灵，并将 Agent 状态映射为表情与动作。 */

import { motion, useReducedMotion } from "motion/react";
import { useId } from "react";

import { cn } from "@/lib/utils";

import { getCharacter } from "./appearances";
import type { SpiritAppearance, SpiritStatus } from "./types";

interface SpiritAvatarProps {
  appearance: SpiritAppearance;
  status: SpiritStatus;
  className?: string;
  decorative?: boolean;
  speechLevel?: number;
}

export function SpiritAvatar({
  appearance,
  status,
  className,
  decorative = false,
  speechLevel = 0,
}: SpiritAvatarProps) {
  const reduceMotion = useReducedMotion();
  const character = getCharacter(appearance.characterId);
  const id = useId().replace(/:/g, "");
  const bodyGradient = `starcore-body-${id}`;
  const eyeGradient = `starcore-eye-${id}`;
  const coreGradient = `starcore-core-${id}`;
  const softGlow = `starcore-glow-${id}`;
  const isSpeaking = status === "speaking";
  const isWorking =
    status === "thinking" || status === "answering" || isSpeaking;
  const isError = status === "error";

  return (
    <motion.svg
      viewBox="0 0 320 320"
      role={decorative ? undefined : "img"}
      aria-hidden={decorative || undefined}
      aria-label={decorative ? undefined : `${character.name} ZYW 星核精灵`}
      className={cn("size-full overflow-visible", className)}
      animate={
        reduceMotion
          ? undefined
          : {
              y: isWorking ? [0, -6, 0] : [0, -4, 0],
              rotate: isError ? [0, -2, 2, 0] : [0, 0.7, 0],
            }
      }
      transition={{
        y: {
          duration: isWorking ? 1.55 : 4,
          repeat: Infinity,
          ease: "easeInOut",
        },
        rotate: {
          duration: isError ? 0.42 : 4,
          repeat: Infinity,
          ease: "easeInOut",
        },
      }}
    >
      <defs>
        <linearGradient id={bodyGradient} x1="91" y1="62" x2="236" y2="264">
          <stop stopColor="#f7fbff" />
          <stop
            offset="0.38"
            stopColor={character.colors[0]}
            stopOpacity="0.72"
          />
          <stop
            offset="0.78"
            stopColor={character.colors[1]}
            stopOpacity="0.68"
          />
          <stop offset="1" stopColor="#a78bfa" stopOpacity="0.86" />
        </linearGradient>
        <radialGradient id={eyeGradient} cx="38%" cy="28%" r="78%">
          <stop stopColor="#35447c" />
          <stop offset="0.58" stopColor="#172554" />
          <stop offset="1" stopColor="#080d24" />
        </radialGradient>
        <radialGradient id={coreGradient} cx="50%" cy="42%" r="66%">
          <stop stopColor="#fff" />
          <stop offset="0.35" stopColor="#fff7c2" />
          <stop offset="0.72" stopColor="#fcd66d" />
          <stop offset="1" stopColor="#f3a83b" />
        </radialGradient>
        <filter id={softGlow} x="-80%" y="-80%" width="260%" height="260%">
          <feGaussianBlur stdDeviation="8" />
        </filter>
      </defs>

      {/* 悬浮阴影和角色反向缩放，保持轻盈的离地感。 */}
      <motion.ellipse
        cx="160"
        cy="287"
        rx="55"
        ry="10"
        fill="#111827"
        opacity="0.2"
        animate={
          reduceMotion
            ? undefined
            : { scaleX: [1, 0.84, 1], opacity: [0.2, 0.11, 0.2] }
        }
        transition={{
          duration: isWorking ? 1.55 : 4,
          repeat: Infinity,
          ease: "easeInOut",
        }}
        style={{ transformOrigin: "160px 287px" }}
      />

      {/* 思考状态围绕角色运行少量星尘。 */}
      {status === "thinking" && (
        <motion.g
          aria-hidden="true"
          animate={reduceMotion ? undefined : { rotate: 360 }}
          transition={{ duration: 3.4, repeat: Infinity, ease: "linear" }}
          style={{ transformOrigin: "160px 163px" }}
        >
          <circle cx="160" cy="23" r="4" fill="#fef3c7" />
          <circle cx="287" cy="174" r="3" fill="#67e8f9" />
          <circle cx="55" cy="238" r="2.5" fill="#c4b5fd" />
        </motion.g>
      )}

      {appearance.characterId === "nova" ? (
        <>
          {/* 星云：彗星尾和耳翼位于主体后方。 */}
          <motion.path
            d="M158 225c20 29 52 36 78 28 20-6 31 2 42 19-20-4-26 4-31 18-8-12-17-17-31-13-34 9-65-10-74-38Z"
            fill={`url(#${bodyGradient})`}
            stroke="#fff"
            strokeOpacity="0.22"
            strokeWidth="2.5"
            animate={reduceMotion ? undefined : { rotate: [0, 3, -2, 0] }}
            transition={{ duration: 3.2, repeat: Infinity, ease: "easeInOut" }}
            style={{ transformOrigin: "161px 231px" }}
          />
          <path
            d="M91 98c-24 0-43-14-55-35 25 8 44 2 62-13 8 20 6 34-7 48Z"
            fill={`url(#${bodyGradient})`}
            stroke="#fff"
            strokeOpacity="0.28"
            strokeWidth="2.5"
          />
          <path
            d="M229 97c24 0 43-14 55-35-25 8-44 2-62-13-8 20-6 34 7 48Z"
            fill={`url(#${bodyGradient})`}
            stroke="#fff"
            strokeOpacity="0.28"
            strokeWidth="2.5"
          />
          <path
            d="M71 79c9 4 16 4 24-2"
            fill="none"
            stroke="#c4b5fd"
            strokeWidth="5"
            strokeLinecap="round"
            opacity="0.62"
          />
          <path
            d="M249 79c-9 4-16 4-24-2"
            fill="none"
            stroke="#c4b5fd"
            strokeWidth="5"
            strokeLinecap="round"
            opacity="0.62"
          />

          {/* 身体背光仅用于柔化边缘，主体本身保持清晰。 */}
          <ellipse
            cx="160"
            cy="183"
            rx="82"
            ry="97"
            fill={character.colors[0]}
            opacity="0.22"
            filter={`url(#${softGlow})`}
          />

          {/* 小巧身体承托星核，头身比例保持亲和。 */}
          <path
            d="M112 175c-17 22-25 58-14 81 12 26 38 33 62 20 24 13 50 6 62-20 11-23 3-59-14-81Z"
            fill={`url(#${bodyGradient})`}
            stroke="#fff"
            strokeOpacity="0.25"
            strokeWidth="3"
          />

          {/* 头部使用柔和的不对称轮廓，避免圆形贴纸感。 */}
          <path
            d="M160 49c-53-1-88 32-87 82 1 54 37 85 87 86 50-1 86-32 87-86 1-50-34-83-87-82Z"
            fill={`url(#${bodyGradient})`}
            stroke="#fff"
            strokeOpacity="0.3"
            strokeWidth="3"
          />
          <path
            d="M101 91c17-23 43-32 72-30 16 1 28 5 38 12"
            fill="none"
            stroke="#fff"
            strokeOpacity="0.48"
            strokeWidth="9"
            strokeLinecap="round"
          />

          {/* Z 形发梢形成稳定的品牌剪影。 */}
          <path
            d="M144 58c-6-15 3-31 26-42-7 13-3 21 13 25 13 3 19 12 14 25-4-10-11-13-24-12-11 1-20 2-29 4Z"
            fill={`url(#${bodyGradient})`}
            stroke="#fff"
            strokeOpacity="0.28"
            strokeWidth="2.5"
            strokeLinejoin="round"
          />
        </>
      ) : appearance.characterId === "byte" ? (
        <ByteSilhouette
          bodyGradient={bodyGradient}
          glow={softGlow}
          reduceMotion={Boolean(reduceMotion)}
        />
      ) : (
        <MomoSilhouette
          bodyGradient={bodyGradient}
          glow={softGlow}
          reduceMotion={Boolean(reduceMotion)}
        />
      )}

      <OutfitLayer appearance={appearance} />

      <FaceLayer
        eyeGradient={eyeGradient}
        status={status}
        reduceMotion={Boolean(reduceMotion)}
        speechLevel={speechLevel}
      />

      {/* 胸口星核是角色视觉中心，也承担运行状态提示。 */}
      <motion.path
        d="m160 205 10 18 20 10-20 10-10 19-10-19-20-10 20-10Z"
        fill={isError ? "#fda4af" : `url(#${coreGradient})`}
        opacity="1"
        stroke="#fff"
        strokeWidth="3"
        strokeLinejoin="round"
        animate={
          reduceMotion
            ? undefined
            : {
                scale: isWorking ? [0.9, 1.12, 0.9] : [0.96, 1.04, 0.96],
                opacity: isError ? [0.55, 1, 0.55] : 1,
              }
        }
        transition={{ duration: isWorking ? 1.05 : 2.8, repeat: Infinity }}
        style={{ transformOrigin: "160px 233px" }}
      />
      <path
        d="m160 214 5 11 11 7-11 5-5 12-5-12-11-5 11-7Z"
        fill="#fff"
        opacity="0.64"
      />

      {/* 漂浮双手脱离身体，动作更轻巧，也便于后续扩展。 */}
      <motion.path
        d="M76 189c-15-7-28 5-25 20 3 13 17 19 29 13 12-6 13-25-4-33Z"
        fill={`url(#${bodyGradient})`}
        stroke="#fff"
        strokeOpacity="0.28"
        strokeWidth="2.5"
        animate={
          reduceMotion
            ? undefined
            : { x: [0, -3, 0], y: [0, 4, 0], rotate: [0, -7, 0] }
        }
        transition={{ duration: 2.6, repeat: Infinity, ease: "easeInOut" }}
        style={{ transformOrigin: "67px 205px" }}
      />
      <motion.path
        d="M244 189c15-7 28 5 25 20-3 13-17 19-29 13-12-6-13-25 4-33Z"
        fill={`url(#${bodyGradient})`}
        stroke="#fff"
        strokeOpacity="0.28"
        strokeWidth="2.5"
        animate={
          reduceMotion
            ? undefined
            : {
                x: [0, 3, 0],
                y:
                  status === "answering" || isSpeaking
                    ? [0, -10, 0]
                    : [0, 4, 0],
                rotate:
                  status === "answering" || isSpeaking
                    ? [0, 15, -5, 0]
                    : [0, 7, 0],
              }
        }
        transition={{
          duration: status === "answering" || isSpeaking ? 1.1 : 2.6,
          repeat: Infinity,
          ease: "easeInOut",
        }}
        style={{ transformOrigin: "253px 205px" }}
      />

      <AccessoryLayer appearance={appearance} />
    </motion.svg>
  );
}

/** 比特使用切角轮廓、电路天线和离散像素尾，形成清晰的数据精灵特征。 */
function ByteSilhouette({
  bodyGradient,
  glow,
  reduceMotion,
}: {
  bodyGradient: string;
  glow: string;
  reduceMotion: boolean;
}) {
  return (
    <g>
      <ellipse
        cx="160"
        cy="179"
        rx="80"
        ry="95"
        fill="#34d399"
        opacity="0.18"
        filter={`url(#${glow})`}
      />
      {/* 像素尾由三个独立数据块组成。 */}
      <motion.g
        animate={reduceMotion ? undefined : { x: [0, 5, 0], y: [0, -3, 0] }}
        transition={{ duration: 2.4, repeat: Infinity, ease: "easeInOut" }}
      >
        <rect
          x="220"
          y="245"
          width="31"
          height="31"
          rx="9"
          fill={`url(#${bodyGradient})`}
          transform="rotate(18 235 260)"
        />
        <rect
          x="258"
          y="259"
          width="22"
          height="22"
          rx="7"
          fill="#60a5fa"
          opacity="0.78"
          transform="rotate(18 269 270)"
        />
        <rect
          x="287"
          y="275"
          width="13"
          height="13"
          rx="4"
          fill="#34d399"
          opacity="0.7"
          transform="rotate(18 293 281)"
        />
      </motion.g>
      {/* 两侧数据翼采用切角几何结构。 */}
      <path
        d="M86 99 47 77l13 44 31 17 13-26Z"
        fill={`url(#${bodyGradient})`}
        stroke="#fff"
        strokeOpacity="0.28"
        strokeWidth="2.5"
        strokeLinejoin="round"
      />
      <path
        d="m234 99 39-22-13 44-31 17-13-26Z"
        fill={`url(#${bodyGradient})`}
        stroke="#fff"
        strokeOpacity="0.28"
        strokeWidth="2.5"
        strokeLinejoin="round"
      />
      <path
        d="M112 174 94 205l8 54 31 23h54l31-23 8-54-18-31Z"
        fill={`url(#${bodyGradient})`}
        stroke="#fff"
        strokeOpacity="0.26"
        strokeWidth="3"
        strokeLinejoin="round"
      />
      <path
        d="M104 82 128 55h64l24 27 17 45-17 58-29 27h-54l-29-27-17-58Z"
        fill={`url(#${bodyGradient})`}
        stroke="#fff"
        strokeOpacity="0.32"
        strokeWidth="3"
        strokeLinejoin="round"
      />
      <path
        d="M115 85c18-17 42-23 69-17"
        fill="none"
        stroke="#fff"
        strokeOpacity="0.48"
        strokeWidth="8"
        strokeLinecap="round"
      />
      {/* 头顶节点沿电路线轻微脉冲。 */}
      <path
        d="M160 55V34l18-12"
        fill="none"
        stroke="#7dd3fc"
        strokeWidth="4"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <motion.rect
        x="173"
        y="16"
        width="13"
        height="13"
        rx="4"
        fill="#34d399"
        animate={
          reduceMotion
            ? undefined
            : { opacity: [0.45, 1, 0.45], rotate: [0, 90, 0] }
        }
        transition={{ duration: 1.8, repeat: Infinity }}
        style={{ transformOrigin: "179.5px 22.5px" }}
      />
      <path
        d="M96 124h14m100 0h14M160 69v-9"
        stroke="#67e8f9"
        strokeWidth="3"
        strokeLinecap="round"
        opacity="0.7"
      />
    </g>
  );
}

/** 沫沫使用月滴轮廓、圆耳和泡泡尾，整体更柔软活泼。 */
function MomoSilhouette({
  bodyGradient,
  glow,
  reduceMotion,
}: {
  bodyGradient: string;
  glow: string;
  reduceMotion: boolean;
}) {
  return (
    <g>
      <ellipse
        cx="160"
        cy="180"
        rx="91"
        ry="101"
        fill="#fb7185"
        opacity="0.16"
        filter={`url(#${glow})`}
      />
      {/* 泡泡尾会沿右下方缓慢漂移。 */}
      <motion.g
        animate={reduceMotion ? undefined : { y: [0, -5, 0], x: [0, 3, 0] }}
        transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
      >
        <circle
          cx="230"
          cy="250"
          r="25"
          fill={`url(#${bodyGradient})`}
          stroke="#fff"
          strokeOpacity="0.22"
          strokeWidth="2.5"
        />
        <circle cx="268" cy="268" r="15" fill="#f9a8d4" opacity="0.75" />
        <circle cx="295" cy="286" r="8" fill="#fbbf24" opacity="0.7" />
      </motion.g>
      {/* 圆耳让轮廓与星云的尖耳翼明显区分。 */}
      <circle
        cx="88"
        cy="104"
        r="28"
        fill={`url(#${bodyGradient})`}
        stroke="#fff"
        strokeOpacity="0.28"
        strokeWidth="2.5"
      />
      <circle
        cx="232"
        cy="104"
        r="28"
        fill={`url(#${bodyGradient})`}
        stroke="#fff"
        strokeOpacity="0.28"
        strokeWidth="2.5"
      />
      <circle cx="88" cy="104" r="13" fill="#f9a8d4" opacity="0.42" />
      <circle cx="232" cy="104" r="13" fill="#f9a8d4" opacity="0.42" />
      <path
        d="M103 176c-19 25-25 63-10 87 14 23 41 28 67 13 26 15 53 10 67-13 15-24 9-62-10-87Z"
        fill={`url(#${bodyGradient})`}
        stroke="#fff"
        strokeOpacity="0.26"
        strokeWidth="3"
      />
      <path
        d="M160 49c-56 0-91 34-88 86 3 53 39 82 88 82s85-29 88-82c3-52-32-86-88-86Z"
        fill={`url(#${bodyGradient})`}
        stroke="#fff"
        strokeOpacity="0.32"
        strokeWidth="3"
      />
      <path
        d="M101 91c19-22 46-30 77-26"
        fill="none"
        stroke="#fff"
        strokeOpacity="0.5"
        strokeWidth="9"
        strokeLinecap="round"
      />
      {/* 月滴发梢比星云的 Z 发梢更圆。 */}
      <path
        d="M145 55c-2-18 10-31 32-38-9 11-7 21 7 29-11-1-18 3-24 14Z"
        fill={`url(#${bodyGradient})`}
        stroke="#fff"
        strokeOpacity="0.28"
        strokeWidth="2.5"
      />
      <motion.circle
        cx="194"
        cy="45"
        r="7"
        fill="#fbbf24"
        opacity="0.82"
        animate={reduceMotion ? undefined : { scale: [0.75, 1.1, 0.75] }}
        transition={{ duration: 2, repeat: Infinity }}
        style={{ transformOrigin: "194px 45px" }}
      />
    </g>
  );
}

/** 五官层负责眨眼、说话和错误表情。 */
function FaceLayer({
  eyeGradient,
  status,
  reduceMotion,
  speechLevel,
}: {
  eyeGradient: string;
  status: SpiritStatus;
  reduceMotion: boolean;
  speechLevel: number;
}) {
  const isError = status === "error";
  return (
    <g>
      <path
        d={
          isError
            ? "M105 119q17-13 31 1M184 120q15-14 31-1"
            : "M105 112q16-10 30 1M185 113q14-11 30-1"
        }
        fill="none"
        stroke="#303b72"
        strokeWidth="4"
        strokeLinecap="round"
      />
      {[124, 196].map((x, index) => (
        <motion.g key={x}>
          <motion.ellipse
            cx={x}
            cy="143"
            rx="22"
            ry="28"
            fill={`url(#${eyeGradient})`}
            animate={reduceMotion ? undefined : { scaleY: [1, 1, 0.08, 1, 1] }}
            transition={{
              duration: 4.8 + index * 0.2,
              repeat: Infinity,
              times: [0, 0.47, 0.5, 0.53, 1],
            }}
            style={{ transformOrigin: `${x}px 143px` }}
          />
          <circle cx={x - 7} cy="134" r="5" fill="#fff" />
          <circle cx={x + 6} cy="153" r="3.2" fill="#67e8f9" />
          <path
            d={`m${x + 4} 128 3 6 6 3-6 3-3 6-3-6-6-3 6-3Z`}
            fill="#fff2b4"
          />
        </motion.g>
      ))}
      <ellipse cx="96" cy="170" rx="15" ry="6" fill="#f9a8d4" opacity="0.4" />
      <ellipse cx="224" cy="170" rx="15" ry="6" fill="#f9a8d4" opacity="0.4" />
      {isError ? (
        <path
          d="M150 184q10-8 20 0"
          fill="none"
          stroke="#303b72"
          strokeWidth="4"
          strokeLinecap="round"
        />
      ) : status === "answering" || status === "speaking" ? (
        <motion.ellipse
          cx="160"
          cy="183"
          rx="8"
          ry={status === "speaking" ? 4.5 + speechLevel * 4 : 5}
          fill="#303b72"
          animate={
            reduceMotion
              ? undefined
              : status === "speaking" && speechLevel > 0
                ? { scaleY: 0.75 + speechLevel * 1.1 }
                : { scaleY: [0.65, 1.45, 0.65] }
          }
          transition={{
            duration: status === "speaking" ? 0.32 : 0.5,
            repeat: Infinity,
          }}
          style={{ transformOrigin: "160px 183px" }}
        />
      ) : (
        <path
          d="M149 180q11 11 22 0"
          fill="none"
          stroke="#303b72"
          strokeWidth="4"
          strokeLinecap="round"
        />
      )}
    </g>
  );
}

/** 服装作为身体与头部之间的独立层，不改变核心角色轮廓。 */
function OutfitLayer({ appearance }: { appearance: SpiritAppearance }) {
  if (appearance.outfitId === "coder") {
    return (
      <g>
        <path
          d="M109 190q51 22 102 0 8 13 10 28l-31 13-30-17-30 17-31-13q2-15 10-28Z"
          fill="#172033"
          fillOpacity="0.9"
        />
        <path
          d="m150 207 10 9 10-9"
          fill="none"
          stroke="#67e8f9"
          strokeWidth="3.5"
          strokeLinecap="round"
        />
      </g>
    );
  }
  if (appearance.outfitId === "explorer") {
    return (
      <g>
        <path
          d="M105 190q55 25 110 0"
          fill="none"
          stroke="#fbbf24"
          strokeWidth="12"
          strokeLinecap="round"
        />
        <path
          d="M204 196q4 21-5 42"
          fill="none"
          stroke="#f59e0b"
          strokeWidth="10"
          strokeLinecap="round"
        />
      </g>
    );
  }
  return null;
}

/** 配饰保持轻量，避免遮挡 Z 形发梢和星核。 */
function AccessoryLayer({ appearance }: { appearance: SpiritAppearance }) {
  if (appearance.accessoryId === "headphones") {
    return (
      <g>
        <path
          d="M89 139c-7-62 24-96 71-96s78 34 71 96"
          fill="none"
          stroke="#26324d"
          strokeWidth="8"
          strokeLinecap="round"
        />
        <rect
          x="78"
          y="128"
          width="20"
          height="43"
          rx="10"
          fill="#26324d"
          stroke="#67e8f9"
          strokeWidth="4"
        />
        <rect
          x="222"
          y="128"
          width="20"
          height="43"
          rx="10"
          fill="#26324d"
          stroke="#c4b5fd"
          strokeWidth="4"
        />
      </g>
    );
  }
  if (appearance.accessoryId === "cap") {
    return (
      <g>
        <path d="M101 74q14-44 64-42 42 2 56 42Z" fill="#24314f" />
        <path d="M163 72q46-7 70 11-34 9-72 2Z" fill="#5365d8" />
        <path
          d="M130 48q29-14 57 1"
          fill="none"
          stroke="#67e8f9"
          strokeWidth="4"
          strokeLinecap="round"
        />
      </g>
    );
  }
  return null;
}
