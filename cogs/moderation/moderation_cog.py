from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy import select

from database.connection import get_session
from models.models import Profile, Statistics, User


class ModerationCog(commands.Cog, name="Moderation"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="botban", description="[Admin] Ban a user from using the bot")
    @app_commands.default_permissions(administrator=True)
    async def botban(self, interaction: discord.Interaction, user: discord.Member) -> None:
        async with get_session() as session:
            r = await session.execute(select(User).where(User.id == user.id))
            u = r.scalar_one_or_none()
            if u:
                u.is_banned = True
        await interaction.response.send_message(
            f"🔨 **{user.display_name}** is banned from using the bot."
        )

    @app_commands.command(name="botunban", description="[Admin] Unban a user from the bot")
    @app_commands.default_permissions(administrator=True)
    async def botunban(self, interaction: discord.Interaction, user: discord.Member) -> None:
        async with get_session() as session:
            r = await session.execute(select(User).where(User.id == user.id))
            u = r.scalar_one_or_none()
            if u:
                u.is_banned = False
        await interaction.response.send_message(
            f"✅ **{user.display_name}** can use the bot again."
        )

    @app_commands.command(name="resetuser", description="[Admin] Reset a user's stats and profile")
    @app_commands.default_permissions(administrator=True)
    async def resetuser(self, interaction: discord.Interaction, user: discord.Member) -> None:
        async with get_session() as session:
            r = await session.execute(select(Profile).where(Profile.user_id == user.id))
            p = r.scalar_one_or_none()
            if p:
                p.level, p.xp, p.total_xp, p.affection = 1, 0, 0, 0
            r2 = await session.execute(select(Statistics).where(Statistics.user_id == user.id))
            s = r2.scalar_one_or_none()
            if s:
                s.total_given, s.total_received, s.daily_given, s.weekly_given = 0, 0, 0, 0
        await interaction.response.send_message(
            f"✅ Reset **{user.display_name}**'s stats."
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ModerationCog(bot))
