from __future__ import annotations

import re

import discord
from discord.ext import commands

from repositories.dm_relay_repository import DMRelayRepository
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
LINK_RETENTION_DAYS = 30  # replies to messages older than this are sent as plain messages


class DMLinkCog(commands.Cog, name="DM Link"):
    """Relays DMs to the bot between two linked partners (see /propose).

    Text, gifs, images and videos sent to the bot arrive in the partner's DMs.
    Replying to a message in your DM shows up as a reply in your partner's DM, pointing at
    the matching message there (see ``_reply_reference``). This is a plain relay —
    persona/AI replies never run in DMs (see cogs/persona).
    """

    help_category = ("💕", "Couple")

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.rel_repo = RelationshipRepository()
        self.links = DMRelayRepository()

    async def cog_load(self) -> None:
        try:
            await self.links.prune(older_than_days=LINK_RETENTION_DAYS)
        except Exception:
            logger.exception("could not prune old DM relay links")

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
        reference = await self._reply_reference(message)
        sent = await self._deliver(message.author, recipient, content, message.attachments, reference)
        if sent is not None:
            try:
                await self.links.add(message.channel.id, message.id, sent.channel.id, sent.id)
            except Exception:
                logger.exception("could not record DM relay link")  # replying to it just won't thread

    async def _reply_reference(self, message: discord.Message) -> discord.MessageReference | None:
        """Where, in the partner's DM, a reply should point.

        Two cases, both resolved from the stored links:
        * replying to your own earlier message -> its copy in the partner's DM;
        * replying to a copy the bot posted of the partner's message -> the partner's original.
        Anything else (a game message, an unlinked or deleted message) is sent as a normal message.
        """
        ref = message.reference
        if ref is None or ref.message_id is None:
            return None
        try:
            link = await self.links.find_by_source(ref.message_id)
            if link is not None:
                return discord.MessageReference(
                    message_id=link.dst_message_id, channel_id=link.dst_channel_id, fail_if_not_exists=False
                )
            link = await self.links.find_by_copy(ref.message_id)
            if link is not None:
                return discord.MessageReference(
                    message_id=link.src_message_id, channel_id=link.src_channel_id, fail_if_not_exists=False
                )
        except Exception:
            logger.exception("could not resolve DM reply target")
        return None

    async def _deliver(
        self,
        speaker: discord.abc.User,
        target: discord.abc.User,
        text: str,
        attachments: list[discord.Attachment],
        reference: discord.MessageReference | None = None,
    ) -> discord.Message | None:
        prefix = f"**{speaker.display_name}:** "

        async def build() -> dict:
            """Fresh kwargs for every attempt (uploaded files can only be sent once)."""
            if attachments:
                files = [await a.to_file() for a in attachments[:MAX_RELAY_FILES]]
                return {"content": (prefix + text) if text else prefix.rstrip(": "), "files": files}
            if text and MEDIA_LINK_RE.search(text):
                return {"content": prefix + text}
            embed = discord.Embed(description=text, color=0xFF6FA5)
            embed.set_author(name=speaker.display_name, icon_url=speaker.display_avatar.url)
            return {"embed": embed}

        try:
            sent = await safe_dm(target, **await build(), **({"reference": reference} if reference else {}))
            if sent is None and reference is not None:
                # The reply target may be gone; the message itself must still arrive.
                sent = await safe_dm(target, **await build())
        except (discord.NotFound, discord.HTTPException):
            logger.warning("could not read attachment while relaying a DM", exc_info=True)
            return None
        if sent is None:
            logger.info("could not DM %s — DMs closed", target.id)
        return sent


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(DMLinkCog(bot))
