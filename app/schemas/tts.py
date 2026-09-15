"""定义语音合成接口的数据结构。"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

SpiritCharacterId = Literal["nova", "byte", "momo"]


class SpeechSynthesisRequest(BaseModel):
    """请求将一段已经完成的回答转换为语音。"""

    text: str = Field(min_length=1, max_length=12000, description="需要朗读的回答正文。")
    speech_rate: float = Field(
        default=1.0,
        ge=0.5,
        le=2.0,
        description="播放语速；1.0 表示正常速度。",
    )
    character_id: SpiritCharacterId = Field(
        default="nova",
        description="当前负责朗读的精灵角色。",
    )

    @field_validator("text")
    @classmethod
    def text_must_not_be_blank(cls, value: str) -> str:
        """拒绝只包含空白字符的合成请求。"""
        normalized = value.strip()
        if not normalized:
            raise ValueError("朗读文本不能为空")
        return normalized


class SpeechCancellationResponse(BaseModel):
    """服务端已接收指定语音任务的取消请求。"""

    request_id: str
    status: str = "cancellation_requested"


class TtsVoiceProfileResponse(BaseModel):
    """访客端和管理端可读取的角色音色配置。"""

    model_config = ConfigDict(from_attributes=True)

    character_id: SpiritCharacterId
    display_name: str
    model: str
    voice: str
    enabled: bool
    auto_speak: bool
    updated_at: datetime


class TtsVoiceProfileListResponse(BaseModel):
    """管理端读取的全部角色音色。"""

    items: list[TtsVoiceProfileResponse]


class TtsVoiceProfileUpdate(BaseModel):
    """管理员允许修改的 CosyVoice 参数。"""

    model: str = Field(min_length=2, max_length=100)
    voice: str = Field(min_length=2, max_length=120)
    enabled: bool = True
    auto_speak: bool = True

    @field_validator("model", "voice")
    @classmethod
    def identifiers_must_not_be_blank(cls, value: str) -> str:
        """清理模型与音色 ID，避免保存不可见空白。"""
        return value.strip()
