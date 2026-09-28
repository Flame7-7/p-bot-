from __future__ import annotations

import discord
from discord.ext import commands

from repositories.persona_repository import PersonaRepository
from utils.logging import get_logger

logger = get_logger(__name__)

AWAY_STATUSES = (discord.Status.offline,)  # Discord reports "invisible" as offline to bots too


class PresenceCog(commands.Cog):
    """Auto-flips AFK mode on/off based on the user's Discord status, for
    anyone with auto_afk left on (the default — see /afk auto).

    Requires the Presence Intent enabled both in code (main.py) and in the
    Discord Developer Portal for this bot application, and only fires for
    servers the bot and the user share (Discord doesn't expose presence
    outside of mutual guilds).
    """

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.persona_repo = PersonaRepository()

    @commands.Cog.listener()
    async def on_presence_update(self, before: discord.Member, after: discord.Member) -> None:
        if before.status == after.status:
            return

        profile = await self.persona_repo.get(after.id)
        if not profile or not profile.auto_afk or not profile.persona_text:
            return

        is_away = after.status in AWAY_STATUSES

        if is_away and not profile.afk_enabled:
            await self.persona_repo.set_afk(after.id, True)
            await self._notify(after, True)
        elif not is_away and profile.afk_enabled:
            await self.persona_repo.set_afk(after.id, False)
            await self._notify(after, False)

    async def _notify(self, member: discord.Member, enabled: bool) -> None:
        try:
            if enabled:
                await member.send(
                    "🤖 Went offline, so AFK auto-reply just turned **on** for your partner's DMs. "
                    "`/afk auto off` if you don't want this."
                )
            else:
                await member.send("👋 Welcome back — AFK auto-reply turned **off**, you're answering yourself again.")
        except discord.Forbidden:
            pass


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(PresenceCog(bot))
