from __future__ import annotations

import discord

from services.roleplay_service import ActionResult

CATEGORY_COLORS = {
    "affection": 0xFF85A1,
    "playful":   0xFFD166,
    "emotional": 0xA8DADC,
    "social":    0xB5EAD7,
}


def build_action_embed(
    result: ActionResult,
    category: str,
    author: discord.Member,
    target: discord.Member | None = None,
) -> discord.Embed:
    color = CATEGORY_COLORS.get(category, 0x7289DA)
    embed = discord.Embed(description=result.message, color=color)
    if result.gif_url:
        embed.set_image(url=result.gif_url)
    parts = [f"+{result.xp_gained} XP", f"+{result.affection_gained} 💕"]
    if result.is_relationship_bonus:
        parts.append("💑 Partner Bonus!")
    embed.set_footer(text="  •  ".join(parts))
    return embed


def build_levelup_embed(author: discord.Member, new_level: int) -> discord.Embed:
    embed = discord.Embed(
        title="🎉 Level Up!",
        description=f"**{author.display_name}** reached **Level {new_level}**!",
        color=0xFFD700,
    )
    embed.set_thumbnail(url=str(author.display_avatar.url))
    return embed


def build_achievement_embed(name: str, author: discord.Member) -> discord.Embed:
    return discord.Embed(
        title="🏆 Achievement Unlocked!",
        description=f"**{author.display_name}** unlocked **{name}**!",
        color=0xFFD700,
    )


def build_profile_embed(
    user: discord.Member,
    profile,
    stats,
    relationship_info: str | None,
    achievements_count: int,
) -> discord.Embed:
    embed = discord.Embed(title=f"{user.display_name}'s Profile", color=0xA8A4FF)
    embed.set_thumbnail(url=str(user.display_avatar.url))
    embed.add_field(name="📊 Level", value=str(profile.level), inline=True)
    embed.add_field(name="✨ XP", value=f"{profile.xp:,}", inline=True)
    embed.add_field(name="💕 Affection", value=f"{profile.affection:,}", inline=True)
    embed.add_field(name="💑 Partner", value=relationship_info or "Single", inline=True)
    embed.add_field(name="🏆 Achievements", value=str(achievements_count), inline=True)
    embed.add_field(
        name="🎯 Fav Action",
        value=f"/{stats.favorite_action}" if stats and stats.favorite_action else "None",
        inline=True,
    )
    if stats:
        embed.add_field(
            name="📈 Interactions",
            value=f"Given: **{stats.total_given:,}**\nReceived: **{stats.total_received:,}**\nToday: **{stats.daily_given:,}**",
            inline=False,
        )
    if profile.bio:
        embed.add_field(name="📝 Bio", value=profile.bio, inline=False)
    embed.set_footer(text=f"ID: {user.id}")
    return embed


def build_relationship_embed(
    user: discord.Member,
    partner: discord.Member,
    relationship,
) -> discord.Embed:
    from datetime import datetime, timezone
    days = (datetime.now(timezone.utc) - relationship.started_at.replace(tzinfo=timezone.utc)).days
    embed = discord.Embed(title="💑 Relationship", color=0xFF85A1)
    embed.add_field(name="Partners", value=f"{user.mention} & {partner.mention}", inline=False)
    embed.add_field(name="💕 Shared Affection", value=f"{relationship.shared_affection:,}", inline=True)
    embed.add_field(name="📅 Together", value=f"{days} days", inline=True)
    embed.add_field(name="🗓️ Since", value=relationship.started_at.strftime("%B %d, %Y"), inline=True)
    embed.set_thumbnail(url=str(user.display_avatar.url))
    return embed


class PaginatedView(discord.ui.View):
    def __init__(self, pages: list[discord.Embed], timeout: float = 120.0) -> None:
        super().__init__(timeout=timeout)
        self.pages = pages
        self.current = 0
        self._sync()

    def _sync(self) -> None:
        self.btn_first.disabled = self.current == 0
        self.btn_prev.disabled = self.current == 0
        self.btn_next.disabled = self.current >= len(self.pages) - 1
        self.btn_last.disabled = self.current >= len(self.pages) - 1
        self.btn_page.label = f"{self.current + 1}/{len(self.pages)}"

    @discord.ui.button(label="◀◀", style=discord.ButtonStyle.secondary)
    async def btn_first(self, i: discord.Interaction, b: discord.ui.Button) -> None:
        self.current = 0; self._sync()
        await i.response.edit_message(embed=self.pages[self.current], view=self)

    @discord.ui.button(label="◀", style=discord.ButtonStyle.primary)
    async def btn_prev(self, i: discord.Interaction, b: discord.ui.Button) -> None:
        self.current = max(0, self.current - 1); self._sync()
        await i.response.edit_message(embed=self.pages[self.current], view=self)

    @discord.ui.button(label="1/1", style=discord.ButtonStyle.secondary, disabled=True)
    async def btn_page(self, i: discord.Interaction, b: discord.ui.Button) -> None:
        pass

    @discord.ui.button(label="▶", style=discord.ButtonStyle.primary)
    async def btn_next(self, i: discord.Interaction, b: discord.ui.Button) -> None:
        self.current = min(len(self.pages) - 1, self.current + 1); self._sync()
        await i.response.edit_message(embed=self.pages[self.current], view=self)

    @discord.ui.button(label="▶▶", style=discord.ButtonStyle.secondary)
    async def btn_last(self, i: discord.Interaction, b: discord.ui.Button) -> None:
        self.current = len(self.pages) - 1; self._sync()
        await i.response.edit_message(embed=self.pages[self.current], view=self)

    async def on_timeout(self) -> None:
        for c in self.children:
            c.disabled = True  # type: ignore[attr-defined]
