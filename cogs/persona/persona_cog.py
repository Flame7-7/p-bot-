from __future__ import annotations

import time
from collections import defaultdict, deque

import discord
from discord import app_commands
from discord.ext import commands

from repositories.persona_repository import PersonaChannelRepository, PersonaRepository
from services.persona_service import generate_persona_reply
from utils.config import get_config
from utils.interactions import respond
from utils.logging import get_logger

logger = get_logger(__name__)

HISTORY_LEN = 8
EMBED_COLOR = 0xFF6FA5
REQUIRED_PERMS = ("view_channel", "send_messages", "embed_links", "read_message_history")


class PersonaModal(discord.ui.Modal, title="Set your persona"):
    text: discord.ui.TextInput = discord.ui.TextInput(
        label="How do you talk? Who are you?",
        style=discord.TextStyle.paragraph,
        placeholder="e.g. casual, lowercase, lots of 'lol', calls her babe...",
        max_length=1500,
        required=True,
    )

    def __init__(self, repo: PersonaRepository, current: str | None) -> None:
        super().__init__()
        self.repo = repo
        if current:
            self.text.default = current

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await self.repo.set_persona_text(interaction.user.id, str(self.text.value))
        await respond(interaction, "✅ Persona saved.", ephemeral=True)

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        logger.error("persona modal failed", exc_info=error)
        await respond(interaction, "Couldn't save that — please try again.", ephemeral=True)


def _missing_perms(channel: discord.abc.GuildChannel, me: discord.Member) -> list[str]:
    perms = channel.permissions_for(me)
    return [p.replace("_", " ") for p in REQUIRED_PERMS if not getattr(perms, p)]


class PersonaCog(commands.Cog, name="Persona"):
    """AI replies in someone's voice, inside ONE configured server channel.

    Persona never runs in DMs. A server admin picks the channel with
    `/persona setup`; when someone there mentions (or replies to) a member who
    is away with a persona set, the bot answers in that member's voice.
    """

    help_category = ("💬", "Persona")

    persona_group = app_commands.Group(name="persona", description="AI persona replies in your server's persona channel")
    afk_group = app_commands.Group(name="afk", description="Let your persona answer for you while you're away")

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.persona_repo = PersonaRepository()
        self.channel_repo = PersonaChannelRepository()
        self._channels: dict[int, int] = {}  # guild_id -> persona channel_id (enabled only)
        self._history: dict[tuple[int, int, int], deque] = defaultdict(lambda: deque(maxlen=HISTORY_LEN))
        self._last_reply: dict[int, float] = {}

    async def cog_load(self) -> None:
        self._channels = await self.channel_repo.all_enabled()

    # ── setup ────────────────────────────────────────────────────────────────

    async def _can_manage(self, interaction: discord.Interaction) -> bool:
        if interaction.guild is None:
            await respond(interaction, "Persona now lives in a server channel — run this in your server.", ephemeral=True)
            return False
        if interaction.permissions.manage_guild or await self.bot.is_owner(interaction.user):
            return True
        await respond(interaction, "You need the **Manage Server** permission for that.", ephemeral=True)
        return False

    @persona_group.command(name="setup", description="Choose the channel where persona replies happen")
    @app_commands.describe(channel="The only channel where the bot will reply in someone's voice")
    @app_commands.guild_only()
    async def persona_setup(self, interaction: discord.Interaction, channel: discord.TextChannel) -> None:
        if not await self._can_manage(interaction):
            return
        missing = _missing_perms(channel, interaction.guild.me)  # type: ignore[union-attr]
        if missing:
            await respond(
                interaction,
                f"I can't use {channel.mention} yet — I'm missing: **{', '.join(missing)}**. "
                "Fix the channel permissions and run this again.",
                ephemeral=True,
            )
            return

        await self.channel_repo.set(interaction.guild_id, channel.id, interaction.user.id)  # type: ignore[arg-type]
        self._channels[interaction.guild_id] = channel.id  # type: ignore[index]

        embed = discord.Embed(
            title="💬 Persona channel set",
            description=(
                f"Persona replies now happen **only** in {channel.mention}.\n\n"
                "**How it works**\n"
                "1. Everyone sets up with `/persona set` (how they talk).\n"
                "2. When someone is away, `/afk on` (or auto-AFK when their status goes offline).\n"
                f"3. In {channel.mention}, mention that person or reply to their message — "
                "I answer in their voice, tagged 🤖 unless they hide it.\n\n"
                "Nothing happens in other channels or in DMs."
            ),
            color=EMBED_COLOR,
        )
        if not get_config().groq_api_key:
            embed.set_footer(text="⚠️ GROQ_API_KEY isn't configured, so replies are paused until it is.")
        await respond(interaction, embed=embed)

    @persona_group.command(name="disable", description="Turn persona replies off for this server")
    @app_commands.guild_only()
    async def persona_disable(self, interaction: discord.Interaction) -> None:
        if not await self._can_manage(interaction):
            return
        changed = await self.channel_repo.disable(interaction.guild_id)  # type: ignore[arg-type]
        self._channels.pop(interaction.guild_id, None)  # type: ignore[arg-type]
        await respond(
            interaction,
            "Persona replies are **off** for this server." if changed else "Persona wasn't enabled here.",
            ephemeral=True,
        )

    @persona_group.command(name="status", description="See where persona replies happen in this server")
    @app_commands.guild_only()
    async def persona_status(self, interaction: discord.Interaction) -> None:
        channel_id = self._channels.get(interaction.guild_id)  # type: ignore[arg-type]
        channel = interaction.guild.get_channel(channel_id) if channel_id and interaction.guild else None
        if channel is None:
            text = "No persona channel is configured. An admin can run `/persona setup`."
            if channel_id:
                text = "The configured persona channel was deleted. An admin should run `/persona setup` again."
        else:
            text = f"Persona replies happen in {channel.mention}."
            missing = _missing_perms(channel, interaction.guild.me)  # type: ignore[union-attr]
            if missing:
                text += f"\n⚠️ I'm missing permissions there: **{', '.join(missing)}**."
        await respond(interaction, text, ephemeral=True)

    # ── per-user persona ─────────────────────────────────────────────────────

    @persona_group.command(name="set", description="Describe how you talk so the bot can reply as you")
    async def persona_set(self, interaction: discord.Interaction) -> None:
        current = await self.persona_repo.get(interaction.user.id)
        await interaction.response.send_modal(PersonaModal(self.persona_repo, current.persona_text if current else None))

    @persona_group.command(name="view", description="See your saved persona")
    async def persona_view(self, interaction: discord.Interaction) -> None:
        p = await self.persona_repo.get(interaction.user.id)
        if not p or not p.persona_text:
            await respond(interaction, "You haven't set a persona yet — use `/persona set`.", ephemeral=True)
            return
        await respond(interaction, f"**Your saved persona:**\n{p.persona_text}", ephemeral=True)

    @afk_group.command(name="on", description="Let your persona answer for you in the persona channel")
    async def afk_on(self, interaction: discord.Interaction) -> None:
        if not get_config().groq_api_key:
            await respond(
                interaction,
                "⚠️ No `GROQ_API_KEY` is configured on this bot, so persona replies can't run yet.",
                ephemeral=True,
            )
            return
        p = await self.persona_repo.get(interaction.user.id)
        if not p or not p.persona_text:
            await respond(interaction, "Set a persona first with `/persona set`.", ephemeral=True)
            return
        await self.persona_repo.set_afk(interaction.user.id, True)
        await respond(
            interaction,
            "🤖 AFK mode is **on** — if someone mentions you or replies to you in a server's persona "
            "channel, I'll answer in your voice until you run `/afk off`.",
            ephemeral=True,
        )

    @afk_group.command(name="off", description="Stop persona replies")
    async def afk_off(self, interaction: discord.Interaction) -> None:
        await self.persona_repo.set_afk(interaction.user.id, False)
        await respond(interaction, "AFK mode is **off** — you're back to answering yourself.", ephemeral=True)

    @afk_group.command(name="label", description="Show or hide the 🤖 tag on persona replies")
    @app_commands.describe(visible="Whether persona replies show a small 'auto-reply' footer")
    async def afk_label(self, interaction: discord.Interaction, visible: bool) -> None:
        await self.persona_repo.set_label(interaction.user.id, visible)
        await respond(interaction, f"Auto-reply tag will now be **{'shown' if visible else 'hidden'}**.", ephemeral=True)

    @afk_group.command(name="auto", description="Auto-enable AFK when your Discord status goes offline/invisible")
    @app_commands.describe(enabled="On by default — turn off if you'd rather flip /afk manually")
    async def afk_auto(self, interaction: discord.Interaction, enabled: bool) -> None:
        await self.persona_repo.set_auto_afk(interaction.user.id, enabled)
        await respond(interaction, f"Auto-AFK is now **{'on' if enabled else 'off'}**.", ephemeral=True)

    # ── the channel listener ─────────────────────────────────────────────────

    @commands.Cog.listener("on_message")
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or message.guild is None:
            return  # DMs and bots never trigger persona
        if self._channels.get(message.guild.id) != message.channel.id:
            return
        if not message.content.strip():
            return

        targets = await self._candidate_targets(message)
        if not targets:
            return

        profiles = await self.persona_repo.get_many([m.id for m in targets])
        owner = next(
            (m for m in targets if (p := profiles.get(m.id)) and p.afk_enabled and p.persona_text),
            None,
        )
        if owner is None:
            return

        me = message.guild.me
        if me is None or _missing_perms(message.channel, me):  # type: ignore[arg-type]
            logger.warning("persona channel %s in guild %s lacks permissions", message.channel.id, message.guild.id)
            return

        now = time.monotonic()
        if now - self._last_reply.get(message.author.id, 0.0) < get_config().persona_reply_cooldown:
            return
        self._last_reply[message.author.id] = now

        profile = profiles[owner.id]
        key = (message.channel.id, message.author.id, owner.id)
        incoming = message.clean_content[:1500]
        async with message.channel.typing():
            reply = await generate_persona_reply(
                profile.persona_text or "",
                list(self._history[key]),
                incoming,
                owner_name=owner.display_name,
                speaker_name=message.author.display_name,
            )
        if not reply:
            return

        self._history[key].append({"role": "user", "content": incoming})
        self._history[key].append({"role": "assistant", "content": reply})

        embed = discord.Embed(description=reply, color=EMBED_COLOR)
        embed.set_author(name=owner.display_name, icon_url=owner.display_avatar.url)
        if profile.label_replies:
            embed.set_footer(text=f"🤖 Auto-reply from {owner.display_name} — they're away right now")
        try:
            await message.reply(embed=embed, mention_author=False, allowed_mentions=discord.AllowedMentions.none())
        except discord.NotFound:
            pass  # the message was deleted while we were generating
        except discord.Forbidden:
            logger.warning("lost permission to reply in persona channel %s", message.channel.id)
        except discord.HTTPException:
            logger.warning("persona reply failed", exc_info=True)

    async def _candidate_targets(self, message: discord.Message) -> list[discord.Member]:
        """Members the message is addressed to: mentions first, then the replied-to author."""
        seen: dict[int, discord.Member] = {}
        for m in message.mentions:
            if isinstance(m, discord.Member) and not m.bot and m.id != message.author.id:
                seen.setdefault(m.id, m)

        ref = message.reference
        if ref and ref.message_id:
            replied = ref.resolved if isinstance(ref.resolved, discord.Message) else None
            if replied is None and ref.cached_message is None:
                try:
                    replied = await message.channel.fetch_message(ref.message_id)
                except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                    replied = None
            replied = replied or ref.cached_message
            author = replied.author if replied else None
            if isinstance(author, discord.Member) and not author.bot and author.id != message.author.id:
                seen.setdefault(author.id, author)
        return list(seen.values())

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel) -> None:
        if self._channels.get(channel.guild.id) == channel.id:
            await self.channel_repo.disable(channel.guild.id)
            self._channels.pop(channel.guild.id, None)
            logger.info("persona channel %s deleted in guild %s; persona disabled", channel.id, channel.guild.id)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(PersonaCog(bot))
