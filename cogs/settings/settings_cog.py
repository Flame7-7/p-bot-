from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy import select

from database.connection import get_session
from models.models import UserSettings


class SettingsView(discord.ui.View):
    def __init__(self, user_id: int, allow: bool, leaderboard: bool) -> None:
        super().__init__(timeout=120)
        self.user_id = user_id
        self.allow = allow
        self.leaderboard = leaderboard
        self._refresh()

    def _refresh(self) -> None:
        self.btn_interactions.label = f"{'✅' if self.allow else '❌'} Interactions: {'ON' if self.allow else 'OFF'}"
        self.btn_interactions.style = discord.ButtonStyle.success if self.allow else discord.ButtonStyle.danger
        self.btn_lb.label = f"{'✅' if self.leaderboard else '❌'} Leaderboard: {'Visible' if self.leaderboard else 'Hidden'}"
        self.btn_lb.style = discord.ButtonStyle.success if self.leaderboard else discord.ButtonStyle.secondary

    def build_embed(self) -> discord.Embed:
        embed = discord.Embed(title="⚙️ Your Settings", color=0x7289DA)
        embed.add_field(
            name="Interactions",
            value="✅ Others can interact with you." if self.allow else "❌ Others cannot interact with you.",
            inline=False,
        )
        embed.add_field(
            name="Leaderboard",
            value="✅ You appear on leaderboards." if self.leaderboard else "❌ Hidden from leaderboards.",
            inline=False,
        )
        return embed

    @discord.ui.button(row=0)
    async def btn_interactions(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("These aren't your settings!", ephemeral=True)
            return
        self.allow = not self.allow
        async with get_session() as session:
            r = await session.execute(select(UserSettings).where(UserSettings.user_id == self.user_id))
            s = r.scalar_one_or_none()
            if not s:
                s = UserSettings(user_id=self.user_id)
                session.add(s)
            s.allow_interactions = self.allow
        self._refresh()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(row=0)
    async def btn_lb(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("These aren't your settings!", ephemeral=True)
            return
        self.leaderboard = not self.leaderboard
        async with get_session() as session:
            r = await session.execute(select(UserSettings).where(UserSettings.user_id == self.user_id))
            s = r.scalar_one_or_none()
            if not s:
                s = UserSettings(user_id=self.user_id)
                session.add(s)
            s.show_in_leaderboard = self.leaderboard
        self._refresh()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(label="🔒 Close", style=discord.ButtonStyle.secondary, row=1)
    async def btn_close(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("These aren't your settings!", ephemeral=True)
            return
        for c in self.children:
            c.disabled = True  # type: ignore[attr-defined]
        await interaction.response.edit_message(view=self)
        self.stop()

    async def on_timeout(self) -> None:
        for c in self.children:
            c.disabled = True  # type: ignore[attr-defined]


class SettingsCog(commands.Cog, name="Settings"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="settings", description="Open your settings panel")
    async def settings(self, interaction: discord.Interaction) -> None:
        async with get_session() as session:
            r = await session.execute(
                select(UserSettings).where(UserSettings.user_id == interaction.user.id)
            )
            s = r.scalar_one_or_none()
        allow = s.allow_interactions if s else True
        lb = s.show_in_leaderboard if s else True
        view = SettingsView(interaction.user.id, allow, lb)
        await interaction.response.send_message(embed=view.build_embed(), view=view, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(SettingsCog(bot))
