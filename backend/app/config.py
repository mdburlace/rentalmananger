"""Application settings, read from environment variables (prefix RM_)."""
from __future__ import annotations

import secrets
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="RM_", env_file=".env", extra="ignore")

    # Where the SQLite database, uploaded receipts and generated secrets live.
    data_dir: Path = Path("./data")
    # Override to use Postgres, e.g. postgresql+psycopg://user:pass@db/rental
    database_url: str | None = None
    # JWT signing key. If unset, one is generated and persisted in data_dir.
    secret_key: str | None = None
    session_hours: int = 24 * 14
    # Set true when served over HTTPS (behind a reverse proxy) so cookies are Secure.
    cookie_secure: bool = False
    # Max upload size for receipts / imports, in MB.
    max_upload_mb: int = 25
    # Directory containing the built frontend (served by FastAPI in production).
    static_dir: Path | None = None

    @property
    def db_url(self) -> str:
        if self.database_url:
            return self.database_url
        return f"sqlite:///{(self.data_dir / 'rental.db').resolve()}"

    @property
    def uploads_dir(self) -> Path:
        return self.data_dir / "uploads"

    def resolved_secret(self) -> str:
        if self.secret_key:
            return self.secret_key
        key_file = self.data_dir / ".secret_key"
        if key_file.exists():
            return key_file.read_text().strip()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        key = secrets.token_urlsafe(48)
        key_file.write_text(key)
        key_file.chmod(0o600)
        return key


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    s.data_dir.mkdir(parents=True, exist_ok=True)
    s.uploads_dir.mkdir(parents=True, exist_ok=True)
    return s
