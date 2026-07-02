from __future__ import annotations

import io
import aiohttp
import discord
from discord.ext import commands
from typing import Optional

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

    @commands.command(name="addgifs", hidden=True)
    @commands.is_owner()
    async def addgifs(
        self,
        ctx: commands.Context,
        category: str,
        name_prefix: str,
        attachments: commands.Greedy[discord.Attachment],
    ) -> None:
        """Bulk add multiple GIFs from attachments (up to 25). Supports .gif, .webp, .mp4, and other video/image formats."""
        if not attachments:
            await ctx.send("❌ Please attach GIF/video files to this command.")
            return

        # Valid file extensions
        valid_extensions = {'.gif', '.webp', '.mp4', '.mov', '.avi', '.webm', '.jpg', '.jpeg', '.png'}

        added = 0
        failed = 0
        for i, attachment in enumerate(attachments[:25], start=1):
            try:
                # Check file extension
                filename_lower = attachment.filename.lower()
                if not any(filename_lower.endswith(ext) for ext in valid_extensions):
                    logger.warning(f"Skipping {attachment.filename}: invalid file type")
                    failed += 1
                    continue
                    
                gif = await self.gif_service.add_gif(
                    category, attachment.url, name=f"{name_prefix}_{i}"
                )
                added += 1
            except Exception as e:
                logger.error(f"Failed to add {attachment.filename}: {e}")
                failed += 1

        await ctx.send(
            f"✅ Added **{added}** GIFs to `{category}`. "
            f"Files named `{name_prefix}_1`, `{name_prefix}_2`, etc. Failed: **{failed}**"
        )

    @commands.command(name="addgifsfromlist", hidden=True)
    @commands.is_owner()
    async def addgifsfromlist(
        self,
        ctx: commands.Context,
        category: str,
        name_prefix: str,
        text_file: Optional[discord.Attachment] = None,
    ) -> None:
        """Add GIFs from a text file containing URLs (one per line)"""
        if not text_file or not text_file.filename.endswith(".txt"):
            await ctx.send("❌ Please attach a .txt file with GIF URLs (one per line).")
            return

        try:
            content = await text_file.read()
            urls = [line.strip() for line in content.decode("utf-8").splitlines() if line.strip()]
        except Exception as e:
            await ctx.send(f"❌ Failed to read file: {e}")
            return

        if not urls:
            await ctx.send("❌ No URLs found in the file.")
            return

        added = 0
        failed = 0
        for i, url in enumerate(urls[:50], start=1):
            try:
                gif = await self.gif_service.add_gif(
                    category, url, name=f"{name_prefix}_{i}"
                )
                added += 1
            except Exception as e:
                logger.error(f"Failed to add {url}: {e}")
                failed += 1

        await ctx.send(
            f"✅ Added **{added}** GIFs to `{category}`. "
            f"Files named `{name_prefix}_1`, `{name_prefix}_2`, etc. Failed: **{failed}**"
        )

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
