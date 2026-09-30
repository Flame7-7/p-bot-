from __future__ import annotations

import random

import discord
from discord import app_commands
from discord.ext import commands

from services.dm_mirror import get_dm_partner

QUESTIONS = [
    ("Always be 10 minutes late", "Always be 20 minutes early"),
    ("Only communicate through memes for a week", "Only communicate through voice notes for a week"),
    ("Go on a spontaneous weekend trip", "Have a fully planned dream vacation"),
    ("Cook a meal together every night", "Order in and watch a show every night"),
    ("Have a rewind button on your relationship", "Have a fast-forward button"),
    ("Know how you two met (in detail) as a movie", "Not know and just enjoy it as it happens"),
    ("Always have the last word", "Never need the last word"),
    ("Celebrate every anniversary big", "Keep it low-key every year"),
    ("Text first, always", "Wait for them to text first"),
    ("Share a single social media account", "Never post about each other at all"),
    ("Have unlimited travel but no savings", "Have great savings but rarely travel"),
    ("Fight it out immediately", "Sleep on it and talk in the morning"),
    ("Have a couple's playlist you both add to", "Keep your music tastes totally separate"),
    ("Get matching tattoos", "Get matching pet names instead"),
    ("Live 5 minutes from each other's family", "Live 5 hours away from both"),
]


class WYRView(discord.ui.View):
    def __init__(self, option_a: str, option_b: str) -> None:
        super().__init__(timeout=600)
        self.option_a = option_a
        self.option_b = option_b
        self.choices: dict[int, str] = {}
        self.messages: dict[int, discord.Message] = {}

        self.btn_a = discord.ui.Button(label=f"A) {option_a}"[:80], style=discord.ButtonStyle.primary)
        self.btn_b = discord.ui.Button(label=f"B) {option_b}"[:80], style=discord.ButtonStyle.secondary)
        self.btn_a.callback = self._make_callback("A")
        self.btn_b.callback = self._make_callback("B")
        self.add_item(self.btn_a)
        self.add_item(self.btn_b)

    def _make_callback(self, choice: str):
        async def callback(interaction: discord.Interaction) -> None:
            if interaction.user.id not in self.messages:
                await interaction.response.send_message("This isn't your question.", ephemeral=True)
                return
            if interaction.user.id in self.choices:
                await interaction.response.send_message("You already answered.", ephemeral=True)
                return
            self.choices[interaction.user.id] = choice
            await interaction.response.send_message(f"You picked **{choice}**. Waiting on them...", ephemeral=True)
            if len(self.choices) == len(self.messages):
                await self._reveal()

        return callback

    async def _reveal(self) -> None:
        ids = list(self.messages.keys())
        lines = []
        for uid in ids:
            lines.append(f"<@{uid}> picked **{self.choices[uid]}**")
        matched = len(set(self.choices.values())) == 1
        status = "💞 You two agree!" if matched else "🤔 Different picks — talk it out!"

        embed = discord.Embed(
            title="🤍 Would You Rather — Results",
            description=f"**A)** {self.option_a}\n**B)** {self.option_b}\n\n" + "\n".join(lines) + f"\n\n{status}",
            color=0xFF6FA5,
        )
        self.btn_a.disabled = True
        self.btn_b.disabled = True
        for msg in self.messages.values():
            try:
                await msg.edit(embed=embed, view=self)
            except discord.HTTPException:
                pass

    async def on_timeout(self) -> None:
        self.btn_a.disabled = True
        self.btn_b.disabled = True
        for msg in self.messages.values():
            try:
                await msg.edit(view=self)
            except discord.HTTPException:
                pass


class WYRCog(commands.Cog):
    """Would You Rather, synced across both partners' DMs."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="wyr", description="Would You Rather — answer together with your partner in DMs")
    async def wyr(self, interaction: discord.Interaction) -> None:
        partner = await get_dm_partner(interaction)
        if not partner:
            await interaction.response.send_message(
                "You need an active partner (`/propose`) to play together.", ephemeral=True
            )
            return

        option_a, option_b = random.choice(QUESTIONS)
        view = WYRView(option_a, option_b)
        embed = discord.Embed(
            title="🤍 Would You Rather...",
            description=f"**A)** {option_a}\n**B)** {option_b}\n\nBoth of you: pick one — results reveal once you both answer.",
            color=0xFF6FA5,
        )

        await interaction.response.send_message(embed=embed, view=view)
        view.messages[interaction.user.id] = await interaction.original_response()

        try:
            view.messages[partner.id] = await partner.send(embed=embed, view=view)
        except discord.Forbidden:
            await interaction.followup.send(
                "Sent your side, but I couldn't DM your partner — their DMs to me are closed.", ephemeral=True
            )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(WYRCog(bot))
