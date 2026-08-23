from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select

from database.connection import get_session
from models.models import RoleplayProfile
from utils.logging import get_logger

logger = get_logger(__name__)

# Kept in one place so services/action_registry.py and verification.py
# agree on what a valid role/gender value is. "requires setup" note:
# only these values are ever accepted; everything else is rejected before
# it reaches the DB.
VALID_GENDERS = ("male", "female", "non-binary")


class RoleplayProfileRepository:
    """Persists the role-selection / consent flow that used to live only in
    verification.py's `user_profiles = {}` dict. Every read/write goes
    through the existing SQLite database via database/connection.py,
    following the same session-per-call pattern as the other repositories
    in this package (e.g. UserRepository), so there is exactly one source
    of truth and it survives bot restarts.
    """

    async def get(self, user_id: int) -> RoleplayProfile | None:
        async with get_session() as session:
            r = await session.execute(
                select(RoleplayProfile).where(RoleplayProfile.user_id == user_id)
            )
            return r.scalar_one_or_none()

    async def is_verified(self, user_id: int) -> bool:
        profile = await self.get(user_id)
        if not profile:
            return False
        return bool(profile.consent_given and profile.gender)

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
            # Changing role re-requires explicit re-agreement, same as the
            # original in-memory GenderSelect.finalize_selection behavior.
            profile.consent_given = False
            await session.flush()
            await session.refresh(profile)
            return profile

    async def set_consent(self, user_id: int, given: bool) -> RoleplayProfile:
        async with get_session() as session:
            r = await session.execute(
                select(RoleplayProfile).where(RoleplayProfile.user_id == user_id)
            )
            profile = r.scalar_one_or_none()
            if not profile:
                profile = RoleplayProfile(user_id=user_id)
                session.add(profile)
            profile.consent_given = given
            profile.consented_at = datetime.now(timezone.utc) if given else None
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
