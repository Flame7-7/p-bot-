from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from services.action_registry import get_by_category, get_all_categories
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
                "A social roleplay bot with relationships, "
                "achievements, leveling, and leaderboards!\n\n"
                "**Browse by Category:**\n"
                "• 💕 **Affection** - Show love and care\n"
                "• 😄 **Playful** - Have fun together\n"
                "• 💭 **Emotional** - Deep connections\n"
                "• 🤝 **Social** - Interact with others\n\n"
                "**Other Features:**\n"
                "• 👤 Profile & Stats\n"
                "• 💑 Relationships\n"
                "• 🏆 Achievements\n"
                "• 📊 Leaderboards\n"
                "• 🎁 Economy\n"
                "• ⚙️ Settings"
            ),
            color=0x7289DA,
        )
        overview.add_field(
            name="⚡ Quick Start",
            value="`/hug @user` · `/profile` · `/propose @user` · `/top`",
            inline=False,
        )
        overview.set_footer(text="Page 1/7")
        pages.append(overview)

        # Pages 2-5: One per category (dynamically generated)
        categories = get_all_categories()
        page_num = 2
        for cat_key, (cat_label, color) in CATEGORY_INFO.items():
            actions = get_by_category(cat_key)
            if not actions:
                continue
            embed = discord.Embed(
                title=f"{cat_label} Commands",
                description=f"Browse all {cat_label.lower()} roleplay actions.",
                color=color,
            )
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
            embed.set_footer(text=f"Page {page_num}/7")
            pages.append(embed)
            page_num += 1

        # Last Page: Utility commands
        other = discord.Embed(
            title="🛠️ Other Commands",
            description="Utility and management commands.",
            color=0x7289DA,
        )
        other.add_field(
            name="👤 Profile",
            value="`/profile` `/setbio` `/stats`",
            inline=False,
        )
        other.add_field(
            name="💑 Relationships",
            value="`/propose` `/partner` `/breakup` `/anniversary`",
            inline=False,
        )
        other.add_field(
            name="🏆 Achievements",
            value="`/achievements`",
            inline=False,
        )
        other.add_field(
            name="📊 Leaderboard",
            value="`/top affection|level|interactions`",
            inline=False,
        )
        other.add_field(
            name="🎁 Economy",
            value="`/daily`",
            inline=False,
        )
        other.add_field(
            name="⚙️ Settings",
            value="`/settings`",
            inline=False,
        )
        other.set_footer(text=f"Page {page_num}/7")
        pages.append(other)

        await interaction.response.send_message(
            embed=pages[0], view=PaginatedView(pages)
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(HelpCog(bot))
