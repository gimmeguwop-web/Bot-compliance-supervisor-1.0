"""
Tests for configuration loading.
"""
import pytest
from app.core.config import get_settings, Settings


def test_settings_load_from_env():
    """Test that settings load correctly from environment."""
    settings = get_settings()
    
    assert settings.APP_ENV in ["development", "production", "testing"]
    assert settings.REDIS_URL.startswith("redis://")
    assert settings.LLM_PROVIDER in ["ollama", "openai"]


def test_settings_database_url_construction():
    """Test database URL construction when not provided directly."""
    settings = Settings(
        DATABASE_URL=None,
        POSTGRES_USER="test_user",
        POSTGRES_PASSWORD="test_pass",
        POSTGRES_DB="test_db"
    )
    
    expected = "postgresql://test_user:test_pass@db:5432/test_db"
    assert settings.db_url == expected


def test_settings_direct_database_url():
    """Test that direct DATABASE_URL takes precedence."""
    custom_url = "postgresql://custom:pass@host:5432/custom_db"
    settings = Settings(
        DATABASE_URL=custom_url,
        POSTGRES_USER="ignored",
        POSTGRES_PASSWORD="ignored",
        POSTGRES_DB="ignored"
    )
    
    assert settings.db_url == custom_url


def test_llm_enabled_check():
    """Test LLM enabled property."""
    settings_with_url = Settings(LLM_BASE_URL="http://localhost:11434/v1")
    settings_without_url = Settings(LLM_BASE_URL="")
    
    assert settings_with_url.is_llm_enabled is True
    assert settings_without_url.is_llm_enabled is False
