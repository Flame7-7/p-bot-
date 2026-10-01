from __future__ import annotations

import asyncio

import discord
from discord.ext import commands

from repositories.persona_repository import PersonaRepository
from utils.logging import get_logger

logger = get_logger(__name__)

OFFLINE_DELAY = 120  # seconds offline before AFK turns on (ignores brief flicker)
RECONCILE_DELAY = 5  # wait for member cache to populate after connecting


class PresenceCog(commands.Cog, name="Presence"):
    """Keeps AFK mode in sync with the user's Discord status for anyone
    with auto_afk on (persona replies in the server persona channel):
    offline/invisible for OFFLINE_DELAY seconds -> AFK on,
    back online -> AFK off. No DMs about it either way.

    This is stateless by design -- every check re-derives the correct AFK
    value from (a) the live presence and (b) auto_afk, rather than tracking
    "did auto-AFK turn this on" in memory. That in-memory-only version broke
    across restarts: after a redeploy, a member who was already online had
    no presence *transition* to trigger the on-return check, so a
    still-True afk_enabled from before the restart was left stuck on. The
    _reconcile() startup pass below exists specifically to fix that stuck
    state as soon as the bot reconnects, without waiting for a new status
    change.

    Needs the Presence Intent (code + Developer Portal) and mutual guilds
    with the user (Discord doesn't expose presence otherwise).
    """

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.persona_repo = PersonaRepository()
        self._pending: dict[int, asyncio.Task] = {}
        self._reconcile_task: asyncio.Task | None = None

    def cog_unload(self) -> None:
        for t in self._pending.values():
            t.cancel()
        if self._reconcile_task:
            self._reconcile_task.cancel()

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        if self._reconcile_task is None or self._reconcile_task.done():
            self._reconcile_task = asyncio.create_task(self._reconcile_all())

    async def _reconcile_all(self) -> None:
        await asyncio.sleep(RECONCILE_DELAY)
        try:
            profiles = await self.persona_repo.list_auto_afk_enabled()
        except Exception:
            logger.exception("could not load auto-AFK profiles for reconcile")
            return

        for profile in profiles:
            if not profile.persona_text:
                continue
            member = self._find_member(profile.user_id)
            if member is None:
                continue  # not in a mutual guild right now -- can't tell, leave it
            await self._sync(member.id, member.status == discord.Status.offline, profile.afk_enabled)

        logger.info("auto-AFK reconcile checked %d profile(s)", len(profiles))

    def _find_member(self, user_id: int) -> discord.Member | None:
        for guild in self.bot.guilds:
            m = guild.get_member(user_id)
            if m:
                return m
        return None

    async def _sync(self, user_id: int, is_away: bool, currently_enabled: bool) -> None:
        if is_away and not currently_enabled:
            await self.persona_repo.set_afk(user_id, True)
            logger.info("auto-AFK on for %s", user_id)
        elif not is_away and currently_enabled:
            await self.persona_repo.set_afk(user_id, False)
            logger.info("auto-AFK off for %s", user_id)

    @commands.Cog.listener()
    async def on_presence_update(self, before: discord.Member, after: discord.Member) -> None:
        if before.status == after.status:
            return

        uid = after.id
        if after.status == discord.Status.offline:
            if uid in self._pending:  # already counting down (multi-guild duplicates)
                return
            self._pending[uid] = asyncio.create_task(self._go_afk_later(uid))
            return

        # back online (online / idle / dnd)
        task = self._pending.pop(uid, None)
        if task:
            task.cancel()

        profile = await self.persona_repo.get(uid)
        if profile and profile.auto_afk and profile.persona_text:
            await self._sync(uid, is_away=False, currently_enabled=profile.afk_enabled)

    async def _go_afk_later(self, user_id: int) -> None:
        try:
            await asyncio.sleep(OFFLINE_DELAY)
            member = self._find_member(user_id)
            if member is None or member.status != discord.Status.offline:
                return
            profile = await self.persona_repo.get(user_id)
            if not profile or not profile.auto_afk or not profile.persona_text:
                return
            await self._sync(user_id, is_away=True, currently_enabled=profile.afk_enabled)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("auto-AFK go-away check failed")
        finally:
            self._pending.pop(user_id, None)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(PresenceCog(bot))
