from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from services.action_registry import get_by_category
from views.embeds import PaginatedView

CATEGORY_INFO = {
    "affection": ("💕 Affection", 0xFF85A1),
    "playful":   ("😄 Playful",   0xFFD166),
    "emotional": ("💭 Emotional", 0xA8DADC),
    "social":    ("🤝 Social",    0xB5EAD7),
}


class HelpCog(commands.Cog, name="Help"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="help", description="View all bot commands")
    async def help(self, interaction: discord.Interaction) -> None:
        pages: list[discord.Embed] = []

        # Page 1: Overview
        overview = discord.Embed(
            title="🌸 Roleplay Bot",
            description=(
                "A social roleplay bot with 32 commands, relationships, "
                "achievements, leveling, and leaderboards!\n\n"
                "Use the buttons below to browse."
            ),
            color=0x7289DA,
        )
        overview.add_field(
            name="⚡ Quick Start",
            value="`/hug @user` · `/profile` · `/propose @user` · `/top`",
            inline=False,
        )
        overview.add_field(
            name="📋 Features",
            value=(
                "• 32 Roleplay commands with GIFs\n"
                "• Relationship system\n"
                "• Achievements & leveling\n"
                "• Daily rewards + streaks\n"
                "• Leaderboards"
            ),
            inline=False,
        )
        overview.set_footer(text="Page 1/6")
        pages.append(overview)

        # Pages 2-5: One per category
        for idx, (cat_key, (cat_label, color)) in enumerate(CATEGORY_INFO.items(), start=2):
            actions = get_by_category(cat_key)
            embed = discord.Embed(title=f"{cat_label} Commands", color=color)
            for action in actions:
                note = " *(target optional)*" if action.self_targetable else ""
                embed.add_field(
                    name=f"/{action.name}{note}",
                    value=(
                        f"{action.description}\n"
                        f"💕 `+{action.affection_gain}` · ✨ `+{action.xp_gain} XP` · "
                        f"⏱️ `{action.cooldown_seconds}s`"
                    ),
                    inline=False,
                )
            embed.set_footer(text=f"Page {idx}/6")
            pages.append(embed)

        # Page 6: Utility commands
        other = discord.Embed(title="🛠️ Other Commands", color=0x7289DA)
        other.add_field(name="👤 Profile", value="`/profile` `/setbio` `/stats`", inline=False)
        other.add_field(name="💑 Relationships", value="`/propose` `/partner` `/breakup` `/anniversary`", inline=False)
        other.add_field(name="🏆 Achievements", value="`/achievements`", inline=False)
        other.add_field(name="📊 Leaderboard", value="`/top affection|level|interactions`", inline=False)
        other.add_field(name="🎁 Economy", value="`/daily`", inline=False)
        other.add_field(name="⚙️ Settings", value="`/settings`", inline=False)
        other.set_footer(text="Page 6/6")
        pages.append(other)

        await interaction.response.send_message(
            embed=pages[0], view=PaginatedView(pages), ephemeral=True
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(HelpCog(bot))
