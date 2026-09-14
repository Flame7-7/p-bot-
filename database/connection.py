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


async def _migrate_nofap_partner_column(conn) -> None:
    """Lightweight self-healing migration: `create_all` only creates missing
    tables, it never alters existing ones. Bots deployed before the
    `partner_id` column existed need it added in place, or every nofap
    read/write will fail with 'no such column'."""

    def _add_column_if_missing(sync_conn) -> None:
        from sqlalchemy import text

        cols = [row[1] for row in sync_conn.exec_driver_sql("PRAGMA table_info(nofap_streaks)").fetchall()]
        if cols and "partner_id" not in cols:
            sync_conn.exec_driver_sql("ALTER TABLE nofap_streaks ADD COLUMN partner_id INTEGER")
            logger.info("migrated nofap_streaks: added partner_id column")

    await conn.run_sync(_add_column_if_missing)


async def init_db() -> None:
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await _migrate_nofap_partner_column(conn)
    logger.info("database initialised: %s", get_config().db_path)


async def close_db() -> None:
    global _engine
    if _engine:
        await _engine.dispose()
        _engine = None
