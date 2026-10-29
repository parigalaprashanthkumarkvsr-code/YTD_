from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, overridable with environment variables or a .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "YTD"
    download_dir: Path = Path("/tmp/ytd-downloads")
    file_ttl_minutes: int = 30
    max_concurrent_jobs: int = 3
    max_duration_seconds: int = 7200
    max_filesize_mb: int = 4096
    max_playlist_items: int = 50
    allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    rate_limit: str = "10/minute"
    rate_limit_enabled: bool = True
    cleanup_interval_seconds: int = 60

    @property
    def allowed_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
