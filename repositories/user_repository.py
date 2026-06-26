from __future__ import annotations

from sqlalchemy import select

from database.connection import get_session
from models.models import GuildSettings, Profile, Statistics, User, UserSettings
from utils.config import get_config
from utils.logging import get_logger

logger = get_logger(__name__)


class UserRepository:
    def __init__(self) -> None:
        self.config = get_config()

    async def get_or_create(
        self, user_id: int, username: str, avatar_url: str | None = None
    ) -> User:
        async with get_session() as session:
            result = await session.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if user:
                user.username = username
                if avatar_url:
                    user.avatar_url = avatar_url
                return user
            user = User(id=user_id, username=username, avatar_url=avatar_url)
            profile = Profile(user_id=user_id)
            stats = Statistics(user_id=user_id)
            settings = UserSettings(user_id=user_id)
            session.add_all([user, profile, stats, settings])
            await session.flush()
            logger.info("new user: %d %s", user_id, username)
            return user

    async def get_profile(self, user_id: int) -> Profile | None:
        async with get_session() as session:
            r = await session.execute(select(Profile).where(Profile.user_id == user_id))
            return r.scalar_one_or_none()

    async def get_stats(self, user_id: int) -> Statistics | None:
        async with get_session() as session:
            r = await session.execute(select(Statistics).where(Statistics.user_id == user_id))
            return r.scalar_one_or_none()

    async def get_settings(self, user_id: int) -> UserSettings | None:
        async with get_session() as session:
            r = await session.execute(select(UserSettings).where(UserSettings.user_id == user_id))
            return r.scalar_one_or_none()

    async def add_xp(self, user_id: int, xp: int) -> tuple[int, int, bool]:
        """Returns (new_level, new_xp, leveled_up)."""
        async with get_session() as session:
            r = await session.execute(select(Profile).where(Profile.user_id == user_id))
            profile = r.scalar_one_or_none()
            if not profile:
                return 1, 0, False
            profile.xp += xp
            profile.total_xp += xp
            old_level = profile.level
            profile.level = self._calc_level(profile.total_xp)
            leveled_up = profile.level > old_level
            return profile.level, profile.xp, leveled_up

    async def add_affection(self, user_id: int, amount: int) -> int:
        async with get_session() as session:
            r = await session.execute(select(Profile).where(Profile.user_id == user_id))
            profile = r.scalar_one_or_none()
            if not profile:
                return 0
            profile.affection += amount
            return profile.affection

    def _calc_level(self, total_xp: int) -> int:
        level = 1
        needed = self.config.base_xp
        xp = total_xp
        while xp >= needed and level < self.config.max_level:
            xp -= needed
            level += 1
            needed = int(needed * self.config.xp_multiplier)
        return level

    def xp_for_next_level(self, level: int) -> int:
        return int(self.config.base_xp * (self.config.xp_multiplier ** (level - 1)))


class GuildRepository:
    async def get_or_create(self, guild_id: int) -> GuildSettings:
        async with get_session() as session:
            r = await session.execute(
                select(GuildSettings).where(GuildSettings.guild_id == guild_id)
            )
            gs = r.scalar_one_or_none()
            if gs:
                return gs
            gs = GuildSettings(guild_id=guild_id)
            session.add(gs)
            await session.flush()
            return gs

    async def get(self, guild_id: int) -> GuildSettings | None:
        async with get_session() as session:
            r = await session.execute(
                select(GuildSettings).where(GuildSettings.guild_id == guild_id)
            )
            return r.scalar_one_or_none()
