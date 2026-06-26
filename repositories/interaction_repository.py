from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import desc, func, select

from database.connection import get_session
from models.models import Interaction, Profile, Statistics
from utils.logging import get_logger

logger = get_logger(__name__)


class InteractionRepository:
    async def record(
        self,
        author_id: int,
        action: str,
        guild_id: int,
        target_id: int | None = None,
        affection_given: int = 0,
        xp_given: int = 0,
    ) -> None:
        async with get_session() as session:
            interaction = Interaction(
                author_id=author_id,
                target_id=target_id,
                guild_id=guild_id,
                action=action,
                affection_given=affection_given,
                xp_given=xp_given,
            )
            session.add(interaction)

            # Update author stats
            r = await session.execute(
                select(Statistics).where(Statistics.user_id == author_id)
            )
            stats = r.scalar_one_or_none()
            if stats:
                now = datetime.now(timezone.utc)
                if stats.last_daily_reset.date() < now.date():
                    stats.daily_given = 0
                    stats.last_daily_reset = now
                stats.total_given += 1
                stats.daily_given += 1
                stats.weekly_given += 1

            # Update target stats
            if target_id:
                r2 = await session.execute(
                    select(Statistics).where(Statistics.user_id == target_id)
                )
                tstats = r2.scalar_one_or_none()
                if tstats:
                    tstats.total_received += 1

    async def get_count(self, user_id: int, action: str | None = None) -> int:
        async with get_session() as session:
            q = select(func.count(Interaction.id)).where(
                Interaction.author_id == user_id
            )
            if action:
                q = q.where(Interaction.action == action)
            r = await session.execute(q)
            return r.scalar_one() or 0

    async def get_leaderboard(self, category: str, limit: int = 10) -> list[dict]:
        async with get_session() as session:
            if category == "affection":
                r = await session.execute(
                    select(Profile.user_id, Profile.affection)
                    .order_by(desc(Profile.affection))
                    .limit(limit)
                )
                return [{"user_id": row[0], "value": row[1]} for row in r.all()]
            elif category == "level":
                r = await session.execute(
                    select(Profile.user_id, Profile.level, Profile.total_xp)
                    .order_by(desc(Profile.total_xp))
                    .limit(limit)
                )
                return [{"user_id": row[0], "value": row[1]} for row in r.all()]
            elif category == "interactions":
                r = await session.execute(
                    select(Statistics.user_id, Statistics.total_given)
                    .order_by(desc(Statistics.total_given))
                    .limit(limit)
                )
                return [{"user_id": row[0], "value": row[1]} for row in r.all()]
        return []
