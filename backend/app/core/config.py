"""
Central settings object. Everything configurable lives in .env — nothing
here should be hardcoded, since Phase 7 (public deployment) needs to swap
these per-environment without touching code.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    cors_origins: str = "http://localhost:5173"

    # Rate limiting
    rate_limit_search: str = "30/hour"
    rate_limit_default: str = "100/hour"

    # Search sources
    semantic_scholar_api_key: str = ""
    pubmed_email: str = ""
    pubmed_api_key: str = ""
    search_max_results_per_source: int = 10
    search_cache_ttl_seconds: int = 3600  # 1 hour
    
    # Phase 2: ingestion
    papers_dir: str = "data/papers"
    cache_dir: str = "data/cache"
    chroma_persist_dir: str = "data/cache/chroma"
    embedding_model: str = "all-MiniLM-L6-v2"
    chunk_size_chars: int = 1500
    chunk_overlap_chars: int = 200
    pdf_download_timeout_seconds: int = 30

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
