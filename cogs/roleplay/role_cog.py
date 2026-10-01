from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from repositories.roleplay_profile_repository import RoleplayProfileRepository
from utils.logging import get_logger

logger = get_logger(__name__)

_GENDER_LABELS = {"male": "Male", "female": "Female", "non-binary": "Non-Binary"}


class RoleSelect(discord.ui.View):
    """One-click pronoun picker. No consent step, no gating -- the role only
    changes the pronouns used in roleplay messages."""

    def __init__(self, repo: RoleplayProfileRepository, user_id: int) -> None:
        super().__init__(timeout=180)
        self.repo = repo
        self.user_id = user_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This menu isn't yours.", ephemeral=True)
            return False
        return True

    async def _select(self, interaction: discord.Interaction, gender: str) -> None:
        await self.repo.set_gender(self.user_id, gender)
        embed = discord.Embed(
            title="✅ Role Updated",
            description=f"Your role is now **{_GENDER_LABELS[gender]}**.",
            color=discord.Color.green(),
        )
        await interaction.response.edit_message(embed=embed, view=None)

    @discord.ui.button(label="Male", style=discord.ButtonStyle.blurple, emoji="👨")
    async def male_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self._select(interaction, "male")

    @discord.ui.button(label="Female", style=discord.ButtonStyle.danger, emoji="👩")
    async def female_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self._select(interaction, "female")

    @discord.ui.button(label="Non-Binary", style=discord.ButtonStyle.grey, emoji="⚧️")
    async def nb_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self._select(interaction, "non-binary")


class RoleCog(commands.Cog, name="Role"):
    help_category = ("🎭", "Roleplay")

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.repo = RoleplayProfileRepository()

    @app_commands.command(name="role", description="Pick the pronouns used in your roleplay messages.")
    async def role(self, interaction: discord.Interaction) -> None:
        profile = await self.repo.get(interaction.user.id)
        current = _GENDER_LABELS.get(profile.gender, "Not set") if profile and profile.gender else "Not set"
        embed = discord.Embed(
            title="Select Your Role",
            description=f"Current: **{current}**\nChoose the pronouns to use in roleplay commands.",
            color=discord.Color.blurple(),
        )
        await interaction.response.send_message(
            embed=embed, view=RoleSelect(self.repo, interaction.user.id), ephemeral=True
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(RoleCog(bot))
