from __future__ import annotations

import discord
from discord.ext import commands

from repositories.achievement_repository import AchievementRepository
from services.gif_service import GifService
from utils.cooldowns import cache_delete_prefix
from utils.logging import get_logger

logger = get_logger(__name__)


class OwnerCog(commands.Cog, name="Owner"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.gif_service = GifService()
        self.ach_repo = AchievementRepository()

    @commands.command(name="sync", hidden=True)
    @commands.is_owner()
    async def sync(self, ctx: commands.Context) -> None:
        synced = await self.bot.tree.sync()
        await ctx.send(f"✅ Synced **{len(synced)}** slash commands globally.")

    @commands.command(name="seed", hidden=True)
    @commands.is_owner()
    async def seed(self, ctx: commands.Context) -> None:
        await self.ach_repo.seed()
        await ctx.send("✅ Achievements seeded.")

    @commands.command(name="addgif", hidden=True)
    @commands.is_owner()
    async def addgif(self, ctx: commands.Context, category: str, *, url: str) -> None:
        gif = await self.gif_service.add_gif(category, url)
        await ctx.send(f"✅ Added GIF `#{gif.id}` to `{category}`.")

    @commands.command(name="clearcache", hidden=True)
    @commands.is_owner()
    async def clearcache(self, ctx: commands.Context, prefix: str = "") -> None:
        deleted = cache_delete_prefix(prefix)
        await ctx.send(f"✅ Cleared **{deleted}** cache entries matching `{prefix or '*'}`.")

    @commands.command(name="botstats", hidden=True)
    @commands.is_owner()
    async def botstats(self, ctx: commands.Context) -> None:
        embed = discord.Embed(title="🤖 Bot Stats", color=0x7289DA)
        embed.add_field(name="Guilds", value=str(len(self.bot.guilds)))
        embed.add_field(name="Users", value=str(sum(g.member_count or 0 for g in self.bot.guilds)))
        embed.add_field(name="Latency", value=f"{self.bot.latency * 1000:.1f}ms")
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(OwnerCog(bot))
