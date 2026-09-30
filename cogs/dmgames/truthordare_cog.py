from __future__ import annotations

import random

import discord
from discord import app_commands
from discord.ext import commands

from services.dm_mirror import get_dm_partner

TRUTHS = [
    "What's a habit of mine that secretly makes you smile?",
    "What's a small thing I do that you've never told me you love?",
    "What's one thing you'd want us to do more of together?",
    "What's a memory of us you replay in your head?",
    "What's something you were nervous to tell me early on?",
    "What's your favorite thing about how we met?",
    "What's one thing you want to do together in the next year?",
    "What's a song that reminds you of me?",
    "What's the most 'us' thing we've ever done?",
    "What's something I do that instantly improves your mood?",
]

DARES = [
    "Send a voice note singing the chorus of our song.",
    "Send the most recent photo in your gallery, no skipping.",
    "Text me a compliment using only emojis.",
    "Send a selfie with your current face, right now.",
    "Write a 2-line poem about me and send it.",
    "Tell me your day in one voice note, dramatic narrator voice.",
    "Send a screenshot of your phone's home screen.",
    "Describe your perfect date with me in exactly 10 words.",
    "Send me a gif of exactly how you feel right now.",
    "Text me the nickname you'd give us as a couple if we were famous.",
]


class TruthOrDareCog(commands.Cog):
    """Sends a truth or dare prompt straight to your partner's DM."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="truthordare", description="Send your partner a truth or dare, right in their DMs")
    @app_commands.describe(mode="Truth (a question) or Dare (a small challenge)")
    @app_commands.choices(
        mode=[app_commands.Choice(name="Truth", value="truth"), app_commands.Choice(name="Dare", value="dare")]
    )
    async def truthordare(self, interaction: discord.Interaction, mode: app_commands.Choice[str]) -> None:
        partner = await get_dm_partner(interaction)
        if not partner:
            await interaction.response.send_message(
                "You need an active partner (`/propose`) to play together.", ephemeral=True
            )
            return

        prompt = random.choice(TRUTHS if mode.value == "truth" else DARES)
        label = "💭 Truth" if mode.value == "truth" else "🎯 Dare"

        embed = discord.Embed(
            title=f"{label} from {interaction.user.display_name}",
            description=prompt,
            color=0xFF6FA5,
        )
        embed.set_footer(text="Just reply here — it'll reach them.")

        try:
            await partner.send(embed=embed)
        except discord.Forbidden:
            await interaction.response.send_message(
                "Couldn't reach your partner's DMs — their DMs to me are closed.", ephemeral=True
            )
            return

        await interaction.response.send_message(f"Sent a **{mode.name}** to your partner: *{prompt}*", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TruthOrDareCog(bot))
