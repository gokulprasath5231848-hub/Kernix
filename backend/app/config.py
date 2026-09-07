from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://kintix:kintix_secret@localhost:5432/kintix_db"
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "openai/gpt-oss-120b"
    DEBUG: bool = False
    # Apply Alembic migrations on boot. Disable for test databases created
    # directly from ORM metadata.
    RUN_MIGRATIONS_ON_STARTUP: bool = True
    # Seed the 48-process demo catalog if the database is empty.
    SEED_DEMO_DATA: bool = True
    API_VERSION: str = "2.4"
    # Comma-separated list of allowed browser origins for CORS. Defaults to the
    # local dev servers; set to the deployed frontend URL(s) in production.
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def async_database_url(self) -> str:
        """DATABASE_URL normalized to the asyncpg driver. Managed Postgres
        providers (Railway/Neon/Render) hand out plain `postgresql://` (or
        `postgres://`) URLs; SQLAlchemy's async engine needs `+asyncpg`."""
        url = self.DATABASE_URL
        if url.startswith("postgresql+"):
            return url
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://", 1)
        if url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql+asyncpg://", 1)
        return url

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache()
def get_settings() -> Settings:
    """Single cached Settings instance. Defined here (not in database.py) so
    config has no dependency on the persistence layer."""
    return Settings()
