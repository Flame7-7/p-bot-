from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from models.models import Base
from utils.config import get_config
from utils.logging import get_logger

logger = get_logger(__name__)

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        config = get_config()
        _engine = create_async_engine(
            f"sqlite+aiosqlite:///{config.db_path}",
            echo=False,
            connect_args={"check_same_thread": False},
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )
    return _session_factory


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with get_session_factory()() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# Additive, idempotent column migrations for databases created before a column
# existed (create_all never alters existing tables). (table, column, DDL type/default)
_COLUMN_MIGRATIONS: tuple[tuple[str, str, str], ...] = (
    ("nofap_streaks", "partner_id", "INTEGER"),
    ("persona_profiles", "auto_afk", "BOOLEAN DEFAULT 1"),
    ("gifs", "name", "VARCHAR(100)"),
)


def _apply_column_migrations(sync_conn) -> None:
    for table, column, ddl in _COLUMN_MIGRATIONS:
        cols = [row[1] for row in sync_conn.exec_driver_sql(f"PRAGMA table_info({table})").fetchall()]
        if cols and column not in cols:
            sync_conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")
            logger.info("migrated %s: added %s column", table, column)


async def init_db() -> None:
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_apply_column_migrations)
    logger.info("database initialised: %s", get_config().db_path)


async def close_db() -> None:
    global _engine
    if _engine:
        await _engine.dispose()
        _engine = None
