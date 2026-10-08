from __future__ import annotations

import asyncio

import discord
from discord import app_commands
from discord.ext import commands

from database.connection import close_db, init_db
from utils.config import ConfigError, get_config
from utils.interactions import GENERIC_ERROR, respond
from utils.logging import get_logger, setup_logging

setup_logging()
logger = get_logger(__name__)

COGS = [
    "cogs.roleplay.roleplay_cog",
    "cogs.roleplay.role_cog",
    "cogs.profile.profile_cog",
    "cogs.relationships.relationships_cog",
    "cogs.achievements.achievements_cog",
    "cogs.economy.economy_cog",
    "cogs.games.games_cog",
    "cogs.movies.movies_cog",
    "cogs.nofap.nofap_cog",
    "cogs.settings.settings_cog",
    "cogs.moderation.moderation_cog",
    "cogs.dmlink.dmlink_cog",
    "cogs.persona.persona_cog",
    "cogs.presence.presence_cog",
    "cogs.dmgames.play_cog",
    "cogs.couple.couple_cog",
    "cogs.reddit.reddit_cog",
    "cogs.owner.owner_cog",
    "cogs.owner.tasks_cog",
    "cogs.help.help_cog",
]


class RoleplayBot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.members = True
        intents.presences = True  # auto-AFK on offline/invisible (see cogs/presence)
        intents.message_content = True  # persona channel replies and trivia-style games read message text
        super().__init__(
            command_prefix=commands.when_mentioned,
            intents=intents,
            help_command=None,
        )

    async def setup_hook(self) -> None:
        await init_db()

        from repositories.achievement_repository import AchievementRepository
        await AchievementRepository().seed()

        for cog in COGS:
            try:
                await self.load_extension(cog)
                logger.info("loaded: %s", cog)
            except Exception:
                logger.exception("failed to load %s", cog)

    async def on_ready(self) -> None:
        logger.info("ready: %s | guilds: %d", self.user, len(self.guilds))
        await self.change_presence(activity=discord.Game(name="with feelings 💕 | /help"))

    async def on_guild_join(self, guild: discord.Guild) -> None:
        from repositories.user_repository import GuildRepository
        await GuildRepository().get_or_create(guild.id)

    async def on_app_command_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ) -> None:
        if isinstance(error, app_commands.CheckFailure):
            return  # the check already answered the user (owner-only, ...)
        original = getattr(error, "original", error)
        if isinstance(original, discord.NotFound):
            logger.info("interaction expired or target deleted: %s", original)
            return
        if isinstance(original, discord.Forbidden):
            await respond(interaction, "I don't have permission to do that here. Check my channel permissions.", ephemeral=True)
            return
        logger.error("command %s failed", getattr(interaction.command, "qualified_name", "?"), exc_info=original)
        await respond(interaction, GENERIC_ERROR, ephemeral=True)

    async def close(self) -> None:
        from utils.http import close_http_session
        await close_http_session()
        await close_db()
        await super().close()


async def main() -> None:
    try:
        token = get_config().token
    except ConfigError as exc:
        raise SystemExit(f"Configuration error: {exc}") from exc
    bot = RoleplayBot()
    async with bot:
        await bot.start(token)


if __name__ == "__main__":
    asyncio.run(main())
