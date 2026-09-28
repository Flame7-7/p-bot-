from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from repositories.persona_repository import PersonaRepository
from utils.config import get_config


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
        await interaction.response.send_message("✅ Persona saved.", ephemeral=True)


class PersonaCog(commands.Cog):
    persona_group = app_commands.Group(name="persona", description="Configure your AI auto-reply persona")
    afk_group = app_commands.Group(name="afk", description="Toggle AI auto-replies while you're away")

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.persona_repo = PersonaRepository()

    @persona_group.command(name="set", description="Describe how you talk so the bot can reply as you")
    async def persona_set(self, interaction: discord.Interaction) -> None:
        current = await self.persona_repo.get(interaction.user.id)
        await interaction.response.send_modal(
            PersonaModal(self.persona_repo, current.persona_text if current else None)
        )

    @persona_group.command(name="view", description="See your saved persona")
    async def persona_view(self, interaction: discord.Interaction) -> None:
        p = await self.persona_repo.get(interaction.user.id)
        if not p or not p.persona_text:
            await interaction.response.send_message(
                "You haven't set a persona yet — use `/persona set`.", ephemeral=True
            )
            return
        await interaction.response.send_message(f"**Your saved persona:**\n{p.persona_text}", ephemeral=True)

    @afk_group.command(name="on", description="Auto-reply to your partner in your voice while you're away")
    async def afk_on(self, interaction: discord.Interaction) -> None:
        if not get_config().groq_api_key:
            await interaction.response.send_message(
                "⚠️ No `GROQ_API_KEY` is configured on this bot, so auto-replies can't run yet. "
                "Get a free one at console.groq.com and add it to `.env`.",
                ephemeral=True,
            )
            return
        p = await self.persona_repo.get(interaction.user.id)
        if not p or not p.persona_text:
            await interaction.response.send_message(
                "Set a persona first with `/persona set`, then turn AFK mode on.", ephemeral=True
            )
            return
        await self.persona_repo.set_afk(interaction.user.id, True)
        await interaction.response.send_message(
            "🤖 AFK mode is **on** — your partner's DMs will get an auto-reply in your voice "
            "until you run `/afk off`. A little 🤖 tag shows on those replies by default "
            "(toggle it with `/afk label`).",
            ephemeral=True,
        )

    @afk_group.command(name="off", description="Turn off AI auto-replies")
    async def afk_off(self, interaction: discord.Interaction) -> None:
        await self.persona_repo.set_afk(interaction.user.id, False)
        await interaction.response.send_message(
            "AFK mode is **off** — you're back to answering yourself.", ephemeral=True
        )

    @afk_group.command(name="label", description="Show or hide the auto-reply tag on generated messages")
    @app_commands.describe(visible="Whether auto-generated replies show a small 'auto-reply' footer")
    async def afk_label(self, interaction: discord.Interaction, visible: bool) -> None:
        await self.persona_repo.set_label(interaction.user.id, visible)
        state = "shown" if visible else "hidden"
        await interaction.response.send_message(f"Auto-reply tag will now be **{state}**.", ephemeral=True)

    @afk_group.command(name="auto", description="Auto-enable AFK mode when your Discord status goes offline/invisible")
    @app_commands.describe(enabled="On by default — turn off if you'd rather flip /afk manually")
    async def afk_auto(self, interaction: discord.Interaction, enabled: bool) -> None:
        await self.persona_repo.set_auto_afk(interaction.user.id, enabled)
        await interaction.response.send_message(
            f"Auto-AFK on offline/invisible is now **{'on' if enabled else 'off'}**.", ephemeral=True
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(PersonaCog(bot))
