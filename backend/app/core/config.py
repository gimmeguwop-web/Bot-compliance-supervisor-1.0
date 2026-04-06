"""
Core configuration module for ESKD Validator.

Loads settings from environment variables and provides type-safe access.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    APP_ENV: str = "development"
    SECRET_KEY: str = "supersecretkey_change_in_prod"
    LOG_LEVEL: str = "INFO"

    # Database
    POSTGRES_USER: str = "eskd_admin"
    POSTGRES_PASSWORD: str = "secure_password"
    POSTGRES_DB: str = "eskd_db"
    DATABASE_URL: Optional[str] = None

    # Redis
    REDIS_URL: str = "redis://redis:6379/0"

    # Storage
    STORAGE_PATH: str = "/app/uploads"
    S3_ENDPOINT_URL: Optional[str] = None
    S3_BUCKET: Optional[str] = None
    S3_ACCESS_KEY: Optional[str] = None
    S3_SECRET_KEY: Optional[str] = None

    # LLM
    LLM_PROVIDER: str = "ollama"  # ollama or openai
    LLM_BASE_URL: str = "http://host.docker.internal:11434/v1"
    LLM_MODEL_NAME: str = "mistral:7b-instruct-v0.3-q4_K_M"
    LLM_API_KEY: Optional[str] = None

    # OCR/CV
    OCR_LANG: str = "ru,en"
    YOLO_MODEL_PATH: str = "models/yolov8n-signatures.pt"
    CONFIDENCE_THRESHOLD: float = 0.5

    # Celery
    WORKER_CONCURRENCY: int = 2
    TASK_TIME_LIMIT: int = 300

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    @property
    def db_url(self) -> str:
        """Get database URL, constructing it if not provided directly."""
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@db:5432/{self.POSTGRES_DB}"
        )

    @property
    def is_llm_enabled(self) -> bool:
        """Check if LLM provider is configured."""
        return bool(self.LLM_BASE_URL)

    @property
    def use_local_storage(self) -> bool:
        """Check if using local file storage vs S3."""
        return self.S3_ENDPOINT_URL is None


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
