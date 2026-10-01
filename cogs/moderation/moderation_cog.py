from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy import select

from database.connection import get_session
from models.models import Profile, Statistics
from utils.interactions import respond


class ModerationCog(commands.Cog, name="Moderation"):
    """Owner-only maintenance commands."""

    help_category = ("🛡️", "Moderation")

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
        if isinstance(error, app_commands.CheckFailure):
            await respond(interaction, "Only the bot owner can use this.", ephemeral=True)
            return
        raise error

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if await self.bot.is_owner(interaction.user):
            return True
        raise app_commands.CheckFailure("owner only")

    @app_commands.command(name="resetuser", description="[Owner] Reset a user's stats and profile")
    @app_commands.default_permissions(administrator=True)
    async def resetuser(self, interaction: discord.Interaction, user: discord.User) -> None:
        async with get_session() as session:
            r = await session.execute(select(Profile).where(Profile.user_id == user.id))
            if p := r.scalar_one_or_none():
                p.level, p.xp, p.total_xp, p.affection = 1, 0, 0, 0
            r2 = await session.execute(select(Statistics).where(Statistics.user_id == user.id))
            if s := r2.scalar_one_or_none():
                s.total_given, s.total_received, s.daily_given, s.weekly_given = 0, 0, 0, 0
        await respond(interaction, f"✅ Reset **{user.display_name}**'s stats.", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ModerationCog(bot))
