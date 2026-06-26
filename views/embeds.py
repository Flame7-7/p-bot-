from __future__ import annotations

import discord
from discord.ui import Button, View, button

from services.roleplay_service import ActionResult

# Discord UI v2 color palette - softer, modern colors
CATEGORY_COLORS = {
    "affection": 0xF47FFF,      # Vibrant pink
    "playful":   0xFFB347,      # Warm orange
    "emotional": 0x58B6FF,      # Soft blue
    "social":    0x77D958,      # Fresh green
}

# Discord blurple for general UI elements
DISCORD_BLURPLE = 0x5865F2
DISCORD_GREEN = 0x57F287
DISCORD_RED = 0xED4245
DISCORD_GOLD = 0xFEE75C


def build_action_embed(
    result: ActionResult,
    category: str,
    author: discord.Member,
    target: discord.Member | None = None,
) -> discord.Embed:
    """Build a modern Discord UI v2 styled action embed."""
    color = CATEGORY_COLORS.get(category, DISCORD_BLURPLE)

    # Build the main message with better formatting
    if target:
        description = f"{author.mention} {result.message}"
    else:
        description = f"{author.mention} {result.message}"

    embed = discord.Embed(description=description, color=color)

    if result.gif_url:
        embed.set_image(url=result.gif_url)

    # Add author avatar for personalization
    embed.set_author(name=author.display_name, icon_url=author.display_avatar.url)

    # Compact footer with stats
    stat_parts = [f"+{result.xp_gained} XP", f"+{result.affection_gained} 💕"]
    if result.is_relationship_bonus:
        stat_parts.insert(1, "💑 Partner Bonus")

    embed.set_footer(text="  •  ".join(stat_parts))
    embed.timestamp = discord.utils.utcnow()

    return embed


def build_levelup_embed(author: discord.Member, new_level: int) -> discord.Embed:
    """Build a celebratory level up embed with Discord UI v2 styling."""
    embed = discord.Embed(
        title=f"🎉 Level {new_level}!",
        description=f"**{author.display_name}** just leveled up!",
        color=DISCORD_GOLD,
    )
    embed.set_thumbnail(url=str(author.display_avatar.url))
    embed.set_footer(text="Keep interacting to reach even higher levels!")
    embed.timestamp = discord.utils.utcnow()
    return embed


def build_achievement_embed(name: str, author: discord.Member) -> discord.Embed:
    """Build an achievement unlock embed with modern styling."""
    embed = discord.Embed(
        title="🏆 Achievement Unlocked",
        description=f"**{author.display_name}** earned:\n\n### {name}",
        color=DISCORD_GOLD,
    )
    embed.set_thumbnail(url=str(author.display_avatar.url))
    embed.set_footer(text="Congratulations on this milestone!")
    embed.timestamp = discord.utils.utcnow()
    return embed


def build_profile_embed(
    user: discord.Member,
    profile,
    stats,
    relationship_info: str | None,
    achievements_count: int,
) -> discord.Embed:
    """Build a comprehensive profile embed with Discord UI v2 layout."""
    embed = discord.Embed(
        title=f"👤 {user.display_name}",
        color=DISCORD_BLURPLE,
    )
    embed.set_thumbnail(url=str(user.display_avatar.url))

    # Main stats row
    embed.add_field(
        name="⭐ Level",
        value=f"`{profile.level}`",
        inline=True
    )
    embed.add_field(
        name="✨ XP",
        value=f"`{profile.xp:,}`",
        inline=True
    )
    embed.add_field(
        name="💕 Affection",
        value=f"`{profile.affection:,}`",
        inline=True
    )

    # Secondary stats row
    embed.add_field(
        name="💑 Status",
        value=relationship_info or "`Single`",
        inline=True
    )
    embed.add_field(
        name="🏆 Achievements",
        value=f"`{achievements_count}`",
        inline=True
    )
    fav_action = f"`/{stats.favorite_action}`" if stats and stats.favorite_action else "`None`"
    embed.add_field(
        name="🎯 Favorite",
        value=fav_action,
        inline=True
    )

    # Detailed stats section
    if stats:
        embed.add_field(
            name="📊 Statistics",
            value=(
                f"Given: `{stats.total_given:,}`\n"
                f"Received: `{stats.total_received:,}`\n"
                f"Today: `{stats.daily_given:,}`"
            ),
            inline=False
        )

    if profile.bio:
        embed.add_field(
            name="📝 About",
            value=profile.bio[:1024],
            inline=False
        )

    embed.set_footer(text=f"User ID: {user.id}")
    embed.timestamp = discord.utils.utcnow()

    return embed


def build_relationship_embed(
    user: discord.Member,
    partner: discord.Member,
    relationship,
) -> discord.Embed:
    """Build a relationship status embed with Discord UI v2 styling."""
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    started = relationship.started_at.replace(tzinfo=timezone.utc)
    days = (now - started).days

    embed = discord.Embed(
        title="💑 Relationship Status",
        color=0xFF85A1,
    )

    # Show both partners
    embed.description = (
        f"{user.mention} **×** {partner.mention}\n"
        f"*Together for {days} day{'s' if days != 1 else ''}*"
    )

    embed.add_field(
        name="💕 Shared Affection",
        value=f"`{relationship.shared_affection:,}`",
        inline=True
    )
    embed.add_field(
        name="🗓️ Since",
        value=started.strftime("%b %d, %Y"),
        inline=True
    )
    embed.add_field(
        name="📅 Duration",
        value=f"`{days} days`",
        inline=True
    )

    # Set thumbnails for both users
    embed.set_thumbnail(url=str(user.display_avatar.url))
    embed.set_footer(text="Cherish your bond!")
    embed.timestamp = discord.utils.utcnow()

    return embed


class DiscordUIV2View(View):
    """Base view class with Discord UI v2 styling conventions."""

    def __init__(self, timeout: float | None = 180.0) -> None:
        super().__init__(timeout=timeout)

    async def on_timeout(self) -> None:
        """Disable all buttons on timeout."""
        for child in self.children:
            if isinstance(child, Button):
                child.disabled = True


class PaginatedView(DiscordUIV2View):
    """Modern pagination view with Discord UI v2 button styling."""

    def __init__(self, pages: list[discord.Embed], timeout: float = 180.0) -> None:
        super().__init__(timeout=timeout)
        self.pages = pages
        self.current_page = 0
        self._update_buttons()

    def _update_buttons(self) -> None:
        """Update button states based on current page."""
        total = len(self.pages)

        # Update navigation buttons
        for child in self.children:
            if isinstance(child, Button):
                if child.custom_id == "first_page":
                    child.disabled = self.current_page == 0
                elif child.custom_id == "prev_page":
                    child.disabled = self.current_page == 0
                elif child.custom_id == "next_page":
                    child.disabled = self.current_page >= total - 1
                elif child.custom_id == "last_page":
                    child.disabled = self.current_page >= total - 1
                elif child.custom_id == "page_indicator":
                    child.label = f"Page {self.current_page + 1}/{total}"

    @button(label="⏮️", style=discord.ButtonStyle.secondary, custom_id="first_page")
    async def first_page(self, interaction: discord.Interaction, button: Button) -> None:
        """Go to first page."""
        self.current_page = 0
        self._update_buttons()
        await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)

    @button(label="◀️", style=discord.ButtonStyle.primary, custom_id="prev_page")
    async def prev_page(self, interaction: discord.Interaction, button: Button) -> None:
        """Go to previous page."""
        self.current_page = max(0, self.current_page - 1)
        self._update_buttons()
        await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)

    @button(label="Page 1/1", style=discord.ButtonStyle.secondary, custom_id="page_indicator", disabled=True)
    async def page_indicator(self, interaction: discord.Interaction, button: Button) -> None:
        """Page indicator (non-interactive)."""
        pass

    @button(label="▶️", style=discord.ButtonStyle.primary, custom_id="next_page")
    async def next_page(self, interaction: discord.Interaction, button: Button) -> None:
        """Go to next page."""
        self.current_page = min(len(self.pages) - 1, self.current_page + 1)
        self._update_buttons()
        await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)

    @button(label="⏭️", style=discord.ButtonStyle.secondary, custom_id="last_page")
    async def last_page(self, interaction: discord.Interaction, button: Button) -> None:
        """Go to last page."""
        self.current_page = len(self.pages) - 1
        self._update_buttons()
        await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)

    async def on_timeout(self) -> None:
        """Disable all buttons when view times out."""
        for child in self.children:
            if isinstance(child, Button):
                child.disabled = True
        try:
            # Try to update the message to show disabled state
            pass  # Message editing handled by Discord automatically on timeout
        except discord.HTTPException:
            pass


def build_profile_embed(
    user: discord.Member,
    profile,
    stats,
    achievements,
    badges: list[str],
) -> discord.Embed:
    """Build a modern Discord UI v2 styled action embed."""
    color = CATEGORY_COLORS.get(category, DISCORD_BLURPLE)

    # Build the main message with better formatting
    if target:
        description = f"{author.mention} {result.message}"
    else:
        description = f"{author.mention} {result.message}"

    embed = discord.Embed(description=description, color=color)

    if result.gif_url:
        embed.set_image(url=result.gif_url)

    # Add author avatar for personalization
    embed.set_author(name=author.display_name, icon_url=author.display_avatar.url)

    # Compact footer with stats
    stat_parts = [f"+{result.xp_gained} XP", f"+{result.affection_gained} 💕"]
    if result.is_relationship_bonus:
        stat_parts.insert(1, "💑 Partner Bonus")

    embed.set_footer(text="  •  ".join(stat_parts))
    embed.timestamp = discord.utils.utcnow()

    return embed


def build_levelup_embed(author: discord.Member, new_level: int) -> discord.Embed:
    """Build a celebratory level up embed with Discord UI v2 styling."""
    embed = discord.Embed(
        title=f"🎉 Level {new_level}!",
        description=f"**{author.display_name}** just leveled up!",
        color=DISCORD_GOLD,
    )
    embed.set_thumbnail(url=str(author.display_avatar.url))
    embed.set_footer(text="Keep interacting to reach even higher levels!")
    embed.timestamp = discord.utils.utcnow()
    return embed


def build_achievement_embed(name: str, author: discord.Member) -> discord.Embed:
    """Build an achievement unlock embed with modern styling."""
    embed = discord.Embed(
        title="🏆 Achievement Unlocked",
        description=f"**{author.display_name}** earned:\n\n### {name}",
        color=DISCORD_GOLD,
    )
    embed.set_thumbnail(url=str(author.display_avatar.url))
    embed.set_footer(text="Congratulations on this milestone!")
    embed.timestamp = discord.utils.utcnow()
    return embed


def build_profile_embed(
    user: discord.Member,
    profile,
    stats,
    relationship_info: str | None,
    achievements_count: int,
) -> discord.Embed:
    """Build a comprehensive profile embed with Discord UI v2 layout."""
    embed = discord.Embed(
        title=f"👤 {user.display_name}",
        color=DISCORD_BLURPLE,
    )
    embed.set_thumbnail(url=str(user.display_avatar.url))

    # Main stats row
    embed.add_field(
        name="⭐ Level",
        value=f"`{profile.level}`",
        inline=True
    )
    embed.add_field(
        name="✨ XP",
        value=f"`{profile.xp:,}`",
        inline=True
    )
    embed.add_field(
        name="💕 Affection",
        value=f"`{profile.affection:,}`",
        inline=True
    )

    # Secondary stats row
    embed.add_field(
        name="💑 Status",
        value=relationship_info or "`Single`",
        inline=True
    )
    embed.add_field(
        name="🏆 Achievements",
        value=f"`{achievements_count}`",
        inline=True
    )
    fav_action = f"`/{stats.favorite_action}`" if stats and stats.favorite_action else "`None`"
    embed.add_field(
        name="🎯 Favorite",
        value=fav_action,
        inline=True
    )

    # Detailed stats section
    if stats:
        embed.add_field(
            name="📊 Statistics",
            value=(
                f"Given: `{stats.total_given:,}`\n"
                f"Received: `{stats.total_received:,}`\n"
                f"Today: `{stats.daily_given:,}`"
            ),
            inline=False
        )

    if profile.bio:
        embed.add_field(
            name="📝 About",
            value=profile.bio[:1024],
            inline=False
        )

    embed.set_footer(text=f"User ID: {user.id}")
    embed.timestamp = discord.utils.utcnow()

    return embed


def build_relationship_embed(
    user: discord.Member,
    partner: discord.Member,
    relationship,
) -> discord.Embed:
    """Build a relationship status embed with Discord UI v2 styling."""
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    started = relationship.started_at.replace(tzinfo=timezone.utc)
    days = (now - started).days

    embed = discord.Embed(
        title="💑 Relationship Status",
        color=0xFF85A1,
    )

    # Show both partners
    embed.description = (
        f"{user.mention} **×** {partner.mention}\n"
        f"*Together for {days} day{'s' if days != 1 else ''}*"
    )

    embed.add_field(
        name="💕 Shared Affection",
        value=f"`{relationship.shared_affection:,}`",
        inline=True
    )
    embed.add_field(
        name="🗓️ Since",
        value=started.strftime("%b %d, %Y"),
        inline=True
    )
    embed.add_field(
        name="📅 Duration",
        value=f"`{days} days`",
        inline=True
    )

    # Set thumbnails for both users
    embed.set_thumbnail(url=str(user.display_avatar.url))
    embed.set_footer(text="Cherish your bond!")
    embed.timestamp = discord.utils.utcnow()

    return embed


class DiscordUIV2View(View):
    """Base view class with Discord UI v2 styling conventions."""

    def __init__(self, timeout: float | None = 180.0) -> None:
        super().__init__(timeout=timeout)

    async def on_timeout(self) -> None:
        """Disable all buttons on timeout."""
        for child in self.children:
            if isinstance(child, Button):
                child.disabled = True


class PaginatedView(DiscordUIV2View):
    """Modern pagination view with Discord UI v2 button styling."""

    def __init__(self, pages: list[discord.Embed], timeout: float = 180.0) -> None:
        super().__init__(timeout=timeout)
        self.pages = pages
        self.current_page = 0
        self._update_buttons()

    def _update_buttons(self) -> None:
        """Update button states based on current page."""
        total = len(self.pages)

        # Update navigation buttons
        for child in self.children:
            if isinstance(child, Button):
                if child.custom_id == "first_page":
                    child.disabled = self.current_page == 0
                elif child.custom_id == "prev_page":
                    child.disabled = self.current_page == 0
                elif child.custom_id == "next_page":
                    child.disabled = self.current_page >= total - 1
                elif child.custom_id == "last_page":
                    child.disabled = self.current_page >= total - 1
                elif child.custom_id == "page_indicator":
                    child.label = f"Page {self.current_page + 1}/{total}"

    @button(label="⏮️", style=discord.ButtonStyle.secondary, custom_id="first_page")
    async def first_page(self, interaction: discord.Interaction, button: Button) -> None:
        """Go to first page."""
        self.current_page = 0
        self._update_buttons()
        await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)

    @button(label="◀️", style=discord.ButtonStyle.primary, custom_id="prev_page")
    async def prev_page(self, interaction: discord.Interaction, button: Button) -> None:
        """Go to previous page."""
        self.current_page = max(0, self.current_page - 1)
        self._update_buttons()
        await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)

    @button(label="Page 1/1", style=discord.ButtonStyle.secondary, custom_id="page_indicator", disabled=True)
    async def page_indicator(self, interaction: discord.Interaction, button: Button) -> None:
        """Page indicator (non-interactive)."""
        pass

    @button(label="▶️", style=discord.ButtonStyle.primary, custom_id="next_page")
    async def next_page(self, interaction: discord.Interaction, button: Button) -> None:
        """Go to next page."""
        self.current_page = min(len(self.pages) - 1, self.current_page + 1)
        self._update_buttons()
        await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)

    @button(label="⏭️", style=discord.ButtonStyle.secondary, custom_id="last_page")
    async def last_page(self, interaction: discord.Interaction, button: Button) -> None:
        """Go to last page."""
        self.current_page = len(self.pages) - 1
        self._update_buttons()
        await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)

    async def on_timeout(self) -> None:
        """Disable all buttons when view times out."""
        for child in self.children:
            if isinstance(child, Button):
                child.disabled = True
        try:
            # Try to update the message to show disabled state
            pass  # Message editing handled by Discord automatically on timeout
        except discord.HTTPException:
            pass


class PaginatedViewMarkdown(DiscordUIV2View):
    """Modern pagination view with Discord UI v2 button styling for markdown content."""

    def __init__(self, pages: list[str], timeout: float = 180.0) -> None:
        super().__init__(timeout=timeout)
        self.pages = pages
        self.current_page = 0
        self._update_buttons()

    def _update_buttons(self) -> None:
        """Update button states based on current page."""
        total = len(self.pages)

        # Update navigation buttons
        for child in self.children:
            if isinstance(child, Button):
                if child.custom_id == "first_page":
                    child.disabled = self.current_page == 0
                elif child.custom_id == "prev_page":
                    child.disabled = self.current_page == 0
                elif child.custom_id == "next_page":
                    child.disabled = self.current_page >= total - 1
                elif child.custom_id == "last_page":
                    child.disabled = self.current_page >= total - 1
                elif child.custom_id == "page_indicator":
                    child.label = f"Page {self.current_page + 1}/{total}"

    @button(label="⏮️", style=discord.ButtonStyle.secondary, custom_id="first_page")
    async def first_page(self, interaction: discord.Interaction, button: Button) -> None:
        """Go to first page."""
        self.current_page = 0
        self._update_buttons()
        await interaction.response.edit_message(content=self.pages[self.current_page], view=self)

    @button(label="◀️", style=discord.ButtonStyle.primary, custom_id="prev_page")
    async def prev_page(self, interaction: discord.Interaction, button: Button) -> None:
        """Go to previous page."""
        self.current_page = max(0, self.current_page - 1)
        self._update_buttons()
        await interaction.response.edit_message(content=self.pages[self.current_page], view=self)

    @button(label="Page 1/1", style=discord.ButtonStyle.secondary, custom_id="page_indicator", disabled=True)
    async def page_indicator(self, interaction: discord.Interaction, button: Button) -> None:
        """Page indicator (non-interactive)."""
        pass

    @button(label="▶️", style=discord.ButtonStyle.primary, custom_id="next_page")
    async def next_page(self, interaction: discord.Interaction, button: Button) -> None:
        """Go to next page."""
        self.current_page = min(len(self.pages) - 1, self.current_page + 1)
        self._update_buttons()
        await interaction.response.edit_message(content=self.pages[self.current_page], view=self)

    @button(label="⏭️", style=discord.ButtonStyle.secondary, custom_id="last_page")
    async def last_page(self, interaction: discord.Interaction, button: Button) -> None:
        """Go to last page."""
        self.current_page = len(self.pages) - 1
        self._update_buttons()
        await interaction.response.edit_message(content=self.pages[self.current_page], view=self)

    async def on_timeout(self) -> None:
        """Disable all buttons when view times out."""
        for child in self.children:
            if isinstance(child, Button):
                child.disabled = True
        try:
            pass
        except discord.HTTPException:
            pass
