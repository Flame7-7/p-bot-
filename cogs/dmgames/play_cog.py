from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from repositories.couple_repository import CoupleRepository
from services.dm_games.registry import BY_KEY, GAMES
from services.dm_games.session import GameManager
from services.dm_mirror import get_partner
from utils.interactions import respond
from utils.logging import get_logger

logger = get_logger(__name__)

NEEDS_PARTNER = "💍 You need an active partner to play together — use `/propose` first."


class PlayCog(commands.Cog, name="Play"):
    """Two-player couple games played in both partners' DMs (buttons, selects, modals)."""

    help_category = ("🎮", "Couple Games")

    play_group = app_commands.Group(name="play", description="Play couple games with your partner in DMs")

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.manager = GameManager(bot)
        self.repo = CoupleRepository()

    async def cog_load(self) -> None:
        self.manager.start_sweeper()

    async def cog_unload(self) -> None:
        await self.manager.stop()

    # ── shared start logic ───────────────────────────────────────────────────

    async def start_game(self, interaction: discord.Interaction, key: str) -> None:
        info = BY_KEY.get(key)
        if info is None:
            await respond(interaction, "I don't know that game.", ephemeral=True)
            return
        partner = await get_partner(self.bot, interaction.user.id)
        if partner is None:
            await respond(interaction, NEEDS_PARTNER, ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        await self.manager.start(interaction, partner, info.cls)

    # ── /play ────────────────────────────────────────────────────────────────

    @play_group.command(name="start", description="Start a game with your partner")
    @app_commands.describe(game="Which game to play")
    @app_commands.choices(game=[app_commands.Choice(name=g.label[:100], value=g.key) for g in GAMES])
    async def play_start(self, interaction: discord.Interaction, game: app_commands.Choice[str]) -> None:
        await self.start_game(interaction, game.value)

    @play_group.command(name="quit", description="End the game you're currently in")
    async def play_quit(self, interaction: discord.Interaction) -> None:
        session = await self.manager.quit(interaction.user.id)
        await respond(
            interaction,
            f"Ended **{session.title}**." if session else "You're not in a game right now.",
            ephemeral=True,
        )

    @play_group.command(name="list", description="See every game you can play together")
    async def play_list(self, interaction: discord.Interaction) -> None:
        lines = [f"**{g.label}** — {g.blurb}" for g in GAMES]
        embed = discord.Embed(title="🎮 Couple games", description="\n".join(lines), color=0xFF6FA5)
        embed.set_footer(text="Start one with /play start · scores are shared in /couple stats")
        await respond(interaction, embed=embed, ephemeral=True)

    # ── short aliases kept from the old bot ──────────────────────────────────

    @app_commands.command(name="ttt", description="Play Tic-Tac-Toe with your partner in DMs")
    async def ttt(self, interaction: discord.Interaction) -> None:
        await self.start_game(interaction, "ttt")

    @app_commands.command(name="connect4", description="Play Connect 4 with your partner in DMs")
    async def connect4(self, interaction: discord.Interaction) -> None:
        await self.start_game(interaction, "connect4")

    @app_commands.command(name="wyr", description="Would You Rather with your partner in DMs")
    async def wyr(self, interaction: discord.Interaction) -> None:
        await self.start_game(interaction, "wyr")

    @app_commands.command(name="truthordare", description="Truth or Dare with your partner in DMs")
    async def truthordare(self, interaction: discord.Interaction) -> None:
        await self.start_game(interaction, "truthordare")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(PlayCog(bot))
