from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from repositories.achievement_repository import AchievementRepository
from views.embeds import PaginatedView

ITEMS_PER_PAGE = 6


class AchievementsCog(commands.Cog, name="Achievements"):
    help_category = ("🏆", "Achievements")

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.repo = AchievementRepository()

    @app_commands.command(name="achievements", description="Browse achievements")
    @app_commands.describe(user="User to view (defaults to you)")
    async def achievements(self, interaction: discord.Interaction, user: discord.Member | None = None) -> None:
        await interaction.response.defer()
        target = user or interaction.user
        all_ach = await self.repo.get_all()
        user_ach = await self.repo.get_user_achievements(target.id)
        unlocked_ids = {ua.achievement_id for ua in user_ach if ua.is_unlocked}
        visible = [a for a in all_ach if not a.is_hidden or a.id in unlocked_ids]

        pages: list[discord.Embed] = []
        chunks = [visible[i:i + ITEMS_PER_PAGE] for i in range(0, max(1, len(visible)), ITEMS_PER_PAGE)]
        total_visible = len([a for a in all_ach if not a.is_hidden])

        for chunk in chunks:
            embed = discord.Embed(
                title=f"🏆 {target.display_name}'s Achievements",
                color=0xFFD700,
            )
            embed.set_thumbnail(url=str(target.display_avatar.url))
            for ach in chunk:
                done = ach.id in unlocked_ids
                status = "✅" if done else "🔒"
                rare = " ⭐" if ach.is_rare else ""
                embed.add_field(
                    name=f"{status} {ach.icon} {ach.name}{rare}",
                    value=ach.description if (done or not ach.is_hidden) else "???",
                    inline=False,
                )
            embed.set_footer(text=f"{len(unlocked_ids)}/{total_visible} unlocked")
            pages.append(embed)

        if len(pages) == 1:
            await interaction.followup.send(embed=pages[0])
        else:
            await interaction.followup.send(embed=pages[0], view=PaginatedView(pages))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AchievementsCog(bot))
