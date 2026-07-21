from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AEGIS_", env_file=".env", extra="ignore")

    app_name: str = "AegisAI"
    app_version: str = "12.0.0"
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 8000

    # Paths
    upload_dir: Path = Path(__file__).resolve().parent.parent / "uploads"
    storage_root: Path = Path(__file__).resolve().parent.parent / "storage"

    # Uploads
    max_upload_bytes: int = 15 * 1024 * 1024
    allowed_content_types: set[str] = {
        "image/png",
        "image/jpeg",
        "image/jpg",
    }

    # Logging
    log_level: str = "INFO"
    log_to_file: bool = True
    log_file_name: str = "aegisai.log"

    # CORS (comma-separated in env as AEGIS_CORS_ORIGINS)
    cors_origins: str = "*"

    # Encryption — empty = auto-generate key file under storage_root
    encryption_key: str = ""
    encrypt_trade_records: bool = True
    encrypt_memory_at_rest: bool = True
    encrypt_charts: bool = True

    # Analysis defaults
    min_confidence_threshold: float = 70.0
    model_version: str = "core-v1"

    @property
    def cors_origin_list(self) -> list[str]:
        raw = self.cors_origins.strip()
        if raw == "*":
            return ["*"]
        return [o.strip() for o in raw.split(",") if o.strip()]

    @property
    def trades_dir(self) -> Path:
        return self.storage_root / "trades"

    @property
    def logs_dir(self) -> Path:
        return self.storage_root / "logs"

    @property
    def log_file(self) -> Path:
        return self.logs_dir / self.log_file_name


settings = Settings()
settings.upload_dir.mkdir(parents=True, exist_ok=True)
settings.storage_root.mkdir(parents=True, exist_ok=True)
settings.trades_dir.mkdir(parents=True, exist_ok=True)
settings.logs_dir.mkdir(parents=True, exist_ok=True)
