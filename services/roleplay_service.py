from __future__ import annotations

from dataclasses import dataclass, field

import discord

from repositories.achievement_repository import AchievementRepository
from repositories.interaction_repository import InteractionRepository
from repositories.relationship_repository import RelationshipRepository
from repositories.roleplay_profile_repository import RoleplayProfileRepository
from repositories.user_repository import UserRepository
from services.action_registry import ActionConfig, get_action
from services.gif_service import GifService
from utils.config import get_config
from utils.cooldowns import check_cooldown, set_cooldown
from utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ActionResult:
    message: str
    gif_url: str | None
    affection_gained: int
    xp_gained: int
    leveled_up: bool
    new_level: int
    new_achievements: list[str]
    is_relationship_bonus: bool


class RoleplayService:
    def __init__(self) -> None:
        self.config = get_config()
        self.gif_service = GifService()
        self.user_repo = UserRepository()
        self.interaction_repo = InteractionRepository()
        self.relationship_repo = RelationshipRepository()
        self.achievement_repo = AchievementRepository()
        self.roleplay_profile_repo = RoleplayProfileRepository()

    async def execute(
        self,
        action_name: str,
        author: discord.Member,
        target: discord.Member | None,
        guild_id: int,
    ) -> ActionResult | str:
        action = get_action(action_name)
        if not action:
            return "Unknown action."

        # Validate target
        if action.requires_target and not target:
            return "You need to specify a target for this action!"
        if target and target.id == author.id and not action.self_targetable:
            return "You can't use this action on yourself!"
        if target and target.bot:
            return "You can't use this action on a bot!"

        # Check cooldown (in-memory)
        remaining = check_cooldown(author.id, action_name)
        if remaining > 0:
            return f"⏳ Cooldown! Try again in **{remaining}s**."

        # Check target opt-out
        if target:
            settings = await self.user_repo.get_settings(target.id)
            if settings and not settings.allow_interactions:
                return f"**{target.display_name}** has interactions disabled."

        # Ensure DB records exist
        await self.user_repo.get_or_create(
            author.id, author.display_name, str(author.display_avatar.url)
        )
        if target:
            await self.user_repo.get_or_create(
                target.id, target.display_name, str(target.display_avatar.url)
            )

        # Relationship bonus
        affection = action.affection_gain
        is_partners = False
        if target:
            partner_id = await self.relationship_repo.get_partner_id(author.id)
            if partner_id == target.id:
                is_partners = True
                affection = int(affection * self.config.relationship_bonus)
                await self.relationship_repo.add_shared_affection(author.id, affection)

        # Apply XP + affection
        new_level, _, leveled_up = await self.user_repo.add_xp(author.id, action.xp_gain)
        new_affection = await self.user_repo.add_affection(author.id, affection)

        # Record interaction
        await self.interaction_repo.record(
            author_id=author.id,
            action=action_name,
            guild_id=guild_id,
            target_id=target.id if target else None,
            affection_given=affection,
            xp_given=action.xp_gain,
        )

        # Set cooldown
        set_cooldown(author.id, action_name, action.cooldown_seconds)

        # Check achievements
        total = await self.interaction_repo.get_count(author.id)
        new_ach = await self.achievement_repo.check_and_unlock(
            user_id=author.id,
            total_interactions=total,
            affection=new_affection,
            level=new_level,
        )

        # GIF
        gif_url = await self.gif_service.get_random_gif(action.gif_category)

        # Response text -- gender is entirely optional here (unlike the
        # requires_verification() gate in verification.py): a user who has
        # never run /consent just gets neutral pronouns, since none of
        # these commands (hug/pat/etc.) ever required setup before.
        author_profile = await self.roleplay_profile_repo.get(author.id)
        target_profile = await self.roleplay_profile_repo.get(target.id) if target else None
        target_name = target.display_name if target else author.display_name
        message = action.get_response(
            author.display_name,
            target_name,
            author_gender=author_profile.gender if author_profile else None,
            target_gender=target_profile.gender if target_profile else None,
        )

        return ActionResult(
            message=message,
            gif_url=gif_url,
            affection_gained=affection,
            xp_gained=action.xp_gain,
            leveled_up=leveled_up,
            new_level=new_level,
            new_achievements=[a.name for a in new_ach],
            is_relationship_bonus=is_partners,
        )
