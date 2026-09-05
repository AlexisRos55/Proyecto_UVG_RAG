from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class AnthropicSettings(BaseSettings):
    """ANTHROPIC_* environment variables (ADR-0006). Model is never hardcoded elsewhere."""

    model_config = SettingsConfigDict(env_prefix="ANTHROPIC_", extra="ignore")

    api_key: str
    model: str = "claude-haiku-4-5-20251001"
    max_tokens: int = 1024


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    database_url: str


class ChromaSettings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    chroma_persist_dir: str = "./data/chroma"


class AuthSettings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    session_secret: str
    allowed_email_domain: str = "uvg.edu.gt"
    session_ttl_minutes: int = 60 * 24
    # Bootstrapping mechanism for EPIC-7 (out of primary thesis evaluation scope, ADR-0008):
    # emails in this allowlist are registered as UserRole.ADMIN instead of UserRole.STUDENT.
    admin_emails: str = ""
    # Sprint 1 demo (ADR-0004 still governs the real auth architecture): a single admin
    # account is seeded at startup if it does not exist yet, so `docker compose up` alone
    # is enough for the demo login. Not a replacement for registration, which stays intact.
    default_admin_email: str = "admin@uvg.edu.gt"
    default_admin_password: str = "admin123"

    @property
    def admin_emails_list(self) -> list[str]:
        emails = [email.strip().lower() for email in self.admin_emails.split(",") if email.strip()]
        if self.default_admin_email.lower() not in emails:
            emails.append(self.default_admin_email.lower())
        return emails


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    app_env: str = "development"
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:5173"
    documents_storage_dir: str = "./data/documents"
    # Sprint 1 demo: bundled/seed corpus loaded automatically at startup (distinct from
    # documents_storage_dir, which holds files uploaded later through the admin panel).
    seed_documents_dir: str = "./documents"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_anthropic_settings() -> AnthropicSettings:
    return AnthropicSettings()  # type: ignore[call-arg]


@lru_cache
def get_database_settings() -> DatabaseSettings:
    return DatabaseSettings()  # type: ignore[call-arg]


@lru_cache
def get_chroma_settings() -> ChromaSettings:
    return ChromaSettings()


@lru_cache
def get_auth_settings() -> AuthSettings:
    return AuthSettings()  # type: ignore[call-arg]


@lru_cache
def get_app_settings() -> AppSettings:
    return AppSettings()
