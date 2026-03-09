"""
Intelli-Credit: Automated Corporate Credit Appraisal Engine
Configuration Module
"""

import os
from pathlib import Path
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # API Keys
    GROQ_API_KEY: str = ""
    SERP_API_KEY: str = ""
    GNEWS_API_KEY: str = ""
    PINECONE_API_KEY: str = ""
    PINECONE_INDEX_NAME: str = "intelli-credit"
    PINECONE_ENVIRONMENT: str = "us-east-1"  # Or your specific region

    # Supabase
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""
    SUPABASE_JWT_SECRET: str = ""
    SUPABASE_STORAGE_BUCKET: str = "documents"

    # Redis (shared state across workers)
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_STATE_TTL_HOURS: int = 72  # Analysis state TTL
    REDIS_RESULT_TTL_HOURS: int = 168  # Full results TTL (7 days)

    # LLM Configuration
    LLM_MODEL: str = "llama-3.3-70b-versatile"
    LLM_TEMPERATURE: float = 0.1
    LLM_MAX_TOKENS: int = 4096

    # Vector Store
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 4

    # CORS (comma-separated allowed origins, "*" for dev)
    CORS_ORIGINS: str = "*"

    # File paths
    UPLOAD_DIR: str = "./uploads"
    REPORTS_DIR: str = "./reports"

    # Research cache
    RESEARCH_CACHE_DIR: str = "./research_cache"
    RESEARCH_CACHE_TTL_HOURS: int = 24

    # Result cache (agent outputs)
    CACHE_DIR: str = "./cache"
    CACHE_TTL_HOURS: int = 24

    # Retry & resilience
    RETRY_MAX_ATTEMPTS: int = 3
    RETRY_BACKOFF_BASE: float = 2.0

    # Agent execution
    AGENT_TIMEOUT_SECONDS: int = 45

    # Quality thresholds
    MIN_QUALITY_SCORE: float = 40.0
    OCR_CONFIDENCE_THRESHOLD: float = 0.65

    # PII redaction
    PII_REDACTION_ENABLED: bool = True

    # App Info
    APP_NAME: str = "Intelli-Credit"
    APP_VERSION: str = "2.0.0"
    APP_DESCRIPTION: str = "Automated Corporate Credit Appraisal Engine"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()


def ensure_directories():
    """Ensure required directories exist."""
    settings = get_settings()
    Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
    Path(settings.REPORTS_DIR).mkdir(parents=True, exist_ok=True)
    Path(settings.CACHE_DIR).mkdir(parents=True, exist_ok=True)
