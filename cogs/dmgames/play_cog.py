from __future__ import annotations

import asyncio

import discord
from discord import app_commands
from discord.ext import commands

from repositories.couple_repository import CoupleRepository
from services.dm_games.registry import BY_KEY, CATEGORIES, GAMES, GameInfo, categories_in_use, games_in
from services.dm_games.session import GameManager
from services.dm_mirror import get_partner
from utils.interactions import OwnedView, respond
from utils.logging import get_logger

logger = get_logger(__name__)

NEEDS_PARTNER = "💍 You need an active partner to play together — use `/propose` first."
PINK = 0xFF6FA5


def game_details(game: GameInfo) -> str:
    lines = [game.blurb, f"⏱ {game.duration}" if game.duration else "", f"👥 {game.players}"]
    if game.difficulty:
        lines.append(f"🎚 {game.difficulty}")
    return "\n".join(l for l in lines if l)


class LauncherView(OwnedView):
    """/play: category → game → [Play]. Built from the game registry, so new games show up by themselves."""

    def __init__(self, cog: "PlayCog", owner_id: int) -> None:
        super().__init__([owner_id], timeout=300)
        self.cog = cog
        self.category: str | None = None
        self.game: GameInfo | None = None
        self._rebuild()

    # ── embeds ───────────────────────────────────────────────────────────────

    def embed(self) -> discord.Embed:
        if self.game:
            e = discord.Embed(title=self.game.label, description=game_details(self.game), color=PINK)
            e.set_footer(text=f"{self.game.category} • press Play to send it to both your DMs")
            return e
        if self.category:
            emoji, blurb = CATEGORIES.get(self.category, ("🎮", ""))
            games = games_in(self.category)
            e = discord.Embed(title=f"{emoji} {self.category}", description=blurb or None, color=PINK)
            for g in games:
                e.add_field(name=g.label, value=game_details(g), inline=True)
            e.set_footer(text="Pick a game from the menu below")
            return e
        lines = []
        for cat in categories_in_use():
            emoji, blurb = CATEGORIES.get(cat, ("🎮", ""))
            lines.append(f"{emoji} **{cat}** — {len(games_in(cat))} games" + (f" · {blurb}" if blurb else ""))
        return discord.Embed(
            title="🎮 COUPLE GAMES",
            description="Choose a category:\n\n" + "\n".join(lines),
            color=PINK,
        )

    # ── components ───────────────────────────────────────────────────────────

    def _rebuild(self) -> None:
        self.clear_items()
        cats = discord.ui.Select(
            placeholder="Choose a category…",
            options=[
                discord.SelectOption(
                    label=c, emoji=CATEGORIES.get(c, ("🎮", ""))[0], value=c, default=c == self.category,
                    description=f"{len(games_in(c))} games",
                )
                for c in categories_in_use()
            ],
            row=0,
        )
        cats.callback = self._pick_category  # type: ignore[method-assign]
        self.add_item(cats)

        if self.category:
            games = discord.ui.Select(
                placeholder="Pick a game…",
                options=[
                    discord.SelectOption(label=g.label[:100], value=g.key, description=g.blurb[:100], default=bool(self.game and g.key == self.game.key))
                    for g in games_in(self.category)
                ],
                row=1,
            )
            games.callback = self._pick_game  # type: ignore[method-assign]
            self.add_item(games)

        if self.game:
            play = discord.ui.Button(label="Play", emoji="▶️", style=discord.ButtonStyle.success, row=2)
            play.callback = self._play  # type: ignore[method-assign]
            self.add_item(play)
        if self.category or self.game:
            back = discord.ui.Button(label="Back", emoji="⬅️", style=discord.ButtonStyle.secondary, row=2)
            back.callback = self._back  # type: ignore[method-assign]
            self.add_item(back)

    async def _pick_category(self, interaction: discord.Interaction) -> None:
        self.category = interaction.data["values"][0]  # type: ignore[index]
        self.game = None
        self._rebuild()
        await interaction.response.edit_message(embed=self.embed(), view=self)

    async def _pick_game(self, interaction: discord.Interaction) -> None:
        self.game = BY_KEY.get(interaction.data["values"][0])  # type: ignore[index]
        self._rebuild()
        await interaction.response.edit_message(embed=self.embed(), view=self)

    async def _back(self, interaction: discord.Interaction) -> None:
        if self.game:
            self.game = None
        else:
            self.category = None
        self._rebuild()
        await interaction.response.edit_message(embed=self.embed(), view=self)

    async def _play(self, interaction: discord.Interaction) -> None:
        if self.game is None:
            return
        game = self.game
        self.stop()
        await interaction.response.edit_message(
            embed=discord.Embed(title=game.label, description="Starting…", color=PINK), view=None
        )
        await self.cog.start_game(interaction, game.key)


class PlayCog(commands.Cog, name="Play"):
    """Two-player couple games played in both partners' DMs (buttons, selects, modals)."""

    help_category = ("🎮", "Couple Games")

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.manager = GameManager(bot)
        self.repo = CoupleRepository()
        self._cleanup_task: asyncio.Task | None = None

    async def cog_load(self) -> None:
        self.manager.start_sweeper()
        # Game messages from a previous run have dead buttons; close them once.
        self._cleanup_task = asyncio.create_task(self._cleanup_after_restart(), name="game-cleanup")

    async def cog_unload(self) -> None:
        if self._cleanup_task:
            self._cleanup_task.cancel()
        await self.manager.stop()

    async def _cleanup_after_restart(self) -> None:
        try:
            closed = await self.manager.cleanup_stale_messages()
            if closed:
                logger.info("closed %d game message(s) left over from the previous run", closed)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("startup game-message cleanup failed")

    # ── activity feed for the bump timers ────────────────────────────────────

    @commands.Cog.listener("on_message")
    async def on_message(self, message: discord.Message) -> None:
        if message.guild is None:
            self.manager.note_message(message.channel.id, message.id)

    @commands.Cog.listener("on_raw_message_delete")
    async def on_raw_message_delete(self, payload: discord.RawMessageDeleteEvent) -> None:
        self.manager.note_deleted(payload.message_id)

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
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=True)
        await self.manager.start(interaction, partner, info.cls)

    # ── /play ────────────────────────────────────────────────────────────────

    async def _game_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        current = current.lower()
        return [
            app_commands.Choice(name=g.label[:100], value=g.key)
            for g in GAMES
            if current in g.label.lower() or current in g.category.lower()
        ][:25]

    @app_commands.command(name="play", description="Pick a couple game to play together in DMs")
    @app_commands.describe(game="Skip the menu and start a game directly")
    @app_commands.autocomplete(game=_game_autocomplete)
    async def play(self, interaction: discord.Interaction, game: str | None = None) -> None:
        if game:
            await self.start_game(interaction, game)
            return
        if await get_partner(self.bot, interaction.user.id) is None:
            await respond(interaction, NEEDS_PARTNER, ephemeral=True)
            return
        view = LauncherView(self, interaction.user.id)
        await interaction.response.send_message(embed=view.embed(), view=view, ephemeral=True)
        view.message = await interaction.original_response()

    @app_commands.command(name="gamequit", description="End the game you're currently in")
    async def gamequit(self, interaction: discord.Interaction) -> None:
        session = await self.manager.quit(interaction.user.id)
        await respond(
            interaction,
            f"Ended **{session.title}**." if session else "You're not in a game right now.",
            ephemeral=True,
        )

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
