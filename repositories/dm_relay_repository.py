from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select

from database.connection import get_session
from models.models import DMRelayLink


class DMRelayRepository:
    async def add(self, src_channel_id: int, src_message_id: int, dst_channel_id: int, dst_message_id: int) -> None:
        async with get_session() as session:
            session.add(DMRelayLink(
                src_channel_id=src_channel_id, src_message_id=src_message_id,
                dst_channel_id=dst_channel_id, dst_message_id=dst_message_id,
            ))

    async def find_by_source(self, message_id: int) -> DMRelayLink | None:
        async with get_session() as session:
            r = await session.execute(select(DMRelayLink).where(DMRelayLink.src_message_id == message_id))
            return r.scalar_one_or_none()

    async def find_by_copy(self, message_id: int) -> DMRelayLink | None:
        async with get_session() as session:
            r = await session.execute(select(DMRelayLink).where(DMRelayLink.dst_message_id == message_id))
            return r.scalars().first()

    async def prune(self, older_than_days: int = 30) -> int:
        cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=older_than_days)
        async with get_session() as session:
            r = await session.execute(delete(DMRelayLink).where(DMRelayLink.created_at < cutoff))
            return r.rowcount or 0
