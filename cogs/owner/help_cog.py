from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from services.action_registry import get_by_category
from views.embeds import PaginatedViewMarkdown

CATEGORY_INFO = {
    "affection": ("Affection", "💕"),
    "playful":   ("Playful", "😄"),
    "emotional": ("Emotional", "💭"),
    "social":    ("Social", "🤝"),
}


class HelpCog(commands.Cog, name="Help"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="help", description="View all bot commands")
    async def help(self, interaction: discord.Interaction) -> None:
        pages: list[str] = []

        # Page 1: Overview
        overview = (
            "# 🌸 Roleplay Bot\n\n"
            "A social roleplay bot with relationships, achievements, leveling, and leaderboards!\n\n"
            "## Browse by Category:\n"
            "• 💕 **Affection** - Show love and care\n"
            "• 😄 **Playful** - Have fun together\n"
            "• 💭 **Emotional** - Deep connections\n"
            "• 🤝 **Social** - Interact with others\n\n"
            "## Other Features:\n"
            "• 👤 Profile & Stats\n"
            "• 💑 Relationships\n"
            "• 🏆 Achievements\n"
            "• 📊 Leaderboards\n"
            "• 🎁 Economy\n"
            "• ⚙️ Settings\n\n"
            "### ⚡ Quick Start\n"
            "`/hug @user` · `/profile` · `/propose @user` · `/top`"
        )
        pages.append(overview)

        # Pages 2-5: One per category (dynamically generated)
        for cat_key, (cat_label, emoji) in CATEGORY_INFO.items():
            actions = get_by_category(cat_key)
            if not actions:
                continue
            
            page_content = f"# {emoji} {cat_label} Commands\n\n"
            page_content += f"Browse all {cat_label.lower()} roleplay actions.\n\n"
            
            for action in actions:
                note = " *(target optional)*" if action.self_targetable else ""
                page_content += (
                    f"## `/{action.name}`{note}\n"
                    f"{action.description}\n"
                    f"- 💕 `+{action.affection_gain}` • ✨ `+{action.xp_gain} XP` • ⏱️ `{action.cooldown_seconds}s`\n\n"
                )
            pages.append(page_content)

        # Last Page: Utility commands
        other = (
            "# 🛠️ Other Commands\n\n"
            "Utility and management commands.\n\n"
            "## 👤 Profile\n"
            "`/profile` `/setbio` `/stats`\n\n"
            "## 💑 Relationships\n"
            "`/propose` `/partner` `/breakup` `/anniversary`\n\n"
            "## 🏆 Achievements\n"
            "`/achievements`\n\n"
            "## 📊 Leaderboard\n"
            "`/top affection|level|interactions`\n\n"
            "## 🎁 Economy\n"
            "`/daily`\n\n"
            "## ⚙️ Settings\n"
            "`/settings`"
        )
        pages.append(other)

        await interaction.response.send_message(
            content=pages[0], view=PaginatedViewMarkdown(pages)
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(HelpCog(bot))
