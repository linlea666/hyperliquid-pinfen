from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralized application configuration."""

    app_name: str = "Wallet Analytics"
    environment: str = "dev"
    debug: bool = True
    api_prefix: str = "/api"

    # Data paths
    data_dir: Path = Path("./data")
    sqlite_path: Path = Path("./data/wallet_analytics.db")
    cache_dir: Path = Path("./data/cache")

    # Security / Auth
    secret_key: str = "change-me"
    allowed_origins: List[str] = ["*"]

    # Hyperliquid
    hyperliquid_base_url: str = "https://api.hyperliquid.xyz/info"
    hyperliquid_timeout_sec: float = 10.0

    # Logging
    log_level: str = "INFO"

    # Queue
    redis_url: str = "redis://localhost:6379/0"
    admin_api_token: str = "change-admin-token"

    # Notifications
    smtp_host: str = "localhost"
    smtp_port: int = 25
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from: str = "no-reply@example.com"
    smtp_use_tls: bool = True
    webhook_url: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    def ensure_dirs(self) -> None:
        """Create required local directories."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_dirs()
    return settings
