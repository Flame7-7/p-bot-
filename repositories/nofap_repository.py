from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select

from database.connection import get_session
from models.models import NoFapStreak
from utils.logging import get_logger

logger = get_logger(__name__)


def _aware(dt: datetime) -> datetime:
    """SQLite loses tzinfo on round-trip, so every read-back datetime needs
    to be re-tagged as UTC before it's safe to subtract from `now()`."""
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def current_streak_days(streak: NoFapStreak | None) -> int:
    """Days since the current streak started, or 0 if there is no active
    streak (never started, or it's brand new)."""
    if streak is None or streak.started_at is None:
        return 0
    delta = datetime.now(timezone.utc) - _aware(streak.started_at)
    return max(delta.days, 0)


class NoFapRepository:
    async def get(self, user_id: int) -> NoFapStreak | None:
        async with get_session() as session:
            r = await session.execute(
                select(NoFapStreak).where(NoFapStreak.user_id == user_id)
            )
            return r.scalar_one_or_none()

    async def start(self, user_id: int) -> tuple[NoFapStreak, bool]:
        """Begin (or resume tracking) a streak for this user.

        Returns `(streak, already_active)`. `already_active` is True when
        the user already has a running streak, in which case nothing is
        changed -- callers should treat this as "no-op, tell the user".
        """
        async with get_session() as session:
            r = await session.execute(
                select(NoFapStreak).where(NoFapStreak.user_id == user_id)
            )
            streak = r.scalar_one_or_none()
            now = datetime.now(timezone.utc)

            if streak is None:
                streak = NoFapStreak(user_id=user_id, started_at=now)
                session.add(streak)
                await session.flush()
                await session.refresh(streak)
                return streak, False

            if streak.started_at is not None:
                return streak, True

            streak.started_at = now
            await session.flush()
            await session.refresh(streak)
            return streak, False

    async def reset(self, user_id: int) -> NoFapStreak | None:
        """Record a relapse: bank the finished streak's length into
        `best_streak_days` if it's a new record, bump `reset_count`, and
        start a fresh streak from now. Returns None if the user has never
        started a streak (nothing to reset)."""
        async with get_session() as session:
            r = await session.execute(
                select(NoFapStreak).where(NoFapStreak.user_id == user_id)
            )
            streak = r.scalar_one_or_none()
            if streak is None or streak.started_at is None:
                return None

            now = datetime.now(timezone.utc)
            finished_days = max((now - _aware(streak.started_at)).days, 0)
            if finished_days > streak.best_streak_days:
                streak.best_streak_days = finished_days

            streak.last_reset_at = now
            streak.reset_count += 1
            streak.started_at = now
            await session.flush()
            await session.refresh(streak)
            logger.info("nofap reset: user=%d finished_days=%d", user_id, finished_days)
            return streak
