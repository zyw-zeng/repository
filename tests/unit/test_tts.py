"""验证 TTS 文本清理、流式缓存和取消基础设施。"""

from pathlib import Path

import pytest

from app.core.exceptions import AppError
from app.services.tts_service import (
    SpeechRun,
    TextToSpeechService,
    normalize_speech_text,
    speech_run_registry,
)


class FakeSpeechProvider:
    """测试使用的确定性流式提供方，不请求真实云服务。"""

    media_type = "audio/mpeg"

    def __init__(self) -> None:
        self.calls = 0

    def stream(self, run: SpeechRun, text: str, speech_rate: float) -> None:
        self.calls += 1
        run.put(f"{text}:{speech_rate}".encode())
        run.finish()


def test_normalize_speech_text_removes_markdown_and_citations() -> None:
    """朗读内容不应包含链接地址、标题符号和引用编号。"""
    text = "## **ZYW** 使用 [可靠 RAG](https://example.com)。[1]"

    assert normalize_speech_text(text) == "ZYW 使用 可靠 RAG。"


def test_tts_requires_api_key(test_settings) -> None:
    """缺少密钥时必须在流式响应开始前返回明确业务错误。"""
    service = TextToSpeechService(test_settings, FakeSpeechProvider())

    with pytest.raises(AppError) as captured:
        service.validate("你好")

    assert captured.value.code == "tts_not_configured"


def test_tts_stream_writes_and_reuses_cache(test_settings, tmp_path: Path) -> None:
    """第一次请求写入缓存，第二次相同请求不再调用云端提供方。"""
    test_settings.dashscope_api_key = "test-key"
    test_settings.tts_cache_path = tmp_path / "tts-cache"
    provider = FakeSpeechProvider()
    service = TextToSpeechService(test_settings, provider)
    text = service.validate("你好，ZYW。")

    first = b"".join(service.stream("tts-run-1", text, 1.0))
    second = b"".join(service.stream("tts-run-2", text, 1.0))

    assert first == second == "你好，ZYW。:1.0".encode()
    assert provider.calls == 1
    assert len(list(test_settings.tts_cache_path.glob("*.mp3"))) == 1


def test_registry_cancels_active_run() -> None:
    """取消登记中的任务后，生产者和消费者都能观察到停止信号。"""
    request_id = "tts-cancel-test"
    run = speech_run_registry.create(request_id)
    try:
        assert speech_run_registry.cancel(request_id) is True
        assert run.cancelled.is_set()
        assert run.completed.is_set()
    finally:
        speech_run_registry.release(run)
