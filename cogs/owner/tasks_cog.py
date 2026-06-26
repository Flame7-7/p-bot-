from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from discord.ext import commands, tasks
from sqlalchemy import update

from database.connection import get_session
from models.models import Statistics
from utils.logging import get_logger

logger = get_logger(__name__)


class TasksCog(commands.Cog, name="Tasks"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._daily_reset.start()

    def cog_unload(self) -> None:
        self._daily_reset.cancel()

    @tasks.loop(hours=24)
    async def _daily_reset(self) -> None:
        try:
            async with get_session() as session:
                await session.execute(
                    update(Statistics).values(
                        daily_given=0,
                        last_daily_reset=datetime.now(timezone.utc),
                    )
                )
            # Clear leaderboard cache
            from utils.cooldowns import cache_delete_prefix
            cache_delete_prefix("lb:")
            logger.info("daily reset complete")
        except Exception as e:
            logger.error("daily reset failed: %s", e)

    @_daily_reset.before_loop
    async def _before_daily(self) -> None:
        await self.bot.wait_until_ready()
        now = datetime.now(timezone.utc)
        seconds_to_midnight = (24 - now.hour) * 3600 - now.minute * 60 - now.second
        await asyncio.sleep(seconds_to_midnight)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TasksCog(bot))
