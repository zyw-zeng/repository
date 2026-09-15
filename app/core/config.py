"""集中读取并校验应用配置，避免业务代码直接访问环境变量。"""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用运行配置；同名环境变量会覆盖这里的默认值。"""

    # 自动读取项目根目录的 .env，并忽略暂时未声明的额外配置。
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Web 服务基础配置。
    app_name: str = "ZYW 的 AI 小助理"
    app_version: str = "0.6.3"
    app_env: str = "development"
    app_debug: bool = False
    app_host: str = "127.0.0.1"
    app_port: int = 8000
    log_level: str = "INFO"

    # 管理端使用短期签名令牌；公开部署前必须通过环境变量设置强密码和随机密钥。
    admin_password: str = Field(default="", repr=False)
    auth_secret_key: str = Field(default="", repr=False)
    admin_token_ttl_minutes: int = 480

    # 模型配置。密钥禁止出现在对象的调试字符串中。
    dashscope_api_key: str = Field(default="", repr=False)
    model_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    # CHAT_MODEL 保留为主回答模型配置名，避免破坏已有 .env。
    chat_model: str = "qwen3.7-plus"
    router_model: str = "qwen3.7-flash"
    # 推荐问题使用独立小模型，不占用主回答模型的调用预算。
    suggestion_model: str = "qwen3.7-flash"
    suggestion_timeout_seconds: float = 5
    suggestion_count: int = 3
    suggestion_history_messages: int = 6
    # JD 使用结构化长输出，不能沿用普通回答较小的输出上限。
    jd_model_max_output_tokens: int = 2600
    jd_evaluation_batch_size: int = 5
    jd_evidence_quote_chars: int = 350
    model_enable_thinking: bool = False
    model_max_output_tokens: int = 1200
    embedding_model: str = "qwen3.7-text-embedding"
    embedding_dimensions: int = 1024
    embedding_batch_size: int = 20
    model_timeout_seconds: float = 60
    model_max_retries: int = 2

    # CosyVoice 语音合成配置。默认关闭自动朗读，由访客主动点击播放后才产生费用。
    tts_model: str = "cosyvoice-v3-flash"
    tts_voice: str = "longanyang"
    tts_format: str = "mp3"
    tts_sample_rate: int = 22050
    tts_max_text_chars: int = 8000
    tts_cache_path: Path = Path("./data/tts-cache")

    # 公开简历配置。接口只读取这个固定文件，不接受访客传入任意服务器路径。
    resume_file_path: Path = Path("./output/pdf/曾有为-AI-Agent应用开发.pdf")
    resume_title: str = "曾有为｜AI Agent 应用开发"
    resume_version: str = "2026.09"
    resume_max_upload_bytes: int = 10 * 1024 * 1024
    # 结构化个人档案只保存本人确认过的事实，用于年限和明确技能判断。
    candidate_profile_path: Path = Path("./data/candidate_profile.json")

    # 本地持久化目录与数据库连接。
    database_url: str = "sqlite:///./data/app.db"
    chroma_path: Path = Path("./data/chroma")
    documents_path: Path = Path("./data/documents")
    chroma_collection: str = "personal_knowledge_base"

    # 文档入库限制。切片大小按字符估算，后续可替换为模型 Token 计数器。
    max_upload_bytes: int = 30 * 1024 * 1024
    max_filename_length: int = 255
    chunk_size: int = 800
    chunk_overlap: int = 120
    ingestion_max_attempts: int = 3

    # RAG 配置控制召回范围、拒答阈值和发送给模型的上下文上限。
    rag_top_k: int = 5
    rag_fetch_k: int = 20
    # 中文短查询在当前 Embedding 下常见有效分数约为 0.35～0.45。
    rag_min_score: float = 0.35
    rag_max_context_chars: int = 12000
    rag_max_history_messages: int = 6

    # Agent 的步骤、检索重试和节点超时都设置硬上限，防止工作流无限运行。
    agent_max_steps: int = 8
    agent_max_retrieval_attempts: int = 2
    agent_timeout_seconds: float = 90
    # Career Agent 使用独立预算，避免求职追问进入普通 Agent 的工具循环。
    career_agent_max_steps: int = 6
    career_agent_timeout_seconds: float = 20

    def ensure_local_directories(self) -> None:
        """创建运行所需目录；已存在时不会覆盖其中的数据。"""
        self.chroma_path.mkdir(parents=True, exist_ok=True)
        self.documents_path.mkdir(parents=True, exist_ok=True)
        self.tts_cache_path.mkdir(parents=True, exist_ok=True)
        self.resume_file_path.parent.mkdir(parents=True, exist_ok=True)
        self.candidate_profile_path.parent.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    """返回进程级配置单例，避免每次请求重复读取环境文件。"""
    return Settings()
