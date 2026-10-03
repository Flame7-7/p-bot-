from __future__ import annotations

from sqlalchemy import select

from database.connection import get_session
from models.models import RoleplayProfile
from utils.logging import get_logger

logger = get_logger(__name__)

# Kept in one place so services/action_registry.py and cogs/roleplay/role_cog.py
# agree on what a valid role/gender value is. Only these values are ever
# accepted; everything else is rejected before it reaches the DB.
VALID_GENDERS = ("male", "female", "non-binary")


class RoleplayProfileRepository:
    """Persists each user's role (pronoun choice) in the SQLite database via
    database/connection.py, using the same session-per-call pattern as the
    other repositories.
    """

    async def get(self, user_id: int) -> RoleplayProfile | None:
        async with get_session() as session:
            r = await session.execute(
                select(RoleplayProfile).where(RoleplayProfile.user_id == user_id)
            )
            return r.scalar_one_or_none()

    async def set_gender(self, user_id: int, gender: str) -> RoleplayProfile:
        if gender not in VALID_GENDERS:
            raise ValueError(f"invalid gender {gender!r}; must be one of {VALID_GENDERS}")
        async with get_session() as session:
            r = await session.execute(
                select(RoleplayProfile).where(RoleplayProfile.user_id == user_id)
            )
            profile = r.scalar_one_or_none()
            if not profile:
                profile = RoleplayProfile(user_id=user_id)
                session.add(profile)
            profile.gender = gender
            await session.flush()
            await session.refresh(profile)
            return profile

    async def reset(self, user_id: int) -> None:
        async with get_session() as session:
            r = await session.execute(
                select(RoleplayProfile).where(RoleplayProfile.user_id == user_id)
            )
            profile = r.scalar_one_or_none()
            if profile:
                await session.delete(profile)
