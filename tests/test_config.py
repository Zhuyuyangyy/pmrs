"""
Tests for application configuration.
"""
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


class TestSettings:
    """Tests for the Settings class."""

    def test_settings_default_project_name(self):
        """Settings has correct default project name."""
        from core.config import Settings
        s = Settings()
        assert "PMRS" in s.PROJECT_NAME

    def test_settings_default_version(self):
        """Settings has a version string."""
        from core.config import Settings
        s = Settings()
        assert s.VERSION is not None
        assert len(s.VERSION) > 0

    def test_settings_default_api_prefix(self):
        """Settings has correct API prefix."""
        from core.config import Settings
        s = Settings()
        assert s.API_PREFIX == "/api/v1"

    def test_settings_default_database_url(self):
        """Settings has a default database URL."""
        from core.config import Settings
        s = Settings()
        assert s.DATABASE_URL is not None
        assert "postgresql" in s.DATABASE_URL or "sqlite" in s.DATABASE_URL

    def test_settings_default_redis_url(self):
        """Settings has a default Redis URL."""
        from core.config import Settings
        s = Settings()
        assert s.REDIS_URL is not None
        assert "redis" in s.REDIS_URL

    def test_settings_supported_protocols(self):
        """Settings lists supported protocols."""
        from core.config import Settings
        s = Settings()
        assert "modbus_tcp" in s.SUPPORTED_PROTOCOLS
        assert "iec61850" in s.SUPPORTED_PROTOCOLS
        assert "dnp3" in s.SUPPORTED_PROTOCOLS

    def test_settings_llm_provider(self):
        """Settings has LLM provider configured."""
        from core.config import Settings
        s = Settings()
        assert s.LLM_PROVIDER in ("dashscope", "openai", "local")

    def test_settings_rate_limit_defaults(self):
        """Settings has sensible rate limit defaults."""
        from core.config import Settings
        s = Settings()
        assert s.RATE_LIMIT_MAX_REQUESTS > 0
        assert s.RATE_LIMIT_WINDOW_SECONDS > 0

    def test_settings_is_production_property(self):
        """is_production property works correctly."""
        from core.config import Settings
        s = Settings(ENVIRONMENT="production")
        assert s.is_production is True
        assert s.is_development is False

    def test_settings_is_development_property(self):
        """is_development property works correctly."""
        from core.config import Settings
        s = Settings(ENVIRONMENT="development")
        assert s.is_development is True
        assert s.is_production is False

    def test_settings_db_pool_defaults(self):
        """Settings has sensible DB pool defaults."""
        from core.config import Settings
        s = Settings()
        assert s.DB_POOL_SIZE > 0
        assert s.DB_POOL_OVERFLOW >= 0
        assert s.DB_POOL_TIMEOUT > 0

    def test_settings_llm_defaults(self):
        """Settings has sensible LLM defaults."""
        from core.config import Settings
        s = Settings()
        assert s.LLM_MODEL is not None
        assert 0.0 <= s.LLM_TEMPERATURE <= 2.0
        assert s.LLM_MAX_TOKENS > 0

    def test_settings_afl_defaults(self):
        """Settings has AFL configuration."""
        from core.config import Settings
        s = Settings()
        assert s.AFL_PATH is not None
        assert s.AFL_INPUT_DIR is not None
        assert s.AFL_OUTPUT_DIR is not None
        assert s.AFL_TIMEOUT > 0
