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

    # Public address of the app, used to build links in emails, e.g. https://rent.example.com
    # If unset, the address the request came in on is used.
    public_url: str | None = None
    # Outgoing email (for "forgot password"). Leave smtp_host unset to disable.
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from: str | None = None
    # "starttls" (port 587), "ssl" (port 465) or "none"
    smtp_security: str = "starttls"
    # How long an emailed reset link stays valid.
    reset_link_minutes: int = 60

    @property
    def email_enabled(self) -> bool:
        return bool(self.smtp_host and (self.smtp_from or self.smtp_username))

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
