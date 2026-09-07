from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import Settings, get_settings


class Base(DeclarativeBase):
    pass


# The engine is created lazily rather than at import time. Importing the app
# should never require a live database driver — that would make the whole
# package untestable without Postgres installed.
_engine: Optional[AsyncEngine] = None
_sessionmaker: Optional[async_sessionmaker] = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(
            settings.async_database_url,
            pool_pre_ping=True,
            echo=settings.DEBUG,
            connect_args=settings.db_connect_args,
        )
    return _engine


def get_sessionmaker() -> async_sessionmaker:
    global _sessionmaker
    if _sessionmaker is None:
        _sessionmaker = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _sessionmaker


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with get_sessionmaker()() as session:
        yield session
