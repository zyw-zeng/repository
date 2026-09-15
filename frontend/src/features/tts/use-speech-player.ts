"use client";

/** 管理按角色自动分句朗读、音频队列、暂停、继续和服务端取消。 */

import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import type {
  SpiritCharacterId,
  SpiritStatus,
} from "@/components/spirit/types";
import { emitSpiritSpeechLevel } from "@/components/spirit/spirit-events";

type SpeechPhase = "idle" | "loading" | "playing" | "paused";

export interface SpeechPlayerState {
  messageId?: string;
  phase: SpeechPhase;
  speed: number;
  automatic: boolean;
}

interface VoiceProfile {
  character_id: SpiritCharacterId;
  enabled: boolean;
  auto_speak: boolean;
}

interface ActiveSpeech {
  messageId: string;
  requestId: string;
  audio: HTMLAudioElement;
  abortController: AbortController;
  objectUrl?: string;
  rejectPlayback: (reason: unknown) => void;
  audioContext?: AudioContext;
  levelFrame?: number;
}

interface RealtimeSession {
  messageId: string;
  characterId: SpiritCharacterId;
  buffer: string;
  receivedText: string;
  queue: string[];
  processing: boolean;
  finishing: boolean;
  stopped: boolean;
  finishWaiters: Array<() => void>;
}

const SPEEDS = [1, 1.25, 1.5] as const;
const MIN_SENTENCE_CHARS = 12;
const MAX_SENTENCE_CHARS = 72;

function createRequestId() {
  return globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random()}`;
}

function startSpeechLevelMeter(current: ActiveSpeech) {
  /** 使用浏览器音频分析器读取真实播放音量；不支持时保留基础说话动画。 */
  if (typeof AudioContext === "undefined") return;
  try {
    const audioContext = new AudioContext();
    const analyser = audioContext.createAnalyser();
    const source = audioContext.createMediaElementSource(current.audio);
    const samples = new Uint8Array(64);
    analyser.fftSize = 64;
    analyser.smoothingTimeConstant = 0.72;
    source.connect(analyser);
    analyser.connect(audioContext.destination);
    current.audioContext = audioContext;
    let lastEmission = 0;

    const updateLevel = (timestamp: number) => {
      if (timestamp - lastEmission >= 50) {
        analyser.getByteTimeDomainData(samples);
        let squaredTotal = 0;
        for (const sample of samples) {
          const centered = (sample - 128) / 128;
          squaredTotal += centered * centered;
        }
        const rms = Math.sqrt(squaredTotal / samples.length);
        emitSpiritSpeechLevel(Math.min(1, rms * 4.5));
        lastEmission = timestamp;
      }
      current.levelFrame = window.requestAnimationFrame(updateLevel);
    };
    void audioContext.resume();
    current.levelFrame = window.requestAnimationFrame(updateLevel);
  } catch {
    // 浏览器限制音频分析时继续正常播放，不影响 TTS 主链路。
  }
}

async function appendSourceBuffer(
  sourceBuffer: SourceBuffer,
  chunk: Uint8Array,
  signal: AbortSignal,
) {
  if (signal.aborted) throw new DOMException("朗读已停止", "AbortError");
  await new Promise<void>((resolve, reject) => {
    const completed = () => {
      cleanup();
      resolve();
    };
    const failed = () => {
      cleanup();
      reject(new Error("浏览器无法继续播放音频流"));
    };
    const aborted = () => {
      cleanup();
      reject(new DOMException("朗读已停止", "AbortError"));
    };
    const cleanup = () => {
      sourceBuffer.removeEventListener("updateend", completed);
      sourceBuffer.removeEventListener("error", failed);
      signal.removeEventListener("abort", aborted);
    };
    sourceBuffer.addEventListener("updateend", completed, { once: true });
    sourceBuffer.addEventListener("error", failed, { once: true });
    signal.addEventListener("abort", aborted, { once: true });
    sourceBuffer.appendBuffer(chunk.slice().buffer);
  });
}

async function responseError(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as {
      error?: { message?: string };
      detail?: string;
    };
    return payload.error?.message ?? payload.detail ?? "语音合成失败";
  } catch {
    return `语音合成失败（${response.status}）`;
  }
}

export function splitReadySpeechSegments(buffer: string): {
  segments: string[];
  remainder: string;
} {
  const segments: string[] = [];
  let remainder = buffer;
  while (remainder.trim()) {
    const boundary = Array.from(remainder).findIndex(
      (character, index) =>
        index + 1 >= MIN_SENTENCE_CHARS && /[。！？!?；;\n]/.test(character),
    );
    if (boundary >= 0) {
      const segment = remainder.slice(0, boundary + 1).trim();
      remainder = remainder.slice(boundary + 1);
      if (segment) segments.push(segment);
      continue;
    }
    if (remainder.length < MAX_SENTENCE_CHARS) break;
    const candidate = remainder.slice(0, MAX_SENTENCE_CHARS);
    const comma = Math.max(
      candidate.lastIndexOf("，"),
      candidate.lastIndexOf(","),
    );
    const splitAt =
      comma >= MIN_SENTENCE_CHARS ? comma + 1 : MAX_SENTENCE_CHARS;
    const segment = remainder.slice(0, splitAt).trim();
    remainder = remainder.slice(splitAt);
    if (segment) segments.push(segment);
  }
  return { segments, remainder };
}

function takeReadySegments(session: RealtimeSession) {
  const result = splitReadySpeechSegments(session.buffer);
  session.queue.push(...result.segments);
  session.buffer = result.remainder;
}

export function useSpeechPlayer(
  onStatusChange: (status: SpiritStatus) => void,
) {
  const [state, setState] = useState<SpeechPlayerState>({
    phase: "idle",
    speed: 1,
    automatic: false,
  });
  const active = useRef<ActiveSpeech | undefined>(undefined);
  const realtime = useRef<RealtimeSession | undefined>(undefined);
  const speedRef = useRef(1);

  const cleanupAudio = useCallback((current: ActiveSpeech) => {
    current.audio.onplaying = null;
    current.audio.onpause = null;
    current.audio.onended = null;
    current.audio.onerror = null;
    current.audio.pause();
    current.audio.removeAttribute("src");
    current.audio.load();
    if (current.levelFrame !== undefined)
      window.cancelAnimationFrame(current.levelFrame);
    if (current.audioContext) void current.audioContext.close();
    emitSpiritSpeechLevel(0);
    if (current.objectUrl) URL.revokeObjectURL(current.objectUrl);
    if (active.current === current) active.current = undefined;
  }, []);

  const cancelActiveAudio = useCallback(
    (notifyServer = true) => {
      const current = active.current;
      if (!current) return;
      if (notifyServer) {
        void fetch(
          `/api/backend/tts/runs/${encodeURIComponent(current.requestId)}/cancel`,
          { method: "POST", keepalive: true },
        ).catch(() => undefined);
      }
      current.abortController.abort();
      current.rejectPlayback(new DOMException("朗读已停止", "AbortError"));
      cleanupAudio(current);
    },
    [cleanupAudio],
  );

  const consumeStream = useCallback(
    async (
      current: ActiveSpeech,
      text: string,
      characterId: SpiritCharacterId,
    ) => {
      const response = await fetch("/api/backend/tts/stream", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "audio/mpeg",
          "X-Request-ID": current.requestId,
        },
        body: JSON.stringify({
          text,
          speech_rate: 1,
          character_id: characterId,
        }),
        signal: current.abortController.signal,
      });
      if (!response.ok) throw new Error(await responseError(response));
      if (!response.body) throw new Error("浏览器没有收到音频流");

      const supportsStreaming =
        typeof MediaSource !== "undefined" &&
        MediaSource.isTypeSupported("audio/mpeg");
      if (!supportsStreaming) {
        const blob = await response.blob();
        current.objectUrl = URL.createObjectURL(blob);
        current.audio.src = current.objectUrl;
        await current.audio.play();
        return;
      }

      const mediaSource = new MediaSource();
      current.objectUrl = URL.createObjectURL(mediaSource);
      current.audio.src = current.objectUrl;
      const playPromise = current.audio.play();
      await new Promise<void>((resolve, reject) => {
        mediaSource.addEventListener("sourceopen", () => resolve(), {
          once: true,
        });
        mediaSource.addEventListener(
          "sourceclose",
          () => reject(new Error("音频流意外关闭")),
          { once: true },
        );
      });
      const sourceBuffer = mediaSource.addSourceBuffer("audio/mpeg");
      const reader = response.body.getReader();
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        if (value?.byteLength)
          await appendSourceBuffer(
            sourceBuffer,
            value,
            current.abortController.signal,
          );
      }
      if (mediaSource.readyState === "open" && !sourceBuffer.updating)
        mediaSource.endOfStream();
      await playPromise;
    },
    [],
  );

  const playOne = useCallback(
    (messageId: string, text: string, characterId: SpiritCharacterId) =>
      new Promise<void>((resolve, reject) => {
        const audio = new Audio();
        let settled = false;
        const settle = (error?: unknown) => {
          if (settled) return;
          settled = true;
          cleanupAudio(current);
          if (error) reject(error);
          else resolve();
        };
        const current: ActiveSpeech = {
          messageId,
          requestId: createRequestId(),
          audio,
          abortController: new AbortController(),
          rejectPlayback: (reason) => settle(reason),
        };
        audio.preload = "auto";
        audio.playbackRate = speedRef.current;
        audio.onplaying = () => {
          if (active.current !== current) return;
          setState((value) => ({ ...value, messageId, phase: "playing" }));
          onStatusChange("speaking");
        };
        audio.onpause = () => {
          if (active.current !== current || audio.ended) return;
          setState((value) => ({ ...value, messageId, phase: "paused" }));
          onStatusChange("idle");
        };
        audio.onended = () => settle();
        audio.onerror = () => settle(new Error("音频播放失败，请重试。"));
        active.current = current;
        startSpeechLevelMeter(current);
        setState((value) => ({ ...value, messageId, phase: "loading" }));
        void consumeStream(current, text, characterId).catch((error) =>
          settle(error),
        );
      }),
    [cleanupAudio, consumeStream, onStatusChange],
  );

  const processQueue = useCallback(async () => {
    const session = realtime.current;
    if (!session || session.processing || session.stopped) return;
    session.processing = true;
    try {
      while (!session.stopped && session.queue.length) {
        const segment = session.queue.shift();
        if (!segment) continue;
        await playOne(session.messageId, segment, session.characterId);
      }
    } catch (error) {
      if ((error as Error).name !== "AbortError") {
        toast.error((error as Error).message || "实时朗读失败，请重试。");
      }
      session.stopped = true;
    } finally {
      session.processing = false;
      if (realtime.current !== session) return;
      if (session.finishing || session.stopped) {
        realtime.current = undefined;
        setState((value) => ({
          phase: "idle",
          speed: value.speed,
          automatic: false,
        }));
        onStatusChange("idle");
        session.finishWaiters.splice(0).forEach((resolve) => resolve());
      } else {
        setState((value) => ({ ...value, phase: "idle" }));
        onStatusChange("answering");
      }
    }
  }, [onStatusChange, playOne]);

  const stop = useCallback(() => {
    const session = realtime.current;
    if (session) {
      session.stopped = true;
      session.queue.length = 0;
      session.buffer = "";
      session.finishWaiters.splice(0).forEach((resolve) => resolve());
      realtime.current = undefined;
    }
    cancelActiveAudio();
    setState((value) => ({
      phase: "idle",
      speed: value.speed,
      automatic: false,
    }));
    onStatusChange("idle");
  }, [cancelActiveAudio, onStatusChange]);

  const startRealtime = useCallback(
    async (messageId: string, characterId: SpiritCharacterId) => {
      try {
        const response = await fetch(
          `/api/backend/tts/profiles/${characterId}`,
          { headers: { Accept: "application/json" } },
        );
        if (!response.ok) throw new Error(await responseError(response));
        const profile = (await response.json()) as VoiceProfile;
        if (!profile.enabled || !profile.auto_speak) return false;
        realtime.current = {
          messageId,
          characterId,
          buffer: "",
          receivedText: "",
          queue: [],
          processing: false,
          finishing: false,
          stopped: false,
          finishWaiters: [],
        };
        setState((value) => ({ ...value, messageId, automatic: true }));
        return true;
      } catch (error) {
        toast.error((error as Error).message || "自动朗读配置读取失败。");
        return false;
      }
    },
    [],
  );

  const appendRealtime = useCallback(
    (delta: string) => {
      const session = realtime.current;
      if (!session || session.stopped || !delta) return;
      session.receivedText += delta;
      session.buffer += delta;
      takeReadySegments(session);
      void processQueue();
    },
    [processQueue],
  );

  const finishRealtime = useCallback(
    (finalAnswer: string) => {
      const session = realtime.current;
      if (!session) return Promise.resolve();
      if (!session.receivedText.trim() && finalAnswer.trim())
        session.buffer = finalAnswer;
      const remaining = session.buffer.trim();
      if (remaining) session.queue.push(remaining);
      session.buffer = "";
      session.finishing = true;
      const completion = new Promise<void>((resolve) =>
        session.finishWaiters.push(resolve),
      );
      void processQueue();
      return completion;
    },
    [processQueue],
  );

  const speak = useCallback(
    async (messageId: string, text: string, characterId: SpiritCharacterId) => {
      const current = active.current;
      if (current?.messageId === messageId) {
        if (current.audio.paused) {
          current.audio.playbackRate = speedRef.current;
          await current.audio.play();
        } else current.audio.pause();
        return;
      }
      stop();
      const session: RealtimeSession = {
        messageId,
        characterId,
        buffer: "",
        receivedText: text,
        queue: [text],
        processing: false,
        finishing: true,
        stopped: false,
        finishWaiters: [],
      };
      realtime.current = session;
      await new Promise<void>((resolve) => {
        session.finishWaiters.push(resolve);
        void processQueue();
      });
    },
    [processQueue, stop],
  );

  const changeSpeed = useCallback(() => {
    setState((value) => {
      const currentIndex = SPEEDS.indexOf(
        value.speed as (typeof SPEEDS)[number],
      );
      const speed = SPEEDS[(currentIndex + 1) % SPEEDS.length];
      speedRef.current = speed;
      if (active.current) active.current.audio.playbackRate = speed;
      return { ...value, speed };
    });
  }, []);

  useEffect(() => () => stop(), [stop]);

  return {
    state,
    speak,
    stop,
    changeSpeed,
    startRealtime,
    appendRealtime,
    finishRealtime,
  };
}
