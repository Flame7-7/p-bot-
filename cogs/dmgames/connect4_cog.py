from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from services.dm_mirror import get_dm_partner

COLS = 7
ROWS = 6


class Connect4Game:
    def __init__(self, p1_id: int, p2_id: int) -> None:
        self.order = [p1_id, p2_id]
        self.marks = {p1_id: "🔴", p2_id: "🟡"}
        # grid[col] is a bottom-to-top list of marks in that column
        self.grid: list[list[str]] = [[] for _ in range(COLS)]
        self.turn_idx = 0
        self.finished = False
        self.messages: dict[int, discord.Message] = {}

    @property
    def turn_id(self) -> int:
        return self.order[self.turn_idx]

    def other(self, user_id: int) -> int:
        return self.order[1] if user_id == self.order[0] else self.order[0]

    def drop(self, user_id: int, col: int) -> bool:
        if self.finished or user_id != self.turn_id or len(self.grid[col]) >= ROWS:
            return False
        self.grid[col].append(self.marks[user_id])
        return True

    def _cell(self, col: int, row: int) -> str | None:
        if 0 <= col < COLS and 0 <= row < len(self.grid[col]):
            return self.grid[col][row]
        return None

    def result(self) -> str | None:
        """None while ongoing, 'draw', or the winning mark."""
        directions = [(1, 0), (0, 1), (1, 1), (1, -1)]
        for col in range(COLS):
            for row in range(len(self.grid[col])):
                mark = self.grid[col][row]
                for dc, dr in directions:
                    if all(self._cell(col + dc * i, row + dr * i) == mark for i in range(4)):
                        return mark
        if all(len(c) == ROWS for c in self.grid):
            return "draw"
        return None

    def render(self) -> str:
        rows_out = []
        for row in reversed(range(ROWS)):
            cells = [self.grid[c][row] if row < len(self.grid[c]) else "⚪" for c in range(COLS)]
            rows_out.append("".join(cells))
        rows_out.append("1️⃣2️⃣3️⃣4️⃣5️⃣6️⃣7️⃣")
        return "\n".join(rows_out)


class Connect4Button(discord.ui.Button):
    def __init__(self, col: int) -> None:
        super().__init__(style=discord.ButtonStyle.secondary, label=str(col + 1), row=0)
        self.col = col

    async def callback(self, interaction: discord.Interaction) -> None:
        view: Connect4View = self.view  # type: ignore[assignment]
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
        if not game.drop(interaction.user.id, self.col):
            await interaction.response.send_message("That column's full.", ephemeral=True)
            return

        outcome = game.result()
        if outcome:
            game.finished = True
            for child in view.children:
                child.disabled = True  # type: ignore[attr-defined]
            status = "🤝 It's a draw!" if outcome == "draw" else f"🎉 <@{interaction.user.id}> wins!"
        else:
            game.turn_idx = 1 - game.turn_idx
            status = f"<@{game.turn_id}>'s turn"

        embed = discord.Embed(title="🔴🟡 Connect 4", description=f"{game.render()}\n\n{status}", color=0xFF6FA5)
        await interaction.response.edit_message(embed=embed, view=view)

        other_msg = game.messages.get(game.other(interaction.user.id))
        if other_msg:
            try:
                await other_msg.edit(embed=embed, view=view)
            except discord.HTTPException:
                pass


class Connect4View(discord.ui.View):
    def __init__(self, game: Connect4Game) -> None:
        super().__init__(timeout=1800)
        self.game = game
        for c in range(COLS):
            self.add_item(Connect4Button(c))

    async def on_timeout(self) -> None:
        for child in self.children:
            child.disabled = True  # type: ignore[attr-defined]
        for msg in self.game.messages.values():
            try:
                await msg.edit(view=self)
            except discord.HTTPException:
                pass


class Connect4Cog(commands.Cog):
    """Connect 4 with a synced board across both partners' DMs."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="connect4", description="Play Connect 4 with your partner across your DMs")
    async def connect4(self, interaction: discord.Interaction) -> None:
        partner = await get_dm_partner(interaction)
        if not partner:
            await interaction.response.send_message(
                "You need an active partner (`/propose`) to play together.", ephemeral=True
            )
            return

        game = Connect4Game(interaction.user.id, partner.id)
        view = Connect4View(game)
        embed = discord.Embed(
            title="🔴🟡 Connect 4", description=f"{game.render()}\n\n<@{interaction.user.id}>'s turn", color=0xFF6FA5
        )

        await interaction.response.send_message(embed=embed, view=view)
        game.messages[interaction.user.id] = await interaction.original_response()

        try:
            game.messages[partner.id] = await partner.send(embed=embed, view=view)
        except discord.Forbidden:
            await interaction.followup.send(
                "Started your board, but I couldn't DM your partner — their DMs to me are closed.",
                ephemeral=True,
            )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Connect4Cog(bot))
