from __future__ import annotations

from datetime import datetime

from sqlalchemy import delete, select

from database.connection import get_session
from models.models import CoupleGameStat, CoupleMilestone, JournalEntry


def pair(a: int, b: int) -> tuple[int, int]:
    """Canonical (low, high) ordering so a couple has one row regardless of who asks."""
    return (a, b) if a < b else (b, a)


class CoupleRepository:
    # ── game stats ───────────────────────────────────────────────────────────

    async def record_game(
        self, a: int, b: int, game: str, *, winner: int | None = None, draw: bool = False, points: int = 0
    ) -> None:
        low, high = pair(a, b)
        async with get_session() as session:
            r = await session.execute(
                select(CoupleGameStat).where(
                    CoupleGameStat.user_low_id == low,
                    CoupleGameStat.user_high_id == high,
                    CoupleGameStat.game == game,
                )
            )
            row = r.scalar_one_or_none()
            if row is None:
                row = CoupleGameStat(
                    user_low_id=low, user_high_id=high, game=game, plays=0, low_wins=0, high_wins=0, draws=0, points=0
                )
                session.add(row)
            row.plays += 1
            row.points += points
            if draw:
                row.draws += 1
            elif winner == low:
                row.low_wins += 1
            elif winner == high:
                row.high_wins += 1

    async def get_stats(self, a: int, b: int) -> list[CoupleGameStat]:
        low, high = pair(a, b)
        async with get_session() as session:
            r = await session.execute(
                select(CoupleGameStat)
                .where(CoupleGameStat.user_low_id == low, CoupleGameStat.user_high_id == high)
                .order_by(CoupleGameStat.plays.desc())
            )
            return list(r.scalars().all())

    # ── milestones ───────────────────────────────────────────────────────────

    async def add_milestone(self, a: int, b: int, title: str, when: datetime, yearly: bool, created_by: int) -> CoupleMilestone:
        low, high = pair(a, b)
        async with get_session() as session:
            row = CoupleMilestone(
                user_low_id=low, user_high_id=high, title=title, event_date=when, yearly=yearly, created_by=created_by
            )
            session.add(row)
            await session.flush()
            return row

    async def list_milestones(self, a: int, b: int) -> list[CoupleMilestone]:
        low, high = pair(a, b)
        async with get_session() as session:
            r = await session.execute(
                select(CoupleMilestone)
                .where(CoupleMilestone.user_low_id == low, CoupleMilestone.user_high_id == high)
                .order_by(CoupleMilestone.event_date)
            )
            return list(r.scalars().all())

    async def remove_milestone(self, a: int, b: int, milestone_id: int) -> bool:
        low, high = pair(a, b)
        async with get_session() as session:
            r = await session.execute(
                delete(CoupleMilestone).where(
                    CoupleMilestone.id == milestone_id,
                    CoupleMilestone.user_low_id == low,
                    CoupleMilestone.user_high_id == high,
                )
            )
            return (r.rowcount or 0) > 0

    # ── journal ──────────────────────────────────────────────────────────────

    async def add_journal(self, a: int, b: int, author_id: int, text: str, prompt: str | None) -> JournalEntry:
        low, high = pair(a, b)
        async with get_session() as session:
            row = JournalEntry(user_low_id=low, user_high_id=high, author_id=author_id, text=text, prompt=prompt)
            session.add(row)
            await session.flush()
            return row

    async def list_journal(self, a: int, b: int, limit: int = 20) -> list[JournalEntry]:
        low, high = pair(a, b)
        async with get_session() as session:
            r = await session.execute(
                select(JournalEntry)
                .where(JournalEntry.user_low_id == low, JournalEntry.user_high_id == high)
                .order_by(JournalEntry.created_at.desc(), JournalEntry.id.desc())
                .limit(limit)
            )
            return list(r.scalars().all())
