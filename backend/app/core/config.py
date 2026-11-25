from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_NAME: str = "EnterpriseIQ API"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

    SECRET_KEY: str = "enterpriseiq-dev-secret-change-in-production-32chars"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # PostgreSQL for Docker/Prod; SQLite async fallback for zero-friction local dev
    DATABASE_URL: str = "sqlite+aiosqlite:///./enterpriseiq_dev.db"
    UPLOAD_DIR: str = "./uploads"

    # LLM Engine (Gemini OpenAI-compatible API; falls back to clearly labeled demo/extractive mode if unset)
    LLM_PROVIDER: str = "gemini"  # gemini | openai | demo
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    LLM_MODEL: str = "gemini-2.0-flash"

    # Vector Store & Embeddings
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    CHROMA_PERSIST_DIR: str = "./chroma_db"
    CHROMA_COLLECTION: str = "enterpriseiq_docs"

    # CORS
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
