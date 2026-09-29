from __future__ import annotations

import asyncio

import discord
from discord.ext import commands

from repositories.persona_repository import PersonaRepository
from utils.logging import get_logger

logger = get_logger(__name__)

OFFLINE_DELAY = 120  # seconds offline before AFK turns on (ignores brief flicker)


class PresenceCog(commands.Cog):
    """Silently flips AFK mode on when the user has been offline/invisible
    for OFFLINE_DELAY seconds, and off again when they come back. No DMs.

    Needs the Presence Intent (code + Developer Portal). Auto-AFK is only
    switched off on return if this cog was the one that switched it on, so a
    manual /afk on isn't cancelled by a status change.
    """

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.persona_repo = PersonaRepository()
        self._pending: dict[int, asyncio.Task] = {}
        self._auto_on: set[int] = set()

    def cog_unload(self) -> None:
        for t in self._pending.values():
            t.cancel()

    @commands.Cog.listener()
    async def on_presence_update(self, before: discord.Member, after: discord.Member) -> None:
        if before.status == after.status:
            return

        uid = after.id
        if after.status == discord.Status.offline:
            if uid in self._pending:  # already counting down (multi-guild duplicates)
                return
            self._pending[uid] = asyncio.create_task(self._go_afk_later(after))
            return

        # back online (online / idle / dnd)
        task = self._pending.pop(uid, None)
        if task:
            task.cancel()
        if uid in self._auto_on:
            self._auto_on.discard(uid)
            await self.persona_repo.set_afk(uid, False)

    async def _go_afk_later(self, member: discord.Member) -> None:
        uid = member.id
        try:
            await asyncio.sleep(OFFLINE_DELAY)
            current = member.guild.get_member(uid)
            if current is None or current.status != discord.Status.offline:
                return
            profile = await self.persona_repo.get(uid)
            if not profile or not profile.auto_afk or not profile.persona_text or profile.afk_enabled:
                return
            await self.persona_repo.set_afk(uid, True)
            self._auto_on.add(uid)
            logger.info("auto-AFK on for %s", uid)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("auto-AFK failed")
        finally:
            self._pending.pop(uid, None)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(PresenceCog(bot))
