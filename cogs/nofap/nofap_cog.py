from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Button, button

from models.models import NoFapStreak
from repositories.nofap_repository import NoFapRepository, current_streak_days
from views.embeds import DiscordUIV2View
from utils.logging import get_logger

logger = get_logger(__name__)

NOFAP_COLOR = 0xE67E22


def _fmt_date(dt) -> str:
    return dt.strftime("%B %d, %Y") if dt else "Never"


def _encouragement(days: int) -> str:
    if days == 0:
        return "Every streak starts with day one. You've got this! 🌱"
    if days < 7:
        return "Keep going! 💪"
    if days < 30:
        return "Solid momentum -- don't stop now! 🔥"
    if days < 90:
        return "That's genuinely impressive. Stay strong! 🏆"
    return "Incredible discipline. You're an inspiration! 🌟"


def build_status_embed(user: discord.abc.User, streak: NoFapStreak | None) -> discord.Embed:
    days = current_streak_days(streak)
    embed = discord.Embed(title="🔥 No-Fap Streak", color=NOFAP_COLOR)
    embed.set_thumbnail(url=str(user.display_avatar.url))

    if streak is None or streak.started_at is None:
        embed.description = (
            "You haven't started tracking yet.\nRun `/nofap start` to begin your streak!"
        )
        return embed

    embed.add_field(name="Current streak", value=f"`{days}` day{'s' if days != 1 else ''}", inline=True)
    embed.add_field(name="Started", value=_fmt_date(streak.started_at), inline=True)
    embed.add_field(name="Last reset", value=_fmt_date(streak.last_reset_at), inline=True)
    embed.set_footer(text=_encouragement(days))
    embed.timestamp = discord.utils.utcnow()
    return embed


def build_stats_embed(user: discord.abc.User, streak: NoFapStreak | None) -> discord.Embed:
    days = current_streak_days(streak)
    embed = discord.Embed(title="📊 No-Fap Stats", color=NOFAP_COLOR)
    embed.set_thumbnail(url=str(user.display_avatar.url))

    if streak is None or streak.started_at is None:
        embed.description = "No stats yet -- run `/nofap start` first."
        return embed

    best = max(streak.best_streak_days, days)
    embed.add_field(name="Current streak", value=f"`{days}` day{'s' if days != 1 else ''}", inline=True)
    embed.add_field(name="Best streak", value=f"`{best}` day{'s' if best != 1 else ''}", inline=True)
    embed.add_field(name="Total resets", value=f"`{streak.reset_count}`", inline=True)
    embed.add_field(name="Tracking since", value=_fmt_date(streak.created_at), inline=True)
    embed.add_field(name="Last reset", value=_fmt_date(streak.last_reset_at), inline=True)
    embed.timestamp = discord.utils.utcnow()
    return embed


class ResetConfirmView(DiscordUIV2View):
    """Confirm before wiping out an active streak -- resets are
    significant/irreversible, unlike most other buttons in the bot."""

    def __init__(self, user_id: int, repo: NoFapRepository) -> None:
        super().__init__(timeout=60)
        self.user_id = user_id
        self.repo = repo

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "This isn't your confirmation to answer.", ephemeral=True
            )
            return False
        return True

    @button(label="Confirm relapse", style=discord.ButtonStyle.danger, custom_id="nofap_confirm")
    async def confirm(self, interaction: discord.Interaction, button: Button) -> None:
        streak = await self.repo.reset(self.user_id)
        self.stop()
        embed = build_status_embed(interaction.user, streak)
        embed.title = "🔁 Streak Reset"
        embed.description = "No worries -- tomorrow's a fresh start. Your new streak begins now."
        await interaction.response.edit_message(embed=embed, view=None)

    @button(label="Cancel", style=discord.ButtonStyle.secondary, custom_id="nofap_cancel")
    async def cancel(self, interaction: discord.Interaction, button: Button) -> None:
        self.stop()
        await interaction.response.edit_message(
            content="Cancelled -- your streak wasn't touched.", embed=None, view=None
        )


class NoFapCog(commands.Cog, name="No-Fap"):
    """Personal streak tracking. Fully separate from the roleplay/consent
    system -- purely a self-improvement tool."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.repo = NoFapRepository()

    nofap_group = app_commands.Group(name="nofap", description="Track your no-fap streak")

    @nofap_group.command(name="start", description="Start tracking your no-fap streak")
    async def start(self, interaction: discord.Interaction) -> None:
        streak, already_active = await self.repo.start(interaction.user.id)
        if already_active:
            days = current_streak_days(streak)
            await interaction.response.send_message(
                f"You're already on a streak (`{days}` day{'s' if days != 1 else ''} so far). "
                f"Use `/nofap status` to check it, or `/nofap reset` if you relapsed.",
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title="🌱 Streak Started",
            description="Your no-fap streak has begun. Check in anytime with `/nofap status`.",
            color=NOFAP_COLOR,
        )
        embed.timestamp = discord.utils.utcnow()
        await interaction.response.send_message(embed=embed)

    @nofap_group.command(name="status", description="View your current no-fap streak")
    async def status(self, interaction: discord.Interaction) -> None:
        streak = await self.repo.get(interaction.user.id)
        await interaction.response.send_message(embed=build_status_embed(interaction.user, streak))

    @nofap_group.command(name="stats", description="View your detailed no-fap statistics")
    async def stats(self, interaction: discord.Interaction) -> None:
        streak = await self.repo.get(interaction.user.id)
        await interaction.response.send_message(embed=build_stats_embed(interaction.user, streak))

    @nofap_group.command(name="reset", description="Record a relapse and start a new streak")
    async def reset(self, interaction: discord.Interaction) -> None:
        streak = await self.repo.get(interaction.user.id)
        if streak is None or streak.started_at is None:
            await interaction.response.send_message(
                "You don't have an active streak yet -- run `/nofap start` first.",
                ephemeral=True,
            )
            return

        days = current_streak_days(streak)
        await interaction.response.send_message(
            f"Reset your `{days}`-day streak? This can't be undone.",
            view=ResetConfirmView(interaction.user.id, self.repo),
            ephemeral=True,
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(NoFapCog(bot))
