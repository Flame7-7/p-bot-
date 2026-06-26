from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy import select

from database.connection import get_session
from models.models import Profile
from repositories.achievement_repository import AchievementRepository
from repositories.relationship_repository import RelationshipRepository
from repositories.user_repository import UserRepository
from views.embeds import build_profile_embed
from utils.logging import get_logger

logger = get_logger(__name__)


class ProfileCog(commands.Cog, name="Profile"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.user_repo = UserRepository()
        self.rel_repo = RelationshipRepository()
        self.ach_repo = AchievementRepository()

    @app_commands.command(name="profile", description="View your or someone's profile")
    @app_commands.describe(user="The user to view (defaults to you)")
    async def profile(self, interaction: discord.Interaction, user: discord.Member | None = None) -> None:
        await interaction.response.defer()
        target = user or interaction.user
        await self.user_repo.get_or_create(target.id, target.display_name, str(target.display_avatar.url))
        profile = await self.user_repo.get_profile(target.id)
        stats = await self.user_repo.get_stats(target.id)
        achs = await self.ach_repo.get_user_achievements(target.id)
        unlocked = sum(1 for a in achs if a.is_unlocked)

        rel_info = None
        partner_id = await self.rel_repo.get_partner_id(target.id)
        if partner_id and interaction.guild:
            partner = interaction.guild.get_member(partner_id)
            rel_info = f"💑 {partner.display_name}" if partner else "💑 Someone special"

        embed = build_profile_embed(
            user=target,  # type: ignore[arg-type]
            profile=profile,
            stats=stats,
            relationship_info=rel_info,
            achievements_count=unlocked,
        )
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="setbio", description="Set your profile bio")
    @app_commands.describe(bio="Your bio (max 200 characters)")
    async def setbio(self, interaction: discord.Interaction, bio: str) -> None:
        if len(bio) > 200:
            await interaction.response.send_message("Bio must be 200 characters or less.", ephemeral=True)
            return
        await self.user_repo.get_or_create(interaction.user.id, interaction.user.display_name)
        async with get_session() as session:
            r = await session.execute(select(Profile).where(Profile.user_id == interaction.user.id))
            p = r.scalar_one_or_none()
            if p:
                p.bio = bio
        await interaction.response.send_message("✅ Bio updated!", ephemeral=True)

    @app_commands.command(name="stats", description="View your interaction statistics")
    @app_commands.describe(user="User to view (defaults to you)")
    async def stats(self, interaction: discord.Interaction, user: discord.Member | None = None) -> None:
        await interaction.response.defer()
        target = user or interaction.user
        await self.user_repo.get_or_create(target.id, target.display_name)
        db_stats = await self.user_repo.get_stats(target.id)
        profile = await self.user_repo.get_profile(target.id)

        embed = discord.Embed(title=f"📊 {target.display_name}'s Stats", color=0x7289DA)
        embed.set_thumbnail(url=str(target.display_avatar.url))
        if db_stats:
            embed.add_field(name="🎯 Given", value=f"{db_stats.total_given:,}", inline=True)
            embed.add_field(name="🎁 Received", value=f"{db_stats.total_received:,}", inline=True)
            embed.add_field(name="📅 Today", value=f"{db_stats.daily_given:,}", inline=True)
            if db_stats.favorite_action:
                embed.add_field(name="❤️ Favorite", value=f"/{db_stats.favorite_action}", inline=True)
        if profile:
            embed.add_field(name="⭐ Level", value=str(profile.level), inline=True)
            embed.add_field(name="✨ Total XP", value=f"{profile.total_xp:,}", inline=True)
            embed.add_field(name="💕 Affection", value=f"{profile.affection:,}", inline=True)
        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ProfileCog(bot))
