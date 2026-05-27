"""
核心配置 - PMRS工业控制协议漏洞挖掘系统
"""
from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    PROJECT_NAME: str = "PMRS - 工业控制协议漏洞挖掘系统"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api/v1"
    DEBUG: bool = True
    ENVIRONMENT: str = "development"

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/pmrs"
    DB_POOL_SIZE: int = 20
    DB_POOL_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    DB_ECHO: bool = False

    REDIS_URL: str = "redis://localhost:6379/0"

    CORS_ORIGINS: list = ["*"]

    RATE_LIMIT_MAX_REQUESTS: int = 100
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    LOG_LEVEL: str = "INFO"

    # 大模型配置
    LLM_PROVIDER: str = "dashscope"  # dashscope, openai, local
    DASHSCOPE_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    LLM_MODEL: str = "qwen-plus"
    LLM_TEMPERATURE: float = 0.1
    LLM_MAX_TOKENS: int = 4096

    # AFL++ 配置
    AFL_PATH: str = "/usr/local/bin"
    AFL_INPUT_DIR: str = "/tmp/afl_input"
    AFL_OUTPUT_DIR: str = "/tmp/afl_output"
    AFL_TIMEOUT: int = 3600

    # 工控协议配置
    SUPPORTED_PROTOCOLS: list = ["modbus_tcp", "iec61850", "dnp3"]
    DEFAULT_TARGET_IP: str = "127.0.0.1"
    DEFAULT_TARGET_PORT: int = 502

    # Wireshark SDK
    WIRESHARK_PATH: Optional[str] = None

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
