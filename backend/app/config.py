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
    # OpenAI-compatible chat/completions endpoint. Defaults to Groq. To use
    # NVIDIA instead, set this to https://integrate.api.nvidia.com/v1/chat/completions
    # and set GROQ_API_KEY / GROQ_MODEL to your NVIDIA key and model id.
    LLM_API_URL: str = "https://api.groq.com/openai/v1/chat/completions"
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
    # Single-operator login. Credentials live here (server-side / env vars), never
    # in the frontend bundle. Leave AUTH_PASSWORD empty to disable the login gate.
    AUTH_EMAIL: str = ""
    AUTH_PASSWORD: str = ""
    # Secret used to sign session tokens. Set a long random value in production.
    AUTH_SECRET: str = "kintix-dev-secret-change-me"
    # Session lifetime in seconds (default 12 hours).
    AUTH_TOKEN_TTL_SECONDS: int = 43200

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
        """Whether the database connection must use SSL. An explicit `sslmode`
        wins; otherwise any non-local host is assumed to be a managed provider
        (Neon, Supabase, Render, …) that requires SSL, while localhost does not."""
        parts = urlsplit(self.DATABASE_URL)
        mode = dict(parse_qsl(parts.query)).get("sslmode", "").lower()
        if mode:
            return mode != "disable"
        host = (parts.hostname or "").lower()
        return host not in {"localhost", "127.0.0.1", "::1", ""}

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
