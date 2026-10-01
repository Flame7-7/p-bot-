from __future__ import annotations

import re

import discord
from discord.ext import commands

from repositories.relationship_repository import RelationshipRepository
from utils.interactions import resolve_user, safe_dm
from utils.logging import get_logger

logger = get_logger(__name__)

# A bare gif/video link is sent as plain content so Discord unfurls and plays it
# (links inside an embed description never preview).
MEDIA_LINK_RE = re.compile(
    r"https?://\S+\.(?:gif|png|jpe?g|webp|mp4|webm|mov)(?:\?\S*)?|"
    r"https?://(?:www\.)?(?:tenor\.com|giphy\.com|media\.giphy\.com)/\S+",
    re.IGNORECASE,
)
MAX_RELAY_FILES = 10


class DMLinkCog(commands.Cog, name="DM Link"):
    """Relays DMs to the bot between two linked partners (see /propose).

    Text, gifs, images and videos sent to the bot arrive in the partner's DMs.
    This is a plain relay — persona/AI replies never run in DMs (see cogs/persona).
    """

    help_category = ("💕", "Couple")

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.rel_repo = RelationshipRepository()

    @commands.Cog.listener("on_message")
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or not isinstance(message.channel, discord.DMChannel):
            return

        content = message.content.strip()
        if not content and not message.attachments:
            return

        recipient_id = await self.rel_repo.get_partner_id(message.author.id)
        if not recipient_id:
            return  # only bridges DMs between linked partners

        recipient = await resolve_user(self.bot, recipient_id)
        if recipient is None:
            return
        await self._deliver(message.author, recipient, content, message.attachments)

    async def _deliver(
        self,
        speaker: discord.abc.User,
        target: discord.abc.User,
        text: str,
        attachments: list[discord.Attachment],
    ) -> None:
        prefix = f"**{speaker.display_name}:** "
        try:
            if attachments:
                files = [await a.to_file() for a in attachments[:MAX_RELAY_FILES]]
                sent = await safe_dm(target, content=(prefix + text) if text else prefix.rstrip(": "), files=files)
            elif text and MEDIA_LINK_RE.search(text):
                sent = await safe_dm(target, content=prefix + text)
            else:
                embed = discord.Embed(description=text, color=0xFF6FA5)
                embed.set_author(name=speaker.display_name, icon_url=speaker.display_avatar.url)
                sent = await safe_dm(target, embed=embed)
        except (discord.NotFound, discord.HTTPException):
            logger.warning("could not read attachment while relaying a DM", exc_info=True)
            return
        if sent is None:
            logger.info("could not DM %s — DMs closed", target.id)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(DMLinkCog(bot))
