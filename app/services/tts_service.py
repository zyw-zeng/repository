"""提供可替换的语音合成边界、CosyVoice 流式实现与任务取消。"""

import hashlib
import logging
import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from queue import Empty, Full, Queue
from threading import Event, Lock, Thread
from typing import Protocol

import dashscope
from dashscope.audio.tts_v2 import AudioFormat, ResultCallback, SpeechSynthesizer

from app.core.config import Settings
from app.core.exceptions import AppError

logger = logging.getLogger(__name__)

_STREAM_END = object()


def normalize_speech_text(text: str) -> str:
    """移除不适合朗读的 Markdown 标记和引用编号，同时保留自然段。"""
    normalized = re.sub(r"```[\s\S]*?```", "代码片段。", text)
    normalized = re.sub(r"!\[([^]]*)]\([^)]+\)", r"\1", normalized)
    normalized = re.sub(r"\[([^]]+)]\([^)]+\)", r"\1", normalized)
    normalized = re.sub(r"(?<!\w)\[\d+(?:\]\[\d+)*]", "", normalized)
    normalized = re.sub(r"[`*_>#~-]+", "", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized.strip()


class StreamingSpeechProvider(Protocol):
    """约束流式语音提供方，后续实时分句模式继续复用此边界。"""

    media_type: str

    def stream(self, run: "SpeechRun", text: str, speech_rate: float) -> None:
        """把音频块持续写入运行对象，完成或失败时必须结束运行。"""


@dataclass
class SpeechRun:
    """保存一次合成的队列、取消信号和底层提供方句柄。"""

    request_id: str
    chunks: Queue[bytes | BaseException | object] = field(default_factory=lambda: Queue(64))
    cancelled: Event = field(default_factory=Event)
    completed: Event = field(default_factory=Event)
    _synthesizer: SpeechSynthesizer | None = None
    _lock: Lock = field(default_factory=Lock)

    def attach(self, synthesizer: SpeechSynthesizer) -> None:
        """关联底层合成器；处理取消早于连接建立的竞态。"""
        with self._lock:
            self._synthesizer = synthesizer
            should_cancel = self.cancelled.is_set()
        if should_cancel:
            self._cancel_synthesizer(synthesizer)

    def put(self, item: bytes | BaseException | object) -> None:
        """向有界队列写入数据，并在客户端取消后停止等待。"""
        while not self.cancelled.is_set():
            try:
                self.chunks.put(item, timeout=0.2)
                return
            except Full:
                continue

    def finish(self) -> None:
        """结束输出流；结束标记只发送一次。"""
        if self.completed.is_set():
            return
        self.completed.set()
        if self.cancelled.is_set():
            # 取消时丢弃尚未播放的数据，保证停止按钮立即生效。
            while True:
                try:
                    self.chunks.get_nowait()
                except Empty:
                    break
            self.chunks.put_nowait(_STREAM_END)
            return
        # 正常完成时等待消费者腾出空间，不能丢弃任何音频块。
        while True:
            if self.cancelled.is_set():
                while True:
                    try:
                        self.chunks.get_nowait()
                    except Empty:
                        break
                self.chunks.put_nowait(_STREAM_END)
                return
            try:
                self.chunks.put(_STREAM_END, timeout=0.2)
                return
            except Full:
                continue

    def cancel(self) -> None:
        """取消云端合成并立即唤醒等待中的 HTTP 流。"""
        self.cancelled.set()
        with self._lock:
            synthesizer = self._synthesizer
        if synthesizer is not None:
            self._cancel_synthesizer(synthesizer)
        self.finish()

    @staticmethod
    def _cancel_synthesizer(synthesizer: SpeechSynthesizer) -> None:
        """优先发送 CosyVoice 取消指令，异常时关闭连接作为兜底。"""
        try:
            synthesizer.streaming_cancel()
        except Exception:
            logger.debug("CosyVoice 取消指令失败，改为关闭连接", exc_info=True)
            try:
                synthesizer.close()
            except Exception:
                logger.debug("关闭 CosyVoice 连接失败", exc_info=True)


class SpeechRunRegistry:
    """维护当前进程内的活动语音任务，未来可替换为共享任务存储。"""

    def __init__(self) -> None:
        self._runs: dict[str, SpeechRun] = {}
        self._lock = Lock()

    def create(self, request_id: str) -> SpeechRun:
        """创建唯一运行，避免重复请求误操作同一条音频流。"""
        with self._lock:
            if request_id in self._runs:
                raise AppError("语音任务正在执行", status_code=409, code="tts_request_active")
            run = SpeechRun(request_id=request_id)
            self._runs[request_id] = run
            return run

    def cancel(self, request_id: str) -> bool:
        """取消仍然活动的任务；已完成任务按幂等语义返回 false。"""
        with self._lock:
            run = self._runs.get(request_id)
        if run is None:
            return False
        run.cancel()
        return True

    def release(self, run: SpeechRun) -> None:
        """仅释放仍指向当前实例的登记，避免并发误删。"""
        with self._lock:
            if self._runs.get(run.request_id) is run:
                self._runs.pop(run.request_id, None)


speech_run_registry = SpeechRunRegistry()


class CosyVoiceProvider:
    """通过 DashScope Python SDK 接收 CosyVoice MP3 音频块。"""

    media_type = "audio/mpeg"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def stream(self, run: SpeechRun, text: str, speech_rate: float) -> None:
        """启动 WebSocket 合成，并把回调音频转交给 FastAPI 响应流。"""
        settings = self.settings
        complete = Event()
        failure: list[BaseException] = []

        class Callback(ResultCallback):
            """把 SDK 回调桥接到线程安全队列。"""

            def on_data(self, data: bytes) -> None:
                if data and not run.cancelled.is_set():
                    run.put(data)

            def on_complete(self) -> None:
                complete.set()

            def on_error(self, message) -> None:
                failure.append(RuntimeError(str(message)))
                complete.set()

            def on_close(self) -> None:
                # 某些网络错误只触发关闭事件，防止工作线程永久等待。
                complete.set()

        try:
            dashscope.api_key = settings.dashscope_api_key
            synthesizer = SpeechSynthesizer(
                model=settings.tts_model,
                voice=settings.tts_voice,
                format=_audio_format(settings.tts_sample_rate),
                speech_rate=speech_rate,
                callback=Callback(),
            )
            run.attach(synthesizer)
            if not run.cancelled.is_set():
                synthesizer.call(text)
                complete.wait(timeout=settings.model_timeout_seconds)
            if failure and not run.cancelled.is_set():
                run.put(failure[0])
            elif not complete.is_set() and not run.cancelled.is_set():
                run.put(TimeoutError("CosyVoice 语音合成超时"))
        except BaseException as exc:
            if not run.cancelled.is_set():
                run.put(exc)
        finally:
            run.finish()


def _audio_format(sample_rate: int) -> AudioFormat:
    """将有限的公开采样率映射到 SDK 枚举，避免传入无效组合。"""
    formats = {
        16000: AudioFormat.MP3_16000HZ_MONO_128KBPS,
        22050: AudioFormat.MP3_22050HZ_MONO_256KBPS,
        24000: AudioFormat.MP3_24000HZ_MONO_256KBPS,
        44100: AudioFormat.MP3_44100HZ_MONO_256KBPS,
        48000: AudioFormat.MP3_48000HZ_MONO_256KBPS,
    }
    try:
        return formats[sample_rate]
    except KeyError as exc:
        raise AppError(
            "TTS_SAMPLE_RATE 不是 CosyVoice 支持的 MP3 采样率",
            status_code=500,
            code="tts_sample_rate_invalid",
        ) from exc


class TextToSpeechService:
    """协调文本清理、缓存、提供方流式输出和任务生命周期。"""

    def __init__(self, settings: Settings, provider: StreamingSpeechProvider | None = None) -> None:
        self.settings = settings
        self.provider = provider or CosyVoiceProvider(settings)

    def validate(self, text: str) -> str:
        """在发送响应头前完成配置与正文校验。"""
        if not self.settings.dashscope_api_key:
            raise AppError(
                "未配置 DASHSCOPE_API_KEY，暂时无法朗读",
                status_code=503,
                code="tts_not_configured",
            )
        if self.settings.tts_format.lower() != "mp3":
            raise AppError(
                "当前网页播放器只支持 TTS_FORMAT=mp3",
                status_code=500,
                code="tts_format_invalid",
            )
        normalized = normalize_speech_text(text)
        if not normalized:
            raise AppError("没有可朗读的正文", status_code=422, code="tts_text_empty")
        if len(normalized) > self.settings.tts_max_text_chars:
            raise AppError(
                f"朗读正文不能超过 {self.settings.tts_max_text_chars} 个字符",
                status_code=413,
                code="tts_text_too_long",
            )
        return normalized

    def stream(self, request_id: str, text: str, speech_rate: float) -> Iterator[bytes]:
        """优先读取磁盘缓存；未命中时边返回边写入原子缓存文件。"""
        cache_file = self._cache_file(text, speech_rate)
        if cache_file.is_file():
            yield from _read_file_chunks(cache_file)
            return

        run = speech_run_registry.create(request_id)
        temporary = cache_file.with_suffix(f".{request_id}.tmp")
        worker = Thread(
            target=self.provider.stream,
            args=(run, text, speech_rate),
            name=f"tts-{request_id[:8]}",
            daemon=True,
        )
        worker.start()
        succeeded = False
        try:
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            with temporary.open("wb") as output:
                while True:
                    item = run.chunks.get()
                    if item is _STREAM_END:
                        succeeded = not run.cancelled.is_set()
                        break
                    if isinstance(item, BaseException):
                        raise item
                    output.write(item)
                    yield item
            if succeeded and temporary.stat().st_size > 0:
                temporary.replace(cache_file)
        finally:
            if not run.completed.is_set():
                run.cancel()
            speech_run_registry.release(run)
            if temporary.exists():
                temporary.unlink(missing_ok=True)

    def _cache_file(self, text: str, speech_rate: float) -> Path:
        """生成包含模型参数的稳定缓存键，修改音色后不会误用旧音频。"""
        identity = "\0".join(
            [
                self.settings.tts_model,
                self.settings.tts_voice,
                self.settings.tts_format,
                str(self.settings.tts_sample_rate),
                str(speech_rate),
                text,
            ]
        )
        digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()
        return self.settings.tts_cache_path / f"{digest}.mp3"


def _read_file_chunks(path: Path, chunk_size: int = 64 * 1024) -> Iterator[bytes]:
    """分块读取缓存，避免长回答的音频一次性占用内存。"""
    with path.open("rb") as source:
        while chunk := source.read(chunk_size):
            yield chunk
