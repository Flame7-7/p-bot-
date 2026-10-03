from __future__ import annotations

import random

import discord
from discord import app_commands
from discord.ext import commands

from services.reddit_service import (
    RedditError, RedditPost, RedditService, get_reddit_service, normalise_subreddit,
)
from utils.interactions import GENERIC_ERROR, OwnedView, respond
from utils.logging import get_logger

logger = get_logger(__name__)

ORANGE = 0xFF4500
TEXT_PREVIEW = 350


def compact(n: int) -> str:
    """12400 -> '12.4k'."""
    for limit, suffix in ((1_000_000, "m"), (1_000, "k")):
        if n >= limit:
            value = n / limit
            return f"{value:.1f}".rstrip("0").rstrip(".") + suffix
    return str(n)


def build_post_embed(post: RedditPost, position: int, total: int) -> discord.Embed:
    embed = discord.Embed(title=post.title[:256], url=post.permalink, color=ORANGE)
    embed.set_author(name=f"r/{post.subreddit}")

    if post.kind == "text" and post.text:
        text = post.text.strip()
        embed.description = text[:TEXT_PREVIEW] + ("…" if len(text) > TEXT_PREVIEW else "")
    elif post.kind == "video":
        embed.description = "🎬 Video post — open it on Reddit to watch."
    elif post.kind == "link":
        embed.description = f"🔗 {post.url[:300]}"

    if post.image_url:
        embed.set_image(url=post.image_url)

    embed.add_field(name="⬆️ Upvotes", value=compact(post.score), inline=True)
    embed.add_field(name="💬 Comments", value=compact(post.num_comments), inline=True)
    embed.add_field(name="👤 Author", value=f"u/{post.author}", inline=True)
    if post.flair:
        embed.add_field(name="🏷️ Flair", value=post.flair[:100], inline=True)
    embed.set_footer(text=f"Post {position}/{total} • Reddit")
    return embed


class RedditView(OwnedView):
    """Browse an already-fetched listing. Buttons never touch the Reddit API."""

    def __init__(self, owner_id: int, posts: list[RedditPost], *, shuffle: bool = False) -> None:
        super().__init__([owner_id], timeout=600)
        self.posts = posts
        self.index = random.randrange(len(posts)) if shuffle else 0
        self._sync()

    @property
    def post(self) -> RedditPost:
        return self.posts[self.index]

    def embed(self) -> discord.Embed:
        return build_post_embed(self.post, self.index + 1, len(self.posts))

    def _sync(self) -> None:
        self.previous.disabled = self.index <= 0
        self.next.disabled = self.index >= len(self.posts) - 1
        self.random_btn.disabled = len(self.posts) < 2
        for item in [i for i in self.children if getattr(i, "url", None)]:
            self.remove_item(item)
        self.add_item(discord.ui.Button(label="View Post", url=self.post.permalink, row=1))

    async def _show(self, interaction: discord.Interaction) -> None:
        self._sync()
        await interaction.response.edit_message(embed=self.embed(), view=self)

    @discord.ui.button(label="Previous", emoji="⬅️", style=discord.ButtonStyle.secondary, row=0)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.index = max(0, self.index - 1)
        await self._show(interaction)

    @discord.ui.button(label="Next", emoji="➡️", style=discord.ButtonStyle.primary, row=0)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.index = min(len(self.posts) - 1, self.index + 1)
        await self._show(interaction)

    @discord.ui.button(label="Random", emoji="🔄", style=discord.ButtonStyle.secondary, row=0)
    async def random_btn(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        choices = [i for i in range(len(self.posts)) if i != self.index]
        if choices:
            self.index = random.choice(choices)
        await self._show(interaction)


class RedditCog(commands.Cog, name="Reddit"):
    """`/reddit <subreddit>` — browse posts with the official Reddit API."""

    help_category = ("🌐", "Reddit")

    def __init__(self, bot: commands.Bot, service: RedditService | None = None) -> None:
        self.bot = bot
        self.service = service or get_reddit_service()

    @staticmethod
    def _allows_nsfw(interaction: discord.Interaction) -> bool:
        """Adult posts only in age-restricted server channels; never in DMs or ordinary channels."""
        channel = interaction.channel
        if interaction.guild is None or isinstance(channel, (discord.DMChannel, discord.GroupChannel)):
            return False
        return bool(getattr(channel, "is_nsfw", lambda: False)())

    @app_commands.command(name="reddit", description="Show a post from a subreddit")
    @app_commands.describe(
        subreddit="e.g. cats (r/cats also works)",
        sort="How to pick posts (default: hot)",
        timeframe="Only for 'top'",
    )
    @app_commands.choices(
        sort=[
            app_commands.Choice(name="hot", value="hot"),
            app_commands.Choice(name="top", value="top"),
            app_commands.Choice(name="new", value="new"),
            app_commands.Choice(name="random", value="random"),
        ],
        timeframe=[app_commands.Choice(name=t, value=t) for t in ("day", "week", "month", "year", "all")],
    )
    async def reddit(
        self,
        interaction: discord.Interaction,
        subreddit: str,
        sort: app_commands.Choice[str] | None = None,
        timeframe: app_commands.Choice[str] | None = None,
    ) -> None:
        mode = sort.value if sort else "hot"
        await interaction.response.defer()  # the API call can take longer than Discord's 3 seconds
        try:
            name = normalise_subreddit(subreddit)
            posts = await self.service.get_posts(
                name,
                "hot" if mode == "random" else mode,
                timeframe.value if timeframe else "week",
                allow_nsfw=self._allows_nsfw(interaction),
            )
        except RedditError as exc:
            await self._fail(interaction, exc.user_message)
            return
        except Exception:
            logger.exception("reddit command failed")
            await self._fail(interaction, GENERIC_ERROR)
            return

        view = RedditView(interaction.user.id, posts, shuffle=mode == "random")
        try:
            view.message = await interaction.followup.send(embed=view.embed(), view=view, wait=True)
        except (discord.NotFound, discord.HTTPException):
            logger.info("interaction expired before the reddit post could be sent")

    @staticmethod
    async def _fail(interaction: discord.Interaction, message: str) -> None:
        try:
            await interaction.edit_original_response(content=f"⚠️ {message}")
        except (discord.NotFound, discord.HTTPException):
            await respond(interaction, f"⚠️ {message}", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(RedditCog(bot))
