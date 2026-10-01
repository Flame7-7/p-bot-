from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from repositories.interaction_repository import InteractionRepository
from repositories.user_repository import UserRepository
from utils.config import get_config
from utils.cooldowns import cache_get, cache_set
from utils.logging import get_logger
from views.embeds import PaginatedView

logger = get_logger(__name__)
config = get_config()

PAGE_SIZE = 10
MEDALS = ["🥇", "🥈", "🥉"]


class EconomyCog(commands.Cog, name="Economy"):
    help_category = ("💰", "Economy")

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.user_repo = UserRepository()
        self.interaction_repo = InteractionRepository()

    @app_commands.command(
        name="daily",
        description="Claim your daily XP and affection reward"
    )
    async def daily(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()

        uid = interaction.user.id

        # Already claimed today?
        if cache_get(f"daily:{uid}"):
            await interaction.followup.send(
                "⏳ You already claimed today's reward! Come back tomorrow."
            )
            return

        # Ensure user exists
        await self.user_repo.get_or_create(
            uid,
            interaction.user.display_name,
            str(interaction.user.display_avatar.url),
        )

        # Calculate streak
        streak_data = cache_get(f"streak:{uid}") or {"streak": 0}
        streak = min(
            int(streak_data.get("streak", 0)) + 1,
            config.max_streak,
        )

        bonus = config.streak_bonus_xp * (streak - 1)
        total_xp = config.daily_xp + bonus

        # Give rewards
        new_level, _, leveled_up = await self.user_repo.add_xp(uid, total_xp)
        await self.user_repo.add_affection(uid, config.daily_affection)

        # Save cooldown + streak
        cache_set(f"daily:{uid}", True, ttl=86400)
        cache_set(f"streak:{uid}", {"streak": streak}, ttl=172800)

        embed = discord.Embed(
            title="🎁 Daily Reward!",
            color=0xFFB347,
        )

        embed.set_thumbnail(url=str(interaction.user.display_avatar.url))

        embed.add_field(
            name="✨ XP",
            value=f"+{total_xp}",
            inline=True,
        )

        embed.add_field(
            name="💕 Affection",
            value=f"+{config.daily_affection}",
            inline=True,
        )

        embed.add_field(
            name="🔥 Streak",
            value=f"{streak} day{'s' if streak != 1 else ''}",
            inline=True,
        )

        if bonus > 0:
            embed.add_field(
                name="⚡ Streak Bonus",
                value=f"+{bonus} XP",
                inline=False,
            )

        if leveled_up:
            embed.add_field(
                name="🎉 Level Up!",
                value=f"You reached **Level {new_level}**!",
                inline=False,
            )

        embed.set_footer(
            text=f"Max streak: {config.max_streak} days"
        )
        embed.timestamp = discord.utils.utcnow()

        await interaction.followup.send(embed=embed)

    @app_commands.command(
        name="top",
        description="View the leaderboard"
    )
    @app_commands.describe(category="Which leaderboard to view")
    @app_commands.choices(
        category=[
            app_commands.Choice(
                name="💕 Affection",
                value="affection",
            ),
            app_commands.Choice(
                name="⭐ Level",
                value="level",
            ),
            app_commands.Choice(
                name="🎯 Interactions",
                value="interactions",
            ),
        ]
    )
    async def top(
        self,
        interaction: discord.Interaction,
        category: app_commands.Choice[str],
    ) -> None:
        await interaction.response.defer()

        cache_key = f"lb:{category.value}"
        rows = cache_get(cache_key)

        if not rows:
            rows = await self.interaction_repo.get_leaderboard(
                category.value,
                limit=50,
            )
            cache_set(cache_key, rows, ttl=60)

        if not rows:
            await interaction.followup.send(
                "No data yet! Start interacting to appear here."
            )
            return

        pages: list[discord.Embed] = []

        chunks = [
            rows[i:i + PAGE_SIZE]
            for i in range(0, len(rows), PAGE_SIZE)
        ]

        for page_num, chunk in enumerate(chunks):
            embed = discord.Embed(
                title=f"🏆 {category.name} Leaderboard",
                color=0xFEE75C,
            )

            lines = []

            for i, row in enumerate(chunk):
                rank = page_num * PAGE_SIZE + i

                prefix = (
                    MEDALS[rank]
                    if rank < 3
                    else f"**#{rank + 1}**"
                )

                member = (
                    interaction.guild.get_member(row["user_id"])
                    if interaction.guild
                    else None
                )

                name = (
                    member.display_name
                    if member
                    else f"User {row['user_id']}"
                )

                lines.append(
                    f"{prefix} **{name}** — `{row['value']:,}`"
                )

            embed.description = "\n".join(lines)

            embed.set_footer(
                text=f"Page {page_num + 1}/{len(chunks)} • Updates every 60s"
            )

            embed.timestamp = discord.utils.utcnow()
            pages.append(embed)

        if len(pages) == 1:
            await interaction.followup.send(embed=pages[0])
        else:
            await interaction.followup.send(
                embed=pages[0],
                view=PaginatedView(pages),
            )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(EconomyCog(bot))