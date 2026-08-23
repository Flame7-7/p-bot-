from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from repositories.roleplay_profile_repository import RoleplayProfileRepository, VALID_GENDERS
from utils.cooldowns import check_cooldown, set_cooldown
from utils.logging import get_logger

logger = get_logger(__name__)

_repo = RoleplayProfileRepository()

# How long a user must wait between role changes, so the gender-select /
# consent buttons can't be spam-clicked. Reuses utils/cooldowns.py rather
# than rolling a second cooldown mechanism -- see that module for why an
# in-memory dict is fine here (it's swept periodically by tasks_cog.py).
_ROLE_CHANGE_COOLDOWN_SECONDS = 10
_ROLE_CHANGE_COOLDOWN_KEY = "consent_role_change"

_GENDER_LABELS = {"male": "Male", "female": "Female", "non-binary": "Non-Binary"}


class GenderSelect(discord.ui.View):
    def __init__(self, user_id: int) -> None:
        super().__init__(timeout=180)
        self.user_id = user_id

    @discord.ui.button(label="Male", style=discord.ButtonStyle.blurple, emoji="👨")
    async def male_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self._select(interaction, "male")

    @discord.ui.button(label="Female", style=discord.ButtonStyle.danger, emoji="👩")
    async def female_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self._select(interaction, "female")

    @discord.ui.button(label="Non-Binary", style=discord.ButtonStyle.grey, emoji="⚧️")
    async def nb_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self._select(interaction, "non-binary")

    async def _select(self, interaction: discord.Interaction, gender: str) -> None:
        remaining = check_cooldown(self.user_id, _ROLE_CHANGE_COOLDOWN_KEY)
        if remaining > 0:
            await interaction.response.send_message(
                f"⏳ You're changing this too fast. Try again in **{remaining}s**.",
                ephemeral=True,
            )
            return
        set_cooldown(self.user_id, _ROLE_CHANGE_COOLDOWN_KEY, _ROLE_CHANGE_COOLDOWN_SECONDS)

        await _repo.set_gender(self.user_id, gender)

        embed = discord.Embed(
            title="✅ Role Updated",
            description=f"Your role is now set to **{_GENDER_LABELS[gender]}**.",
            color=discord.Color.green(),
        )
        embed.add_field(
            name="Next Step",
            value="Please confirm the Community Guidelines below to finish setup.",
        )
        await interaction.response.edit_message(embed=embed, view=ConsentView(self.user_id))


class ConsentView(discord.ui.View):
    def __init__(self, user_id: int) -> None:
        super().__init__(timeout=180)
        self.user_id = user_id

    @discord.ui.button(label="I Agree", style=discord.ButtonStyle.green, emoji="✅")
    async def agree_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await _repo.set_consent(self.user_id, True)
        embed = discord.Embed(
            title="🔓 Setup Complete",
            description="Your role and consent are saved. This is stored in the database, "
                        "so it will still be here after the bot restarts.",
            color=discord.Color.gold(),
        )
        await interaction.response.edit_message(embed=embed, view=None)

    @discord.ui.button(label="Decline", style=discord.ButtonStyle.red, emoji="❌")
    async def decline_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await _repo.set_consent(self.user_id, False)
        embed = discord.Embed(
            title="🚫 Setup Not Completed",
            description="You must agree to continue. Run `/consent` again whenever you're ready.",
            color=discord.Color.red(),
        )
        await interaction.response.edit_message(embed=embed, view=None)


class StatusView(discord.ui.View):
    """Shown when a user runs /consent and already has a saved profile --
    lets them change role or reset instead of re-running the whole flow
    blind."""

    def __init__(self, user_id: int) -> None:
        super().__init__(timeout=180)
        self.user_id = user_id

    @discord.ui.button(label="Change Role", style=discord.ButtonStyle.primary, emoji="🔄")
    async def change_role(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        embed = discord.Embed(
            title="Select Your Role",
            description="Choose the role you'd like to use in roleplay commands.",
            color=discord.Color.blurple(),
        )
        await interaction.response.edit_message(embed=embed, view=GenderSelect(self.user_id))

    @discord.ui.button(label="Reset", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def reset(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await _repo.reset(self.user_id)
        embed = discord.Embed(
            title="🗑️ Configuration Reset",
            description="Your role and consent have been cleared. Run `/consent` to set up again.",
            color=discord.Color.orange(),
        )
        await interaction.response.edit_message(embed=embed, view=None)


class VerificationCog(commands.Cog, name="Verification"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.repo = _repo

    async def get_user_profile(self, user_id: int):
        return await self.repo.get(user_id)

    async def is_verified(self, user_id: int) -> bool:
        return await self.repo.is_verified(user_id)

    async def get_gender_text(
        self, user_id: int, male_text: str, female_text: str, neutral_text: str = "they"
    ) -> str:
        """Returns text based on the user's selected role. Kept for any
        existing callers of the old verification.py API; roleplay_service's
        pronoun substitution uses services/action_registry.PRONOUNS
        directly instead, since it needs subject/object/possessive forms.
        """
        profile = await self.repo.get(user_id)
        if not profile or not profile.gender:
            return neutral_text
        if profile.gender == "male":
            return male_text
        if profile.gender == "female":
            return female_text
        return neutral_text

    async def _start_flow(self, interaction: discord.Interaction) -> None:
        profile = await self.repo.get(interaction.user.id)
        if profile and profile.consent_given and profile.gender:
            embed = discord.Embed(
                title="✅ Already Set Up",
                description=f"Role: **{_GENDER_LABELS.get(profile.gender, profile.gender)}**\n"
                            f"Consent: **Given**",
                color=discord.Color.green(),
            )
            embed.set_footer(text="Use the buttons below to change your role or reset.")
            await interaction.response.send_message(embed=embed, view=StatusView(interaction.user.id))
            return

        embed = discord.Embed(
            title="⚠️ Setup Required",
            description="Select the role you'd like to use in roleplay commands, then confirm "
                        "the Community Guidelines.",
            color=discord.Color.orange(),
        )
        await interaction.response.send_message(embed=embed, view=GenderSelect(interaction.user.id))

    @app_commands.command(name="consent", description="Set up or review your roleplay role/consent configuration.")
    async def consent(self, interaction: discord.Interaction) -> None:
        await self._start_flow(interaction)

    @app_commands.command(name="verify", description="Alias for /consent -- set up your roleplay role/consent.")
    async def verify(self, interaction: discord.Interaction) -> None:
        await self._start_flow(interaction)

    @app_commands.command(name="consentstatus", description="Check your current role/consent status.")
    async def consent_status(self, interaction: discord.Interaction) -> None:
        profile = await self.repo.get(interaction.user.id)

        if not profile:
            status, gender, consent = "❌ Not Started", "Not Set", "Not Given"
        else:
            verified = await self.repo.is_verified(interaction.user.id)
            status = "✅ Verified" if verified else "⚠️ Incomplete"
            gender = _GENDER_LABELS.get(profile.gender, "Not Set")
            consent = "✅ Given" if profile.consent_given else "❌ Pending"

        embed = discord.Embed(title="Roleplay Configuration", color=discord.Color.blurple())
        embed.add_field(name="Status", value=status, inline=False)
        embed.add_field(name="Role", value=gender, inline=True)
        embed.add_field(name="Consent", value=consent, inline=True)
        if status != "✅ Verified":
            embed.set_footer(text="Run /consent to complete setup.")
        await interaction.response.send_message(embed=embed)


def requires_verification():
    """Gate for any command that should require a completed /consent flow.
    Not currently applied to any of the affection/playful/emotional/social
    roleplay commands (they never required this), but is here, working end
    to end against the database, for whichever commands should use it.
    """
    async def predicate(interaction: discord.Interaction) -> bool:
        cog = interaction.client.get_cog("Verification")
        if not cog:
            raise app_commands.CommandError("Verification system not loaded.")

        if not await cog.is_verified(interaction.user.id):
            embed = discord.Embed(
                title="🔒 Command Locked",
                description="You must complete setup before using this command.\nUse `/consent` to start.",
                color=discord.Color.red(),
            )
            if interaction.response.is_done():
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
        return True
    return app_commands.check(predicate)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(VerificationCog(bot))
