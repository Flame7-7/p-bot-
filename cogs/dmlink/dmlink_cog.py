from __future__ import annotations

import asyncio
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
# Tenor / Giphy "page" links (as pasted by Discord's GIF picker) only turn into a playable gif
# once Discord has resolved them, so we read the resolved embed instead of relaying the link.
GIF_PAGE_RE = re.compile(
    r"https?://(?:www\.)?(?:tenor\.com|giphy\.com|media\.giphy\.com|media\.tenor\.com)/\S+",
    re.IGNORECASE,
)
DIRECT_IMAGE_RE = re.compile(r"https?://\S+\.(?:gif|png|jpe?g|webp)(?:\?\S*)?$", re.IGNORECASE)
EMBED_RESOLVE_TRIES = 4
EMBED_RESOLVE_DELAY = 0.75  # seconds between re-fetches while Discord builds the embed
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
        gif_url = await self._resolve_gif(message, content)
        sent = await self._deliver(
            message.author, recipient, content, message.attachments, reference, gif_url=gif_url
        )
        if sent is not None:
            try:
                await self.links.add(message.channel.id, message.id, sent.channel.id, sent.id)
            except Exception:
                logger.exception("could not record DM relay link")  # replying to it just won't thread

    async def _resolve_gif(self, message: discord.Message, content: str) -> str | None:
        """Direct, embeddable image URL for a gif/image link in ``content`` (or ``None``).

        Discord's GIF picker sends a tenor/giphy page link. Relayed as text it shows up as a
        bare link, so we pull the real gif URL out of the embed Discord generated for it.
        """
        if not content or message.attachments:
            return None
        if DIRECT_IMAGE_RE.fullmatch(content):
            return content
        if not GIF_PAGE_RE.search(content):
            return None

        current = message
        for attempt in range(EMBED_RESOLVE_TRIES):
            url = self._gif_from_embeds(current.embeds)
            if url:
                return url
            if attempt == EMBED_RESOLVE_TRIES - 1:
                break
            await asyncio.sleep(EMBED_RESOLVE_DELAY)  # embeds are attached a moment after the message
            try:
                current = await message.channel.fetch_message(message.id)
            except (discord.NotFound, discord.HTTPException):
                break
        return None

    @staticmethod
    def _gif_from_embeds(embeds: list[discord.Embed]) -> str | None:
        for e in embeds:
            if e.type not in ("gifv", "image"):
                continue
            # gifv embeds expose the animated gif as the thumbnail; plain images as ``image``/url
            for media in (e.thumbnail, e.image):
                if media and media.url:
                    return media.url
            if e.type == "image" and e.url:
                return e.url
        return None

    # ---------------- reactions ----------------

    @commands.Cog.listener("on_raw_reaction_add")
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent) -> None:
        await self._mirror_reaction(payload, add=True)

    @commands.Cog.listener("on_raw_reaction_remove")
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent) -> None:
        await self._mirror_reaction(payload, add=False)

    async def _mirror_reaction(self, payload: discord.RawReactionActionEvent, add: bool) -> None:
        """Carry a reaction over to the matching message in the partner's DM.

        Reacting to your own message -> reaction on its copy in your partner's DM.
        Reacting to the copy of your partner's message -> reaction on their original.
        The bot places the reaction (Discord offers no way to react as someone else).
        """
        if payload.guild_id is not None or payload.user_id == self.bot.user.id:
            return
        try:
            link = await self.links.find_by_source(payload.message_id)
            if link is not None:
                channel_id, message_id = link.dst_channel_id, link.dst_message_id
            else:
                link = await self.links.find_by_copy(payload.message_id)
                if link is None:
                    return
                channel_id, message_id = link.src_channel_id, link.src_message_id

            channel = self.bot.get_partial_messageable(channel_id, type=discord.ChannelType.private)
            target = channel.get_partial_message(message_id)
            if add:
                await target.add_reaction(payload.emoji)
            else:
                await target.remove_reaction(payload.emoji, self.bot.user)
        except (discord.NotFound, discord.Forbidden):
            return  # message gone, DMs closed, or an emoji the bot cannot use
        except discord.HTTPException:
            logger.warning("could not mirror DM reaction", exc_info=True)
        except Exception:
            logger.exception("could not mirror DM reaction")

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
        gif_url: str | None = None,
    ) -> discord.Message | None:
        prefix = f"**{speaker.display_name}:** "

        async def build() -> dict:
            """Fresh kwargs for every attempt (uploaded files can only be sent once)."""
            if attachments:
                files = [await a.to_file() for a in attachments[:MAX_RELAY_FILES]]
                return {"content": (prefix + text) if text else prefix.rstrip(": "), "files": files}
            if gif_url:
                # Show the gif itself (no link text); keep any words that came with it.
                caption = re.sub(r"\s+", " ", text.replace(gif_url, "")).strip()
                caption = re.sub(r"\s+", " ", GIF_PAGE_RE.sub("", caption)).strip()
                embed = discord.Embed(description=caption or None, color=0xFF6FA5)
                embed.set_author(name=speaker.display_name, icon_url=speaker.display_avatar.url)
                embed.set_image(url=gif_url)
                return {"embed": embed}
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
