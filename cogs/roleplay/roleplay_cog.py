from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from repositories.relationship_repository import RelationshipRepository
from repositories.roleplay_profile_repository import RoleplayProfileRepository
from services.action_registry import get_action, get_all_actions
from services.roleplay_service import RoleplayService
from utils.config import get_config
from utils.interactions import GENERIC_ERROR, respond, resolve_user, safe_dm
from utils.logging import get_logger
from views.embeds import build_achievement_embed, build_action_embed, build_levelup_embed

logger = get_logger(__name__)

INTIMATE = "intimate"


def _is_intimate(name: str) -> bool:
    action = get_action(name)
    return bool(action and action.category == INTIMATE)


def _autocomplete_for(intimate: bool):
    async def autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        current = current.lower().strip()
        matches = [
            a for a in get_all_actions().values()
            if (a.category == INTIMATE) == intimate and (current in a.name or current in a.description.lower())
        ]
        matches.sort(key=lambda a: (not a.name.startswith(current), a.name))
        return [
            app_commands.Choice(name=f"{a.name} — {a.description}"[:100], value=a.name)
            for a in matches[:25]
        ]
    return autocomplete


class RoleplayCog(commands.Cog, name="Roleplay"):
    """`/roleplay <action> [user]` — every action is defined in content/roleplay/*.md."""

    help_category = ("🎭", "Roleplay")

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.service = RoleplayService()
        self.rel_repo = RelationshipRepository()
        self.profile_repo = RoleplayProfileRepository()
        self._legacy: list[app_commands.Command] = []

    # ── lifecycle ────────────────────────────────────────────────────────────

    async def cog_load(self) -> None:
        if get_config().legacy_roleplay_commands:
            self._register_legacy_commands()

    async def cog_unload(self) -> None:
        for cmd in self._legacy:
            self.bot.tree.remove_command(cmd.name)
        self._legacy.clear()

    def _register_legacy_commands(self) -> None:
        """Optional `/hug`, `/kiss`, ... shortcuts (LEGACY_ROLEPLAY_COMMANDS=true).

        Built from the content files, so there is no per-command Python code.
        Discord allows 100 global slash commands; check the count before enabling.
        """
        for action in get_all_actions().values():
            if self.bot.tree.get_command(action.name):
                continue
            cmd = self._build_legacy(action.name, action.description)
            self.bot.tree.add_command(cmd)
            self._legacy.append(cmd)
        logger.info("registered %d legacy roleplay shortcuts", len(self._legacy))

    def _build_legacy(self, name: str, description: str) -> app_commands.Command:
        async def callback(interaction: discord.Interaction, target: discord.User | None = None) -> None:
            await self._dispatch(interaction, name, target)

        callback.__name__ = f"legacy_{name}"
        return app_commands.Command(name=name, description=(description or name)[:100], callback=callback)

    # ── commands ─────────────────────────────────────────────────────────────

    @app_commands.command(name="roleplay", description="Hug, kiss, cuddle, poke… pick an action (type to search)")
    @app_commands.describe(action="What to do", target="Who to do it to (in DMs it defaults to your partner)")
    @app_commands.autocomplete(action=_autocomplete_for(False))
    async def roleplay(self, interaction: discord.Interaction, action: str, target: discord.User | None = None) -> None:
        if _is_intimate(action) or get_action(action) is None:
            await respond(
                interaction,
                "I don't know that action — start typing in the `action` field to see the list.",
                ephemeral=True,
            )
            return
        await self._dispatch(interaction, action, target)

    @app_commands.command(
        name="intimate",
        description="Adults-only actions (needs /consent; DMs or age-restricted channels)",
        extras={"nsfw_only": True},
    )
    @app_commands.describe(action="What to do", target="Who to do it to (in DMs it defaults to your partner)")
    @app_commands.autocomplete(action=_autocomplete_for(True))
    async def intimate(self, interaction: discord.Interaction, action: str, target: discord.User | None = None) -> None:
        if not _is_intimate(action):
            await respond(interaction, "I don't know that action — start typing to search.", ephemeral=True)
            return
        if not await self._intimate_allowed(interaction):
            return
        await self._dispatch(interaction, action, target)

    # ── internals ────────────────────────────────────────────────────────────

    async def _intimate_allowed(self, interaction: discord.Interaction) -> bool:
        channel = interaction.channel
        in_dm = isinstance(channel, discord.DMChannel)
        nsfw_channel = bool(getattr(channel, "is_nsfw", lambda: False)()) and not in_dm
        if not (in_dm or nsfw_channel):
            await respond(interaction, "🔞 Use this in DMs or an age-restricted channel.", ephemeral=True)
            return False
        if not await self.profile_repo.is_verified(interaction.user.id):
            await respond(interaction, "🔒 Run `/consent` first to unlock this.", ephemeral=True)
            return False
        return True

    async def _dispatch(self, interaction: discord.Interaction, action_name: str, target: discord.User | None) -> None:
        try:
            await self._run(interaction, action_name, target)
        except Exception:
            logger.exception("roleplay action %s failed", action_name)
            await respond(interaction, GENERIC_ERROR, ephemeral=True)

    async def _run(self, interaction: discord.Interaction, action_name: str, target: discord.User | None) -> None:
        await interaction.response.defer()

        # In a DM there's nobody to @mention, so no target means "my partner".
        in_dm = isinstance(interaction.channel, discord.DMChannel)
        partner_id = await self.rel_repo.get_partner_id(interaction.user.id) if in_dm else None
        if in_dm and target is None and partner_id:
            target = await resolve_user(interaction.client, partner_id)

        result = await self.service.execute(
            action_name=action_name,
            author=interaction.user,  # type: ignore[arg-type]
            target=target,  # type: ignore[arg-type]
            guild_id=interaction.guild_id or 0,
        )
        if isinstance(result, str):
            await interaction.followup.send(result, ephemeral=True)
            return

        action = get_action(action_name)
        embed = build_action_embed(result, action.category if action else "social", interaction.user, target)  # type: ignore[arg-type]
        await interaction.followup.send(embed=embed)

        if result.leveled_up:
            await interaction.followup.send(embed=build_levelup_embed(interaction.user, result.new_level))  # type: ignore[arg-type]
        for ach_name in result.new_achievements:
            await interaction.followup.send(embed=build_achievement_embed(ach_name, interaction.user))  # type: ignore[arg-type]

        # Mirror into the partner's DM so it plays out for both of them.
        if in_dm and partner_id and target and target.id == partner_id:
            await safe_dm(target, embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(RoleplayCog(bot))
    logger.info("RoleplayCog loaded (%d actions)", len(get_all_actions()))
