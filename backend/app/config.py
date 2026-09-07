from functools import lru_cache
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic_settings import BaseSettings, SettingsConfigDict

# libpq query params that asyncpg does not accept as connect kwargs. They are
# stripped from the URL; SSL is re-applied via connect_args (see db_connect_args).
_LIBPQ_ONLY_PARAMS = {"sslmode", "channel_binding"}

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
        """DATABASE_URL normalized for SQLAlchemy's asyncpg driver. Managed
        Postgres providers (Railway/Neon/Render) hand out plain `postgresql://`
        (or `postgres://`) URLs, and Neon/Render append libpq-only query params
        (`sslmode`, `channel_binding`) that asyncpg rejects — strip those and
        re-apply SSL through db_connect_args instead."""
        url = self.DATABASE_URL
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

        parts = urlsplit(url)
        kept = [(k, v) for k, v in parse_qsl(parts.query) if k not in _LIBPQ_ONLY_PARAMS]
        return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(kept), parts.fragment))

    @property
    def db_ssl_required(self) -> bool:
        """Whether the database connection must use SSL. Managed providers
        require it; local Postgres does not."""
        url = self.DATABASE_URL.lower()
        params = dict(parse_qsl(urlsplit(url).query))
        mode = params.get("sslmode", "")
        return mode in {"require", "verify-ca", "verify-full"} or ".neon.tech" in url

    @property
    def db_connect_args(self) -> dict:
        """Extra kwargs for create_async_engine — passed through to asyncpg."""
        return {"ssl": True} if self.db_ssl_required else {}

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache()
def get_settings() -> Settings:
    """Single cached Settings instance. Defined here (not in database.py) so
    config has no dependency on the persistence layer."""
    return Settings()
