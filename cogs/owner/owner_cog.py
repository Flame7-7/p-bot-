from __future__ import annotations

import re
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from repositories.achievement_repository import AchievementRepository
from services.action_registry import get_all_actions
from services.gif_service import GifService
from utils.cooldowns import cache_delete_prefix
from utils.logging import get_logger

logger = get_logger(__name__)

# Accept gifs separated by spaces, commas, AND/OR new lines in one paste,
# instead of one command invocation per link.
_SPLIT_RE = re.compile(r"[,\s]+")
_GIF_URL_RE = re.compile(r"^https?://\S+\.gif(\?\S*)?$", re.IGNORECASE)


async def _category_autocomplete(
    interaction: discord.Interaction, current: str
) -> list[app_commands.Choice[str]]:
    # There are 62 gif categories -- too many for a static Choice list
    # (Discord caps those at 25), so this uses autocomplete instead,
    # which supports searching a much longer list.
    categories = sorted({a.gif_category for a in get_all_actions().values()})
    current = current.lower()
    matches = [c for c in categories if current in c.lower()]
    return [app_commands.Choice(name=c, value=c) for c in matches[:25]]


def is_owner():
    async def predicate(interaction: discord.Interaction) -> bool:
        return await interaction.client.is_owner(interaction.user)
    return app_commands.check(predicate)


class OwnerCog(commands.Cog, name="Owner"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.gif_service = GifService()
        self.ach_repo = AchievementRepository()

    @commands.command(name="sync", hidden=True)
    @commands.is_owner()
    async def sync(self, ctx: commands.Context) -> None:
        synced = await self.bot.tree.sync()
        guild_counts: list[str] = []
        for guild in self.bot.guilds:
            try:
                guild_synced = await self.bot.tree.sync(guild=discord.Object(id=guild.id))
                guild_counts.append(f"{guild.name}: {len(guild_synced)}")
            except Exception as exc:
                logger.error("guild sync failed for %s: %s", guild.id, exc)
                guild_counts.append(f"{guild.name}: failed")

        summary = ", ".join(guild_counts[:10])
        if len(guild_counts) > 10:
            summary += f" (+{len(guild_counts) - 10} more)"
        await ctx.send(
            f"✅ Synced **{len(synced)}** global slash commands and "
            f"**{len(guild_counts)}** guild command sets."
            + (f"\\n{summary}" if summary else "")
        )

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

    # ---------------- /gif add: bulk-add without attachments or a text file ----------------

    gif_group = app_commands.Group(
        name="gif", description="Manage the gif library used by roleplay commands"
    )

    @gif_group.command(name="add", description="Add one or more gifs to a category in a single command")
    @app_commands.describe(
        category="Which roleplay action this gif shows up for (start typing to search)",
        urls="One or more direct .gif URLs — separate with spaces, commas, or new lines",
    )
    @app_commands.autocomplete(category=_category_autocomplete)
    @is_owner()
    async def gif_add(self, interaction: discord.Interaction, category: str, urls: str) -> None:
        valid_categories = {a.gif_category for a in get_all_actions().values()}
        if category not in valid_categories:
            await interaction.response.send_message(
                f"❌ `{category}` isn't a known category. Start typing in the `category` "
                f"field to pick from the list.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)

        candidates = [u for u in _SPLIT_RE.split(urls.strip()) if u]
        added, duplicates, invalid = [], [], []

        for url in candidates:
            if not _GIF_URL_RE.match(url):
                invalid.append(url)
                continue
            if await self.gif_service.gif_exists(category, url):
                duplicates.append(url)
                continue
            try:
                await self.gif_service.add_gif(category, url)
                added.append(url)
            except Exception as e:
                logger.error("failed to add gif %s: %s", url, e)
                invalid.append(url)

        lines = [f"✅ Added **{len(added)}** gif(s) to `{category}`."]
        if duplicates:
            lines.append(f"↩️ Skipped {len(duplicates)} already in the library.")
        if invalid:
            lines.append(f"⚠️ Skipped {len(invalid)} invalid link(s) — must be a direct `.gif` URL.")

        embed = discord.Embed(
            title="Gif library updated",
            description="\n".join(lines),
            color=0x2ECC71,
        )
        if invalid:
            embed.add_field(name="Invalid links", value="\n".join(invalid[:10]), inline=False)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @gif_group.command(name="list", description="See how many gifs a category has")
    @app_commands.autocomplete(category=_category_autocomplete)
    @is_owner()
    async def gif_list(self, interaction: discord.Interaction, category: str) -> None:
        from database.connection import get_session
        from models.models import GIF
        from sqlalchemy import select

        async with get_session() as session:
            result = await session.execute(select(GIF.url).where(GIF.category == category))
            urls = [r[0] for r in result.all()]

        if not urls:
            await interaction.response.send_message(f"No gifs for `{category}` yet.", ephemeral=True)
            return

        embed = discord.Embed(
            title=f"Gifs for `{category}` ({len(urls)})",
            description="\n".join(urls[:20]),
            color=0x2ECC71,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def cog_app_command_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ) -> None:
        if isinstance(error, app_commands.CheckFailure):
            await interaction.response.send_message("Owner-only command.", ephemeral=True)
        else:
            raise error

    # ---------------- existing bulk-add paths (attachments / text file) ----------------

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