from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from repositories.relationship_repository import RelationshipRepository

WIN_LINES = [(0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 3, 6), (1, 4, 7), (2, 5, 8), (0, 4, 8), (2, 4, 6)]


class DuoTicTacToeGame:
    """Shared state for one match. Both players' messages point at the same
    game + the same View instance, so a move made in either DM updates both.
    """

    def __init__(self, p1_id: int, p2_id: int) -> None:
        self.order = [p1_id, p2_id]
        self.marks = {p1_id: "❌", p2_id: "⭕"}
        self.board: list[str | None] = [None] * 9
        self.turn_idx = 0
        self.finished = False
        self.messages: dict[int, discord.Message] = {}

    @property
    def turn_id(self) -> int:
        return self.order[self.turn_idx]

    def other(self, user_id: int) -> int:
        return self.order[1] if user_id == self.order[0] else self.order[0]

    def play(self, user_id: int, idx: int) -> bool:
        if self.finished or self.board[idx] is not None or user_id != self.turn_id:
            return False
        self.board[idx] = self.marks[user_id]
        return True

    def result(self) -> str | None:
        """None while ongoing, 'draw', or the winning mark."""
        for a, b, c in WIN_LINES:
            if self.board[a] and self.board[a] == self.board[b] == self.board[c]:
                return self.board[a]
        return "draw" if all(self.board) else None


class DuoTicTacToeButton(discord.ui.Button):
    def __init__(self, idx: int) -> None:
        super().__init__(style=discord.ButtonStyle.secondary, label="\u200b", row=idx // 3)
        self.idx = idx

    async def callback(self, interaction: discord.Interaction) -> None:
        view: DuoTicTacToeView = self.view  # type: ignore[assignment]
        game = view.game

        if interaction.user.id not in game.marks:
            await interaction.response.send_message("This isn't your game.", ephemeral=True)
            return
        if game.finished:
            await interaction.response.send_message("This game's already over.", ephemeral=True)
            return
        if interaction.user.id != game.turn_id:
            await interaction.response.send_message("Not your turn yet — hang tight.", ephemeral=True)
            return
        if not game.play(interaction.user.id, self.idx):
            await interaction.response.send_message("That spot's taken.", ephemeral=True)
            return

        mark = game.board[self.idx]
        self.label = mark
        self.style = discord.ButtonStyle.danger if mark == "❌" else discord.ButtonStyle.success
        self.disabled = True

        outcome = game.result()
        if outcome:
            game.finished = True
            for child in view.children:
                child.disabled = True  # type: ignore[attr-defined]
            status = "🤝 It's a draw!" if outcome == "draw" else f"🎉 <@{interaction.user.id}> wins!"
        else:
            game.turn_idx = 1 - game.turn_idx
            status = f"<@{game.turn_id}>'s turn"

        embed = discord.Embed(title="⭕❌ Tic-Tac-Toe", description=status, color=0xFF6FA5)
        await interaction.response.edit_message(embed=embed, view=view)

        other_msg = game.messages.get(game.other(interaction.user.id))
        if other_msg:
            try:
                await other_msg.edit(embed=embed, view=view)
            except discord.HTTPException:
                pass


class DuoTicTacToeView(discord.ui.View):
    def __init__(self, game: DuoTicTacToeGame) -> None:
        super().__init__(timeout=1800)
        self.game = game
        for i in range(9):
            self.add_item(DuoTicTacToeButton(i))

    async def on_timeout(self) -> None:
        for child in self.children:
            child.disabled = True  # type: ignore[attr-defined]
        for msg in self.game.messages.values():
            try:
                await msg.edit(view=self)
            except discord.HTTPException:
                pass


class DMGamesCog(commands.Cog):
    """Two-player games that work across two separate bot-DM channels —
    unlike a normal shared-channel game, each player gets their own message
    that stays in sync with the other's.
    """

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.rel_repo = RelationshipRepository()

    @app_commands.command(name="ttt", description="Play Tic-Tac-Toe with your partner across your DMs")
    async def ttt(self, interaction: discord.Interaction) -> None:
        partner_id = await self.rel_repo.get_partner_id(interaction.user.id)
        if not partner_id:
            await interaction.response.send_message(
                "You need an active partner (`/propose`) to play together.", ephemeral=True
            )
            return

        partner = self.bot.get_user(partner_id)
        if not partner:
            try:
                partner = await self.bot.fetch_user(partner_id)
            except discord.NotFound:
                partner = None
        if not partner:
            await interaction.response.send_message("Couldn't find your partner's account.", ephemeral=True)
            return

        game = DuoTicTacToeGame(interaction.user.id, partner_id)
        view = DuoTicTacToeView(game)
        embed = discord.Embed(
            title="⭕❌ Tic-Tac-Toe", description=f"<@{interaction.user.id}>'s turn", color=0xFF6FA5
        )

        await interaction.response.send_message(embed=embed, view=view)
        game.messages[interaction.user.id] = await interaction.original_response()

        try:
            game.messages[partner_id] = await partner.send(embed=embed, view=view)
        except discord.Forbidden:
            await interaction.followup.send(
                "Started your board, but I couldn't DM your partner — their DMs to me are closed.",
                ephemeral=True,
            )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(DMGamesCog(bot))
