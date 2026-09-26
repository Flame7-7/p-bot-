from __future__ import annotations

from collections import defaultdict, deque

import discord
from discord.ext import commands

from repositories.persona_repository import PersonaRepository
from repositories.relationship_repository import RelationshipRepository
from services.persona_service import generate_persona_reply
from utils.logging import get_logger

logger = get_logger(__name__)

HISTORY_LEN = 8  # in-memory turns of context per pair; resets on restart


class DMLinkCog(commands.Cog):
    """Bridges bot-DMs between two linked partners (see /partner, /propose).

    If either partner DMs the bot and they have an active relationship, the
    message is relayed to the other partner's DMs. If the recipient has
    turned AFK mode on (see cogs/persona), the bot generates a reply in
    their voice instead of leaving the sender hanging, and separately DMs
    the recipient a copy of what was said and what the bot answered.
    """

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.rel_repo = RelationshipRepository()
        self.persona_repo = PersonaRepository()
        self._history: dict[tuple[int, int], deque] = defaultdict(lambda: deque(maxlen=HISTORY_LEN))

    @commands.Cog.listener("on_message")
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or not isinstance(message.channel, discord.DMChannel):
            return

        sender = message.author
        recipient_id = await self.rel_repo.get_partner_id(sender.id)
        if not recipient_id:
            return  # only bridges DMs between people linked via /partner

        content = message.content.strip()
        attachments = [a.url for a in message.attachments]
        if not content and not attachments:
            return

        recipient_persona = await self.persona_repo.get(recipient_id)
        afk = bool(recipient_persona and recipient_persona.afk_enabled and recipient_persona.persona_text)

        if afk:
            recipient_user = await self._resolve(recipient_id)
            key = (sender.id, recipient_id)
            reply = await generate_persona_reply(
                recipient_persona.persona_text,
                list(self._history[key]),
                content or "[sent an attachment]",
            )
            if reply and recipient_user:
                self._history[key].append({"role": "user", "content": content or "[sent an attachment]"})
                self._history[key].append({"role": "assistant", "content": reply})
                await self._deliver(
                    speaker=recipient_user,
                    target=sender,
                    text=reply,
                    auto=True,
                    label=recipient_persona.label_replies,
                )
                await self._notify_owner(recipient_user, sender, content, attachments, reply)
                return
            # no reply generated (no API key / call failed) — fall through to a plain relay

        recipient_user = await self._resolve(recipient_id)
        if recipient_user:
            await self._deliver(speaker=sender, target=recipient_user, text=content, attachments=attachments, auto=False)

    async def _resolve(self, user_id: int) -> discord.User | None:
        user = self.bot.get_user(user_id)
        if user:
            return user
        try:
            return await self.bot.fetch_user(user_id)
        except discord.NotFound:
            return None

    async def _deliver(
        self,
        *,
        speaker: discord.abc.User,
        target: discord.abc.User,
        text: str,
        auto: bool,
        attachments: list[str] | None = None,
        label: bool = True,
    ) -> None:
        embed = discord.Embed(description=text or None, color=0xFF6FA5)
        embed.set_author(name=speaker.display_name, icon_url=speaker.display_avatar.url)
        if auto and label:
            embed.set_footer(text=f"🤖 Auto-reply from {speaker.display_name} — they're away right now")
        if attachments:
            embed.set_image(url=attachments[0])
            if len(attachments) > 1:
                embed.add_field(name="More attachments", value="\n".join(attachments[1:]))

        try:
            await target.send(embed=embed)
        except discord.Forbidden:
            logger.info("could not DM %s (%s) — DMs closed", target, target.id)

    async def _notify_owner(
        self,
        owner: discord.abc.User,
        sender: discord.abc.User,
        incoming: str,
        attachments: list[str],
        reply: str,
    ) -> None:
        """Keep the AFK partner in the loop on what was said on their behalf."""
        embed = discord.Embed(color=0x99AAB5)
        shown_incoming = incoming or ("*[attachment]*" if attachments else "*[empty]*")
        embed.add_field(name=f"💬 {sender.display_name} said", value=shown_incoming, inline=False)
        embed.add_field(name="🤖 Bot replied as you", value=reply, inline=False)
        embed.set_footer(text="Turn this off anytime with /afk off")
        try:
            await owner.send(embed=embed)
        except discord.Forbidden:
            pass


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(DMLinkCog(bot))
