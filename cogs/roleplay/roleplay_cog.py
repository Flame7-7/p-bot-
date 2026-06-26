from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from services.action_registry import get_all_actions
from services.roleplay_service import ActionResult, RoleplayService
from views.embeds import build_action_embed, build_achievement_embed, build_levelup_embed
from utils.logging import get_logger

logger = get_logger(__name__)

_service = RoleplayService()


async def _run(
    interaction: discord.Interaction,
    action_name: str,
    target: discord.Member | None,
) -> None:
    await interaction.response.defer()
    result = await _service.execute(
        action_name=action_name,
        author=interaction.user,  # type: ignore[arg-type]
        target=target,
        guild_id=interaction.guild_id or 0,
    )
    if isinstance(result, str):
        await interaction.followup.send(result, ephemeral=True)
        return

    from services.action_registry import get_action
    action = get_action(action_name)
    embed = build_action_embed(
        result,
        action.category if action else "social",
        interaction.user,  # type: ignore[arg-type]
        target,
    )
    await interaction.followup.send(embed=embed)

    if result.leveled_up:
        await interaction.followup.send(
            embed=build_levelup_embed(interaction.user, result.new_level)  # type: ignore[arg-type]
        )
    for ach_name in result.new_achievements:
        await interaction.followup.send(
            embed=build_achievement_embed(ach_name, interaction.user)  # type: ignore[arg-type]
        )


def _build_cog(bot: commands.Bot) -> None:
    """
    Attach all action commands directly to RoleplayCog as properly-typed
    methods. Each method is defined with a real function signature so
    discord.py's parameter extractor works on every Python version.
    """
    pass  # Commands are defined below as real methods


class RoleplayCog(commands.Cog, name="Roleplay"):
    """All 32 roleplay slash commands."""

    # ── Affection ─────────────────────────────────────────────────────────────

    @app_commands.command(name="hug", description="Give someone a warm hug")
    async def hug(self, interaction: discord.Interaction, target: discord.Member) -> None:
        await _run(interaction, "hug", target)

    @app_commands.command(name="pat", description="Pat someone on the head")
    async def pat(self, interaction: discord.Interaction, target: discord.Member) -> None:
        await _run(interaction, "pat", target)

    @app_commands.command(name="kiss", description="Kiss someone")
    async def kiss(self, interaction: discord.Interaction, target: discord.Member) -> None:
        await _run(interaction, "kiss", target)

    @app_commands.command(name="cuddle", description="Cuddle with someone")
    async def cuddle(self, interaction: discord.Interaction, target: discord.Member) -> None:
        await _run(interaction, "cuddle", target)

    @app_commands.command(name="poke", description="Poke someone")
    async def poke(self, interaction: discord.Interaction, target: discord.Member) -> None:
        await _run(interaction, "poke", target)

    @app_commands.command(name="boop", description="Boop someone on the nose")
    async def boop(self, interaction: discord.Interaction, target: discord.Member) -> None:
        await _run(interaction, "boop", target)

    @app_commands.command(name="headpat", description="Give someone a headpat")
    async def headpat(self, interaction: discord.Interaction, target: discord.Member) -> None:
        await _run(interaction, "headpat", target)

    @app_commands.command(name="nuzzle", description="Nuzzle someone affectionately")
    async def nuzzle(self, interaction: discord.Interaction, target: discord.Member) -> None:
        await _run(interaction, "nuzzle", target)

    @app_commands.command(name="snuggle", description="Snuggle with someone")
    async def snuggle(self, interaction: discord.Interaction, target: discord.Member) -> None:
        await _run(interaction, "snuggle", target)

    @app_commands.command(name="tackle", description="Tackle someone in excitement")
    async def tackle(self, interaction: discord.Interaction, target: discord.Member) -> None:
        await _run(interaction, "tackle", target)

    # ── Playful ───────────────────────────────────────────────────────────────

    @app_commands.command(name="slap", description="Slap someone playfully")
    async def slap(self, interaction: discord.Interaction, target: discord.Member) -> None:
        await _run(interaction, "slap", target)

    @app_commands.command(name="punch", description="Punch someone playfully")
    async def punch(self, interaction: discord.Interaction, target: discord.Member) -> None:
        await _run(interaction, "punch", target)

    @app_commands.command(name="kick", description="Kick someone playfully")
    async def kick(self, interaction: discord.Interaction, target: discord.Member) -> None:
        await _run(interaction, "kick", target)

    @app_commands.command(name="bite", description="Bite someone playfully")
    async def bite(self, interaction: discord.Interaction, target: discord.Member) -> None:
        await _run(interaction, "bite", target)

    @app_commands.command(name="lick", description="Lick someone")
    async def lick(self, interaction: discord.Interaction, target: discord.Member) -> None:
        await _run(interaction, "lick", target)

    @app_commands.command(name="tickle", description="Tickle someone")
    async def tickle(self, interaction: discord.Interaction, target: discord.Member) -> None:
        await _run(interaction, "tickle", target)

    @app_commands.command(name="pounce", description="Pounce on someone")
    async def pounce(self, interaction: discord.Interaction, target: discord.Member) -> None:
        await _run(interaction, "pounce", target)

    @app_commands.command(name="throw", description="Throw something at someone")
    async def throw(self, interaction: discord.Interaction, target: discord.Member) -> None:
        await _run(interaction, "throw", target)

    # ── Emotional (target optional) ────────────────────────────────────────────

    @app_commands.command(name="cry", description="Express that you're crying")
    async def cry(self, interaction: discord.Interaction, target: discord.Member | None = None) -> None:
        await _run(interaction, "cry", target)

    @app_commands.command(name="wave", description="Wave at someone")
    async def wave(self, interaction: discord.Interaction, target: discord.Member | None = None) -> None:
        await _run(interaction, "wave", target)

    @app_commands.command(name="blush", description="Blush")
    async def blush(self, interaction: discord.Interaction, target: discord.Member | None = None) -> None:
        await _run(interaction, "blush", target)

    @app_commands.command(name="smile", description="Smile warmly")
    async def smile(self, interaction: discord.Interaction, target: discord.Member | None = None) -> None:
        await _run(interaction, "smile", target)

    @app_commands.command(name="wink", description="Wink at someone")
    async def wink(self, interaction: discord.Interaction, target: discord.Member | None = None) -> None:
        await _run(interaction, "wink", target)

    @app_commands.command(name="dance", description="Dance")
    async def dance(self, interaction: discord.Interaction, target: discord.Member | None = None) -> None:
        await _run(interaction, "dance", target)

    @app_commands.command(name="laugh", description="Laugh out loud")
    async def laugh(self, interaction: discord.Interaction, target: discord.Member | None = None) -> None:
        await _run(interaction, "laugh", target)

    @app_commands.command(name="sigh", description="Sigh expressively")
    async def sigh(self, interaction: discord.Interaction, target: discord.Member | None = None) -> None:
        await _run(interaction, "sigh", target)

    # ── Social ────────────────────────────────────────────────────────────────

    @app_commands.command(name="highfive", description="High-five someone")
    async def highfive(self, interaction: discord.Interaction, target: discord.Member) -> None:
        await _run(interaction, "highfive", target)

    @app_commands.command(name="fistbump", description="Fist-bump someone")
    async def fistbump(self, interaction: discord.Interaction, target: discord.Member) -> None:
        await _run(interaction, "fistbump", target)

    @app_commands.command(name="handshake", description="Shake hands with someone")
    async def handshake(self, interaction: discord.Interaction, target: discord.Member) -> None:
        await _run(interaction, "handshake", target)

    @app_commands.command(name="bow", description="Bow respectfully")
    async def bow(self, interaction: discord.Interaction, target: discord.Member) -> None:
        await _run(interaction, "bow", target)

    @app_commands.command(name="stare", description="Stare at someone")
    async def stare(self, interaction: discord.Interaction, target: discord.Member) -> None:
        await _run(interaction, "stare", target)

    @app_commands.command(name="glare", description="Glare at someone")
    async def glare(self, interaction: discord.Interaction, target: discord.Member) -> None:
        await _run(interaction, "glare", target)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(RoleplayCog(bot))
    logger.info("RoleplayCog loaded with 32 commands")
