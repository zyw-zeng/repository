"""封装精灵角色音色配置的数据库操作。"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.storage.models import TtsVoiceProfile

DEFAULT_VOICE_PROFILES = (
    ("nova", "星云"),
    ("byte", "比特"),
    ("momo", "沫沫"),
)


class TtsVoiceProfileRepository:
    """读取和更新固定的三个角色音色配置。"""

    def __init__(self, session: Session) -> None:
        self.session = session

    def ensure_defaults(self) -> list[TtsVoiceProfile]:
        """补齐缺失的默认角色，兼容尚未执行数据种子的测试数据库。"""
        profiles = {item.character_id: item for item in self.list_all()}
        for character_id, display_name in DEFAULT_VOICE_PROFILES:
            if character_id not in profiles:
                profile = TtsVoiceProfile(
                    character_id=character_id,
                    display_name=display_name,
                )
                self.session.add(profile)
                profiles[character_id] = profile
        self.session.flush()
        return [profiles[character_id] for character_id, _ in DEFAULT_VOICE_PROFILES]

    def list_all(self) -> list[TtsVoiceProfile]:
        """按角色 ID 返回全部配置。"""
        return list(
            self.session.scalars(
                select(TtsVoiceProfile).order_by(TtsVoiceProfile.character_id)
            )
        )

    def get(self, character_id: str) -> TtsVoiceProfile | None:
        """读取单个角色配置。"""
        return self.session.get(TtsVoiceProfile, character_id)
