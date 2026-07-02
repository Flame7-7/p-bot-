from __future__ import annotations

import asyncio
import traceback

import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy import select

from database.connection import close_db, init_db
from utils.config import get_config
from utils.logging import get_logger, setup_logging

setup_logging()
logger = get_logger(__name__)

COGS = [
    "cogs.roleplay.roleplay_cog",
    "cogs.profile.profile_cog",
    "cogs.relationships.relationships_cog",
    "cogs.achievements.achievements_cog",
    "cogs.economy.economy_cog",
    "cogs.games.games_cog",
    "cogs.settings.settings_cog",
    "cogs.moderation.moderation_cog",
    "cogs.owner.owner_cog",
    "cogs.owner.help_cog",
    "cogs.owner.tasks_cog",
]


class RoleplayBot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.members = True
        super().__init__(
            command_prefix=commands.when_mentioned,
            intents=intents,
            help_command=None,
        )

    async def setup_hook(self) -> None:
        await init_db()

        # Seed achievements on first run
        from repositories.achievement_repository import AchievementRepository
        await AchievementRepository().seed()

        for cog in COGS:
            try:
                await self.load_extension(cog)
                logger.info("loaded: %s", cog)
            except Exception:
                logger.error("failed to load %s:\n%s", cog, traceback.format_exc())

    async def on_ready(self) -> None:
        logger.info("ready: %s | guilds: %d", self.user, len(self.guilds))
        await self.change_presence(activity=discord.Game(name="with feelings 💕 | /help"))

    async def on_guild_join(self, guild: discord.Guild) -> None:
        from repositories.user_repository import GuildRepository
        await GuildRepository().get_or_create(guild.id)

    async def on_app_command_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        # Block banned users
        if interaction.guild_id:
            from database.connection import get_session
            from models.models import User
            async with get_session() as session:
                r = await session.execute(select(User).where(User.id == interaction.user.id))
                u = r.scalar_one_or_none()
                if u and u.is_banned:
                    try:
                        await interaction.response.send_message("🚫 You are banned from using this bot.", ephemeral=True)
                    except Exception:
                        pass
                    return

        logger.error("command error: %s", error)
        msg = "Something went wrong. Please try again!"
        try:
            if interaction.response.is_done():
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await interaction.response.send_message(msg, ephemeral=True)
        except Exception:
            pass

    async def close(self) -> None:
        await close_db()
        await super().close()


async def main() -> None:
    bot = RoleplayBot()
    async with bot:
        await bot.start(get_config().token)


if __name__ == "__main__":
    asyncio.run(main())
