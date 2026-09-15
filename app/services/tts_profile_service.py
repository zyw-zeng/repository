"""管理角色音色配置，并向公开朗读接口提供当前生效设置。"""

from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.schemas.tts import SpiritCharacterId, TtsVoiceProfileUpdate
from app.storage.models import TtsVoiceProfile
from app.storage.repositories.tts_profiles import TtsVoiceProfileRepository


class TtsVoiceProfileService:
    """提供固定角色音色的读取和管理员更新能力。"""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.profiles = TtsVoiceProfileRepository(session)

    def list_profiles(self) -> list[TtsVoiceProfile]:
        """返回完整配置，并全部存在的三个角色。"""
        items = self.profiles.ensure_defaults()
        self.session.commit()
        return items

    def get_profile(self, character_id: SpiritCharacterId) -> TtsVoiceProfile:
        """读取角色配置；测试库未初始化数据时自动补齐默认值。"""
        profile = self.profiles.get(character_id)
        if profile is None:
            self.profiles.ensure_defaults()
            self.session.commit()
            profile = self.profiles.get(character_id)
        if profile is None:
            raise AppError("角色音色不存在", status_code=404, code="tts_profile_not_found")
        return profile

    def update_profile(
        self,
        character_id: SpiritCharacterId,
        request: TtsVoiceProfileUpdate,
    ) -> TtsVoiceProfile:
        """更新模型、音色和自动朗读策略，并立即提交。"""
        profile = self.get_profile(character_id)
        profile.model = request.model
        profile.voice = request.voice
        profile.enabled = request.enabled
        profile.auto_speak = request.auto_speak
        self.session.commit()
        self.session.refresh(profile)
        return profile
