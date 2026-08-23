from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from repositories.custom_command_repository import CustomCommandRepository
from services.custom_command_service import (
    COMMAND_NAME_RE,
    validate_name,
    validate_response,
    render_response,
)
from utils.cooldowns import check_cooldown, set_cooldown
from views.embeds import PaginatedViewMarkdown

MANAGEMENT_COMMANDS = {
    "help",
    "consent",
    "verify",
    "consentstatus",
    "addcommand",
    "editcommand",
    "removecommand",
    "customcommands",
}

MAX_COOLDOWN = 3600


async def _is_manager(interaction: discord.Interaction) -> bool:
    if not interaction.guild:
        return False
    if interaction.guild_permissions.administrator:
        return True
    # Keep bot-owner access useful even if the owner is not a server admin.
    return await interaction.client.is_owner(interaction.user) if interaction.client else False


class CustomCommandsCog(commands.Cog, name="Custom Commands"):
    """Guild-scoped self-service slash commands backed by SQLite."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.repo = CustomCommandRepository()
        self._loaded_guilds: set[int] = set()

    async def cog_load(self) -> None:
        # setup_hook runs before Discord has populated bot.guilds, so actual
        # guild registration is performed from on_ready below.
        pass

    async def _register(self, command, guild_id: int) -> None:
        guild = discord.Object(id=guild_id)
        self.bot.tree.add_command(command, guild=guild, override=True)

    async def _unregister(self, name: str, guild_id: int) -> None:
        guild = discord.Object(id=guild_id)
        self.bot.tree.remove_command(name, guild=guild)

    def _name_available(self, name: str, guild_id: int) -> bool:
        normalized = name.lower()
        if normalized in MANAGEMENT_COMMANDS:
            return False

        # Global commands such as /hug, /profile, /settings, etc. are also
        # unavailable to custom commands. Guild-specific commands are checked
        # separately.
        if any(cmd.name == normalized for cmd in self.bot.tree.get_commands()):
            return False
        guild = discord.Object(id=guild_id)
        if any(cmd.name == normalized for cmd in self.bot.tree.get_commands(guild=guild)):
            return False
        return True

    def _build_dynamic_command(self, stored) -> app_commands.Command:
        command_id = stored.id
        name = stored.name
        description = stored.description[:100] or "Custom server command"

        @app_commands.describe(target="Optional member target for this command")
        async def callback(
            interaction: discord.Interaction,
            target: discord.Member | None = None,
        ) -> None:
            current = await self.repo.get(interaction.guild_id or 0, name)
            if not current or not current.enabled:
                await interaction.response.send_message(
                    "❌ This custom command is no longer available.", ephemeral=True
                )
                return

            if current.cooldown_seconds:
                key = f"custom:{current.guild_id}:{current.id}"
                remaining = check_cooldown(interaction.user.id, key)
                if remaining:
                    await interaction.response.send_message(
                        f"⏳ Cooldown! Try again in **{remaining}s**.", ephemeral=True
                    )
                    return

            try:
                message = render_response(current, interaction, target)
            except ValueError as exc:
                await interaction.response.send_message(
                    f"❌ This command's response is invalid: {exc}", ephemeral=True
                )
                return

            if current.cooldown_seconds:
                set_cooldown(
                    interaction.user.id,
                    f"custom:{current.guild_id}:{current.id}",
                    current.cooldown_seconds,
                )

            await interaction.response.send_message(
                message,
                allowed_mentions=discord.AllowedMentions(
                    users=True, roles=False, everyone=False
                ),
            )

        callback.__name__ = f"custom_command_{command_id}"
        callback.__qualname__ = callback.__name__
        return app_commands.Command(
            name=name,
            description=description,
            callback=callback,
        )

    async def _load_guild(self, guild_id: int, sync: bool = True) -> int:
        commands_to_load = await self.repo.list_for_guild(guild_id)
        loaded = 0

        for stored in commands_to_load:
            # A stale DB row should not break the entire guild. Existing bot
            # commands always win over a custom command with the same name.
            if not self._name_available(stored.name, guild_id):
                existing = self.bot.tree.get_command(
                    stored.name, guild=discord.Object(id=guild_id)
                )
                if existing and getattr(existing, "callback", None):
                    continue
                continue
            await self._register(self._build_dynamic_command(stored), guild_id)
            loaded += 1

        if sync:
            await self.bot.tree.sync(guild=discord.Object(id=guild_id))
        self._loaded_guilds.add(guild_id)
        return loaded

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        # On reconnect Discord may fire on_ready again. Only initialize each
        # guild once during this process.
        for guild in self.bot.guilds:
            if guild.id in self._loaded_guilds:
                continue
            try:
                loaded = await self._load_guild(guild.id, sync=True)
                if loaded:
                    self.bot.get_cog("Custom Commands")
                    # Logging is intentionally omitted here to avoid noisy
                    # reconnect logs.
            except Exception:
                # A guild sync failure should not prevent other guilds from
                # working; the DB remains the source of truth.
                continue

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild) -> None:
        try:
            await self._load_guild(guild.id, sync=True)
        except Exception:
            pass

    @app_commands.command(name="addcommand", description="Create a server custom slash command")
    @app_commands.describe(
        name="Lowercase command name, e.g. cuddleme",
        response="Response text. Placeholders: {user}, {mention}, {target}, {target_mention}, {server}",
        description="Short description shown in Discord's command menu",
        category="Category used when listing custom commands",
        cooldown="Per-user cooldown in seconds (0-3600)",
        requires_target="Require a member target when the command is used",
    )
    async def add_command(
        self,
        interaction: discord.Interaction,
        name: str,
        response: str,
        description: str = "Custom server command",
        category: str = "custom",
        cooldown: app_commands.Range[int, 0, MAX_COOLDOWN] = 0,
        requires_target: bool = False,
    ) -> None:
        if not await _is_manager(interaction):
            await interaction.response.send_message(
                "❌ You need Administrator permission (or bot-owner access) to manage custom commands.",
                ephemeral=True,
            )
            return
        if not interaction.guild_id:
            await interaction.response.send_message(
                "❌ Custom commands can only be created inside a server.", ephemeral=True
            )
            return

        name = name.lower().strip()
        category = category.strip().lower()[:50]
        description = description.strip()[:100] or "Custom server command"

        validation = validate_name(name)
        if not validation.ok:
            await interaction.response.send_message(f"❌ {validation.error}", ephemeral=True)
            return
        validation = validate_response(response)
        if not validation.ok:
            await interaction.response.send_message(f"❌ {validation.error}", ephemeral=True)
            return
        if not self._name_available(name, interaction.guild_id):
            await interaction.response.send_message(
                f"❌ `/{name}` conflicts with an existing command or reserved command name.",
                ephemeral=True,
            )
            return
        if await self.repo.get(interaction.guild_id, name):
            await interaction.response.send_message(
                f"❌ `/{name}` already exists in this server.", ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)
        try:
            stored = await self.repo.create(
                interaction.guild_id,
                name,
                response,
                description,
                category or "custom",
                interaction.user.id,
                int(cooldown),
                requires_target,
            )
            await self._register(self._build_dynamic_command(stored), interaction.guild_id)
            await self.bot.tree.sync(guild=discord.Object(id=interaction.guild_id))
        except Exception:
            # Roll back the DB row if registration fails.
            await self.repo.delete(stored.id) if "stored" in locals() else None
            await interaction.followup.send(
                "❌ I couldn't register that command. Nothing was changed.", ephemeral=True
            )
            return

        target_note = "target required" if requires_target else "target optional"
        await interaction.followup.send(
            f"✅ Created `/{name}` in **{interaction.guild.name}** "
            f"({target_note}, cooldown `{int(cooldown)}s`).",
            ephemeral=True,
        )

    @app_commands.command(name="editcommand", description="Edit a server custom slash command")
    @app_commands.describe(
        name="Existing custom command name",
        response="New response text",
        description="New Discord command description",
        category="New category",
        cooldown="New per-user cooldown in seconds",
        requires_target="Whether a target is required",
        enabled="Whether the command is enabled",
    )
    async def edit_command(
        self,
        interaction: discord.Interaction,
        name: str,
        response: str | None = None,
        description: str | None = None,
        category: str | None = None,
        cooldown: app_commands.Range[int, 0, MAX_COOLDOWN] | None = None,
        requires_target: bool | None = None,
        enabled: bool | None = None,
    ) -> None:
        if not await _is_manager(interaction) or not interaction.guild_id:
            await interaction.response.send_message(
                "❌ You need Administrator permission (or bot-owner access) in a server.",
                ephemeral=True,
            )
            return

        name = name.lower().strip()
        current = await self.repo.get(interaction.guild_id, name)
        if not current:
            await interaction.response.send_message(
                f"❌ Custom command `/{name}` was not found.", ephemeral=True
            )
            return

        original_values = {
            "response": current.response,
            "description": current.description,
            "category": current.category,
            "cooldown_seconds": current.cooldown_seconds,
            "requires_target": current.requires_target,
            "enabled": current.enabled,
        }
        changes: dict = {}
        if response is not None:
            validation = validate_response(response)
            if not validation.ok:
                await interaction.response.send_message(
                    f"❌ {validation.error}", ephemeral=True
                )
                return
            changes["response"] = response
        if description is not None:
            changes["description"] = description.strip()[:100] or "Custom server command"
        if category is not None:
            changes["category"] = category.strip().lower()[:50] or "custom"
        if cooldown is not None:
            changes["cooldown_seconds"] = int(cooldown)
        if requires_target is not None:
            changes["requires_target"] = requires_target
        if enabled is not None:
            changes["enabled"] = enabled

        if not changes:
            await interaction.response.send_message(
                "❌ Provide at least one field to change.", ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        # Remove the old guild registration first so an updated description
        # or enabled state cannot leave a stale Discord definition behind.
        await self._unregister(name, interaction.guild_id)
        try:
            updated = await self.repo.update(current.id, **changes)
            if not updated:
                raise RuntimeError("custom command disappeared")
            if updated.enabled:
                await self._register(self._build_dynamic_command(updated), interaction.guild_id)
            await self.bot.tree.sync(guild=discord.Object(id=interaction.guild_id))
        except Exception:
            # Discord is the published state, so restore both the database
            # row and the previous in-memory definition when sync fails.
            try:
                await self.repo.update(current.id, **original_values)
            except Exception:
                pass
            try:
                await self._unregister(name, interaction.guild_id)
                await self._register(self._build_dynamic_command(current), interaction.guild_id)
                await self.bot.tree.sync(guild=discord.Object(id=interaction.guild_id))
            except Exception:
                pass
            await interaction.followup.send(
                "❌ I couldn't update the Discord command; the previous definition was restored.",
                ephemeral=True,
            )
            return

        await interaction.followup.send(
            f"✅ Updated `/{name}`.", ephemeral=True
        )

    @app_commands.command(name="removecommand", description="Delete a server custom slash command")
    @app_commands.describe(name="Existing custom command name")
    async def remove_command(self, interaction: discord.Interaction, name: str) -> None:
        if not await _is_manager(interaction) or not interaction.guild_id:
            await interaction.response.send_message(
                "❌ You need Administrator permission (or bot-owner access) in a server.",
                ephemeral=True,
            )
            return

        name = name.lower().strip()
        current = await self.repo.get(interaction.guild_id, name)
        if not current:
            await interaction.response.send_message(
                f"❌ Custom command `/{name}` was not found.", ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)
        await self._unregister(name, interaction.guild_id)
        try:
            await self.bot.tree.sync(guild=discord.Object(id=interaction.guild_id))
            await self.repo.delete(current.id)
        except Exception:
            try:
                await self._register(self._build_dynamic_command(current), interaction.guild_id)
                await self.bot.tree.sync(guild=discord.Object(id=interaction.guild_id))
            except Exception:
                pass
            await interaction.followup.send(
                "❌ I couldn't remove the Discord command; the previous definition was restored.",
                ephemeral=True,
            )
            return

        await interaction.followup.send(f"🗑️ Removed `/{name}`.", ephemeral=True)

    @app_commands.command(name="customcommands", description="List this server's custom slash commands")
    async def list_commands(self, interaction: discord.Interaction) -> None:
        if not interaction.guild_id:
            await interaction.response.send_message(
                "❌ Custom commands are server-specific.", ephemeral=True
            )
            return

        commands_in_guild = await self.repo.list_for_guild(
            interaction.guild_id, include_disabled=True
        )
        if not commands_in_guild:
            await interaction.response.send_message(
                "🧩 This server has no custom commands yet.", ephemeral=True
            )
            return

        pages: list[str] = []
        chunk_size = 10
        for offset in range(0, len(commands_in_guild), chunk_size):
            chunk = commands_in_guild[offset : offset + chunk_size]
            lines = [f"# 🧩 Custom Commands — {interaction.guild.name}\\n"]
            for command in chunk:
                status = "🟢 enabled" if command.enabled else "🔴 disabled"
                target = "target required" if command.requires_target else "target optional"
                lines.append(
                    f"## `/{command.name}`\\n"
                    f"{command.description}\\n"
                    f"- Category: `{command.category}` • {status} • {target} • "
                    f"cooldown `{command.cooldown_seconds}s`"
                )
            pages.append("\\n\\n".join(lines))


        await interaction.response.send_message(
            content=pages[0],
            view=PaginatedViewMarkdown(pages),
            ephemeral=True,
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(CustomCommandsCog(bot))
