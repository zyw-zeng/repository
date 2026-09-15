"""提供 CosyVoice 回答后流式朗读和服务端取消接口。"""

from typing import Annotated

from fastapi import APIRouter, Depends, Header, Path, status
from fastapi.responses import StreamingResponse

from app.api.dependencies import AdminAuthorization, DatabaseSession
from app.core.config import Settings, get_settings
from app.core.exceptions import AppError
from app.schemas.tts import (
    SpeechCancellationResponse,
    SpeechSynthesisRequest,
    SpiritCharacterId,
    TtsVoiceProfileListResponse,
    TtsVoiceProfileResponse,
    TtsVoiceProfileUpdate,
)
from app.services.tts_profile_service import TtsVoiceProfileService
from app.services.tts_service import TextToSpeechService, speech_run_registry

router = APIRouter(prefix="/api/v1/tts", tags=["语音"])


@router.post(
    "/stream",
    summary="流式合成回答语音",
    description="使用阿里云 CosyVoice 将完整回答转换为 MP3，并按音频块持续返回。",
    response_class=StreamingResponse,
    responses={
        200: {"content": {"audio/mpeg": {}}, "description": "MP3 音频流。"},
        503: {"description": "尚未配置 DashScope。"},
    },
)
def stream_speech(
    request: SpeechSynthesisRequest,
    session: DatabaseSession,
    settings: Annotated[Settings, Depends(get_settings)],
    request_id: Annotated[
        str,
        Header(alias="X-Request-ID", min_length=8, max_length=128),
    ],
) -> StreamingResponse:
    """按当前角色音色校验文本并返回可取消、可缓存的音频流。"""
    profile = TtsVoiceProfileService(session).get_profile(request.character_id)
    if not profile.enabled:
        raise AppError("当前角色没有启用语音", status_code=409, code="tts_voice_disabled")
    # 每次请求复制一份配置，管理端更新后下一段语音立即使用新音色。
    speech_settings = settings.model_copy(
        update={"tts_model": profile.model, "tts_voice": profile.voice}
    )
    service = TextToSpeechService(speech_settings)
    normalized = service.validate(request.text)
    return StreamingResponse(
        service.stream(request_id, normalized, request.speech_rate),
        media_type=service.provider.media_type,
        headers={
            "Cache-Control": "private, max-age=86400",
            "Content-Disposition": "inline",
            "X-TTS-Request-ID": request_id,
            "X-Accel-Buffering": "no",
        },
    )


@router.get(
    "/profiles/{character_id}",
    response_model=TtsVoiceProfileResponse,
    summary="读取角色当前音色",
)
def get_voice_profile(
    character_id: Annotated[SpiritCharacterId, Path(description="精灵角色 ID。")],
    session: DatabaseSession,
) -> TtsVoiceProfileResponse:
    """供访客端读取是否自动朗读以及当前角色音色。"""
    return TtsVoiceProfileResponse.model_validate(
        TtsVoiceProfileService(session).get_profile(character_id)
    )


@router.get(
    "/profiles",
    response_model=TtsVoiceProfileListResponse,
    summary="管理端读取全部角色音色",
)
def list_voice_profiles(
    _: AdminAuthorization,
    session: DatabaseSession,
) -> TtsVoiceProfileListResponse:
    """管理员读取星云、比特和沫沫的完整配置。"""
    return TtsVoiceProfileListResponse(
        items=[
            TtsVoiceProfileResponse.model_validate(item)
            for item in TtsVoiceProfileService(session).list_profiles()
        ]
    )


@router.put(
    "/profiles/{character_id}",
    response_model=TtsVoiceProfileResponse,
    summary="更新角色 CosyVoice 音色",
)
def update_voice_profile(
    character_id: Annotated[SpiritCharacterId, Path(description="精灵角色 ID。")],
    request: TtsVoiceProfileUpdate,
    _: AdminAuthorization,
    session: DatabaseSession,
) -> TtsVoiceProfileResponse:
    """管理员更新配置；后续合成请求立即读取新值。"""
    profile = TtsVoiceProfileService(session).update_profile(character_id, request)
    return TtsVoiceProfileResponse.model_validate(profile)


@router.post(
    "/runs/{request_id}/cancel",
    response_model=SpeechCancellationResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="停止正在进行的语音合成",
)
def cancel_speech(
    request_id: Annotated[str, Path(description="语音请求使用的 X-Request-ID。")],
) -> SpeechCancellationResponse:
    """按幂等方式取消活动任务；任务已结束时同样安全返回。"""
    speech_run_registry.cancel(request_id)
    return SpeechCancellationResponse(request_id=request_id)
