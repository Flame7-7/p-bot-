from __future__ import annotations

from sqlalchemy import select

from database.connection import get_session
from models.models import PersonaProfile


class PersonaRepository:
    async def get(self, user_id: int) -> PersonaProfile | None:
        async with get_session() as session:
            r = await session.execute(select(PersonaProfile).where(PersonaProfile.user_id == user_id))
            return r.scalar_one_or_none()

    async def _get_or_create(self, session, user_id: int) -> PersonaProfile:
        r = await session.execute(select(PersonaProfile).where(PersonaProfile.user_id == user_id))
        p = r.scalar_one_or_none()
        if not p:
            p = PersonaProfile(user_id=user_id)
            session.add(p)
        return p

    async def set_persona_text(self, user_id: int, text: str) -> PersonaProfile:
        async with get_session() as session:
            p = await self._get_or_create(session, user_id)
            p.persona_text = text
            await session.flush()
            return p

    async def set_afk(self, user_id: int, enabled: bool) -> PersonaProfile:
        async with get_session() as session:
            p = await self._get_or_create(session, user_id)
            p.afk_enabled = enabled
            await session.flush()
            return p

    async def set_label(self, user_id: int, visible: bool) -> PersonaProfile:
        async with get_session() as session:
            p = await self._get_or_create(session, user_id)
            p.label_replies = visible
            await session.flush()
            return p

    async def set_auto_afk(self, user_id: int, enabled: bool) -> PersonaProfile:
        async with get_session() as session:
            p = await self._get_or_create(session, user_id)
            p.auto_afk = enabled
            await session.flush()
            return p
