from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select

from database.connection import get_session
from models.models import Achievement, UserAchievement
from utils.logging import get_logger

logger = get_logger(__name__)

ACHIEVEMENTS = [
    dict(key="first_interaction", name="First Steps", description="Perform your first interaction",
         icon="👣", category="interaction", condition_type="count", condition_value=1, xp_reward=50),
    dict(key="interactions_10", name="Getting Started", description="Perform 10 interactions",
         icon="⭐", category="interaction", condition_type="count", condition_value=10, xp_reward=75),
    dict(key="interactions_100", name="Social Butterfly", description="Perform 100 interactions",
         icon="🦋", category="interaction", condition_type="count", condition_value=100, xp_reward=200),
    dict(key="interactions_500", name="Interaction Master", description="Perform 500 interactions",
         icon="🌟", category="interaction", condition_type="count", condition_value=500, xp_reward=500,
         is_rare=True),
    dict(key="interactions_1000", name="Legend", description="Perform 1000 interactions",
         icon="👑", category="interaction", condition_type="count", condition_value=1000, xp_reward=1000,
         is_rare=True),
    dict(key="affection_100", name="Warm Heart", description="Reach 100 affection",
         icon="💛", category="progression", condition_type="affection", condition_value=100, xp_reward=100),
    dict(key="affection_1000", name="Beloved", description="Reach 1000 affection",
         icon="💖", category="progression", condition_type="affection", condition_value=1000, xp_reward=300),
    dict(key="affection_10000", name="Heartthrob", description="Reach 10,000 affection",
         icon="💗", category="progression", condition_type="affection", condition_value=10000, xp_reward=1000,
         is_rare=True),
    dict(key="level_5", name="Rising", description="Reach level 5",
         icon="🌱", category="progression", condition_type="level", condition_value=5, xp_reward=50),
    dict(key="level_10", name="Rising Star", description="Reach level 10",
         icon="⭐", category="progression", condition_type="level", condition_value=10, xp_reward=150),
    dict(key="level_25", name="Experienced", description="Reach level 25",
         icon="🏅", category="progression", condition_type="level", condition_value=25, xp_reward=400,
         is_rare=True),
    dict(key="level_50", name="Veteran", description="Reach level 50",
         icon="🎖️", category="progression", condition_type="level", condition_value=50, xp_reward=750,
         is_rare=True),
    dict(key="relationship_started", name="Taken", description="Enter your first relationship",
         icon="💕", category="relationship", condition_type="milestone", condition_value=1, xp_reward=100),
    dict(key="secret_dancer", name="???", description="???",
         icon="🕵️", category="special", condition_type="milestone", condition_value=0, xp_reward=500,
         is_hidden=True, is_rare=True),
]


class AchievementRepository:
    async def seed(self) -> None:
        async with get_session() as session:
            for data in ACHIEVEMENTS:
                r = await session.execute(
                    select(Achievement).where(Achievement.key == data["key"])
                )
                if not r.scalar_one_or_none():
                    ach = Achievement(**{
                        k: v for k, v in data.items()
                        if k in {c.name for c in Achievement.__table__.columns}
                    })
                    session.add(ach)
        logger.info("achievements seeded")

    async def get_all(self) -> list[Achievement]:
        async with get_session() as session:
            r = await session.execute(select(Achievement).order_by(Achievement.id))
            return list(r.scalars().all())

    async def get_user_achievements(self, user_id: int) -> list[UserAchievement]:
        async with get_session() as session:
            r = await session.execute(
                select(UserAchievement).where(UserAchievement.user_id == user_id)
            )
            return list(r.scalars().all())

    async def check_and_unlock(
        self,
        user_id: int,
        total_interactions: int,
        affection: int,
        level: int,
    ) -> list[Achievement]:
        unlocked: list[Achievement] = []
        async with get_session() as session:
            all_ach = (await session.execute(select(Achievement))).scalars().all()
            for ach in all_ach:
                # Skip already unlocked
                r = await session.execute(
                    select(UserAchievement).where(
                        UserAchievement.user_id == user_id,
                        UserAchievement.achievement_id == ach.id,
                        UserAchievement.is_unlocked == True,
                    )
                )
                if r.scalar_one_or_none():
                    continue

                met = False
                if ach.condition_type == "count":
                    met = total_interactions >= ach.condition_value
                elif ach.condition_type == "affection":
                    met = affection >= ach.condition_value
                elif ach.condition_type == "level":
                    met = level >= ach.condition_value

                if met:
                    r2 = await session.execute(
                        select(UserAchievement).where(
                            UserAchievement.user_id == user_id,
                            UserAchievement.achievement_id == ach.id,
                        )
                    )
                    ua = r2.scalar_one_or_none()
                    if not ua:
                        ua = UserAchievement(user_id=user_id, achievement_id=ach.id)
                        session.add(ua)
                    ua.is_unlocked = True
                    ua.progress = ach.condition_value
                    ua.unlocked_at = datetime.now(timezone.utc)
                    unlocked.append(ach)
        return unlocked
