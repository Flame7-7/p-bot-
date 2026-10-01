from __future__ import annotations

from sqlalchemy import select

from database.connection import get_session
from models.models import PersonaChannel, PersonaProfile


class PersonaRepository:
    async def get(self, user_id: int) -> PersonaProfile | None:
        async with get_session() as session:
            r = await session.execute(select(PersonaProfile).where(PersonaProfile.user_id == user_id))
            return r.scalar_one_or_none()

    async def get_many(self, user_ids: list[int]) -> dict[int, PersonaProfile]:
        if not user_ids:
            return {}
        async with get_session() as session:
            r = await session.execute(select(PersonaProfile).where(PersonaProfile.user_id.in_(user_ids)))
            return {p.user_id: p for p in r.scalars().all()}

    async def _update(self, user_id: int, **fields) -> PersonaProfile:
        async with get_session() as session:
            r = await session.execute(select(PersonaProfile).where(PersonaProfile.user_id == user_id))
            p = r.scalar_one_or_none()
            if p is None:
                p = PersonaProfile(user_id=user_id)
                session.add(p)
            for key, value in fields.items():
                setattr(p, key, value)
            await session.flush()
            return p

    async def set_persona_text(self, user_id: int, text: str) -> PersonaProfile:
        return await self._update(user_id, persona_text=text)

    async def set_afk(self, user_id: int, enabled: bool) -> PersonaProfile:
        return await self._update(user_id, afk_enabled=enabled)

    async def set_label(self, user_id: int, visible: bool) -> PersonaProfile:
        return await self._update(user_id, label_replies=visible)

    async def set_auto_afk(self, user_id: int, enabled: bool) -> PersonaProfile:
        return await self._update(user_id, auto_afk=enabled)

    async def list_auto_afk_enabled(self) -> list[PersonaProfile]:
        async with get_session() as session:
            r = await session.execute(select(PersonaProfile).where(PersonaProfile.auto_afk.is_(True)))
            return list(r.scalars().all())


class PersonaChannelRepository:
    """Guild ↔ persona channel configuration."""

    async def get(self, guild_id: int) -> PersonaChannel | None:
        async with get_session() as session:
            r = await session.execute(select(PersonaChannel).where(PersonaChannel.guild_id == guild_id))
            return r.scalar_one_or_none()

    async def set(self, guild_id: int, channel_id: int, configured_by: int | None = None) -> PersonaChannel:
        async with get_session() as session:
            r = await session.execute(select(PersonaChannel).where(PersonaChannel.guild_id == guild_id))
            row = r.scalar_one_or_none()
            if row is None:
                row = PersonaChannel(guild_id=guild_id, channel_id=channel_id)
                session.add(row)
            row.channel_id = channel_id
            row.enabled = True
            row.configured_by = configured_by
            await session.flush()
            return row

    async def disable(self, guild_id: int) -> bool:
        async with get_session() as session:
            r = await session.execute(select(PersonaChannel).where(PersonaChannel.guild_id == guild_id))
            row = r.scalar_one_or_none()
            if row is None or not row.enabled:
                return False
            row.enabled = False
            return True

    async def all_enabled(self) -> dict[int, int]:
        """guild_id -> channel_id for every enabled guild (loaded into a cache at startup)."""
        async with get_session() as session:
            r = await session.execute(select(PersonaChannel).where(PersonaChannel.enabled.is_(True)))
            return {row.guild_id: row.channel_id for row in r.scalars().all()}
