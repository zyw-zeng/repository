/** 在精灵舞台与聊天面板之间传递快捷问题，保持两个组件独立。 */

export const SPIRIT_QUESTION_EVENT = "zyw:spirit-question";
export const SPIRIT_SPEECH_LEVEL_EVENT = "zyw:spirit-speech-level";

export function askFromSpirit(question: string) {
  window.dispatchEvent(
    new CustomEvent<string>(SPIRIT_QUESTION_EVENT, { detail: question }),
  );
}

export function emitSpiritSpeechLevel(level: number) {
  /** 音量值限制在 0～1，供嘴部和声波组件安全消费。 */
  window.dispatchEvent(
    new CustomEvent<number>(SPIRIT_SPEECH_LEVEL_EVENT, {
      detail: Math.max(0, Math.min(1, level)),
    }),
  );
}
