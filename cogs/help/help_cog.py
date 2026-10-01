from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

import discord
from discord import app_commands
from discord.ext import commands

from services.action_registry import get_all_actions
from utils.interactions import OwnedView, respond
from utils.logging import get_logger

logger = get_logger(__name__)

COLOR = 0xFF6FA5
PAGE_CHARS = 3600

# Display order; categories that have no visible commands are never shown.
CATEGORY_ORDER = [
    "Couple", "Couple Games", "Persona", "Roleplay", "Economy", "Games", "Movies",
    "Achievements", "Profile", "Habits", "Utility", "Custom", "Moderation", "Owner",
]
CATEGORY_EMOJI = {
    "Couple": "💕", "Couple Games": "🎮", "Persona": "💬", "Roleplay": "🎭", "Economy": "💰",
    "Games": "🎲", "Movies": "🎬", "Achievements": "🏆", "Profile": "👤", "Habits": "🌱",
    "Utility": "⚙️", "Custom": "🧩", "Moderation": "🛡️", "Owner": "👑",
}


@dataclass
class HelpEntry:
    usage: str
    description: str


@dataclass
class HelpCategory:
    name: str
    entries: list[HelpEntry] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def emoji(self) -> str:
        return CATEGORY_EMOJI.get(self.name, "📌")


def _param_usage(cmd: app_commands.Command) -> str:
    parts = []
    for p in cmd.parameters:
        parts.append(f"<{p.display_name}>" if p.required else f"[{p.display_name}]")
    return " ".join(parts)


def _ancestors(cmd) -> list:
    chain = [cmd]
    while getattr(chain[-1], "parent", None) is not None and not isinstance(chain[-1].parent, app_commands.CommandTree):
        chain.append(chain[-1].parent)
    return chain


def _category_of(cmd: app_commands.Command | app_commands.Group) -> str:
    for node in _ancestors(cmd):
        binding = getattr(node, "binding", None)
        category = getattr(binding, "help_category", None)
        if category:
            return category[1]
        module_cat = getattr(node, "module", "") or ""
        if "custom_commands" in module_cat:
            return "Custom"
    return "Utility"


def _visible(cmd, perms: discord.Permissions, in_guild: bool, nsfw_ok: bool, is_owner: bool) -> bool:
    if is_owner:
        return True
    for node in _ancestors(cmd):
        required = getattr(node, "default_permissions", None)
        if required is not None and not (perms.administrator or perms.is_superset(required)):
            return False
        if getattr(node, "guild_only", False) and not in_guild:
            return False
        if node.extras.get("nsfw_only") and not nsfw_ok:
            return False
    return True


def collect(
    bot: commands.Bot,
    *,
    guild: discord.Guild | None,
    perms: discord.Permissions,
    nsfw_ok: bool,
    is_owner: bool,
) -> dict[str, HelpCategory]:
    """Build the help catalogue from what is actually registered right now."""
    categories: dict[str, HelpCategory] = {}

    def add(name: str, usage: str, description: str) -> None:
        categories.setdefault(name, HelpCategory(name)).entries.append(HelpEntry(usage, description))

    tree_commands = list(bot.tree.get_commands())
    if guild is not None:
        tree_commands += bot.tree.get_commands(guild=guild)

    for top in tree_commands:
        if not _visible(top, perms, guild is not None, nsfw_ok, is_owner):
            continue
        leaves = [top] if isinstance(top, app_commands.Command) else list(top.walk_commands())
        for leaf in leaves:
            if not _visible(leaf, perms, guild is not None, nsfw_ok, is_owner):
                continue
            category = _category_of(leaf)
            if category == "Owner" and not is_owner:
                continue
            add(category, f"/{leaf.qualified_name} {_param_usage(leaf)}".strip(), leaf.description or "—")

    if is_owner:
        for cmd in bot.commands:  # mention-prefixed text commands, e.g. "@bot sync"
            add("Owner", f"@{bot.user.name if bot.user else 'bot'} {cmd.qualified_name}", cmd.help or cmd.short_doc or "Owner text command")

    roleplay = categories.get("Roleplay")
    if roleplay:
        grouped: dict[str, list[str]] = defaultdict(list)
        for action in get_all_actions().values():
            if action.category != "intimate":
                grouped[action.category].append(action.name)
        for cat, names in grouped.items():
            roleplay.notes.append(f"**{cat.title()}:** " + ", ".join(sorted(names)))

    for cat in categories.values():
        cat.entries.sort(key=lambda e: e.usage)
    return categories


def ordered(categories: dict[str, HelpCategory]) -> list[HelpCategory]:
    known = [categories[n] for n in CATEGORY_ORDER if n in categories]
    extra = [c for n, c in sorted(categories.items()) if n not in CATEGORY_ORDER]
    return known + extra


def build_pages(category: HelpCategory) -> list[discord.Embed]:
    lines = [f"`{e.usage}`\n└ {e.description}" for e in category.entries]
    if category.notes:
        lines.append("**Available actions** (type in the `action` field to search)\n" + "\n".join(category.notes))
    pages: list[str] = []
    current = ""
    for line in lines:
        if current and len(current) + len(line) + 2 > PAGE_CHARS:
            pages.append(current)
            current = ""
        current += ("\n\n" if current else "") + line
    pages.append(current or "Nothing here yet.")
    return [
        discord.Embed(title=f"{category.emoji} {category.name}", description=text, color=COLOR).set_footer(
            text=f"Page {i}/{len(pages)}" if len(pages) > 1 else "Pick another category from the menu"
        )
        for i, text in enumerate(pages, 1)
    ]


def build_overview(cats: list[HelpCategory]) -> discord.Embed:
    lines = [f"{c.emoji} **{c.name}** — {len(c.entries)} command{'s' if len(c.entries) != 1 else ''}" for c in cats]
    embed = discord.Embed(
        title="💕 Help",
        description="Choose a category from the menu below.\n\n" + "\n".join(lines),
        color=COLOR,
    )
    embed.set_footer(text="Only commands you can use right now are listed")
    return embed


class HelpView(OwnedView):
    def __init__(self, owner_id: int, cats: list[HelpCategory]) -> None:
        super().__init__([owner_id], timeout=240)
        self.cats = {c.name: c for c in cats}
        self.overview = build_overview(cats)
        self.pages: list[discord.Embed] = [self.overview]
        self.page = 0

        options = [discord.SelectOption(label="Overview", emoji="🏠", value="__overview__")]
        options += [discord.SelectOption(label=c.name, emoji=c.emoji, value=c.name, description=f"{len(c.entries)} commands") for c in cats[:24]]
        select = discord.ui.Select(placeholder="Browse a category…", options=options)
        select.callback = self._select  # type: ignore[method-assign]
        self.add_item(select)
        self._sync_buttons()

    def _sync_buttons(self) -> None:
        multi = len(self.pages) > 1
        self.prev_button.disabled = not multi or self.page == 0
        self.next_button.disabled = not multi or self.page >= len(self.pages) - 1

    async def _select(self, interaction: discord.Interaction) -> None:
        value = interaction.data["values"][0]  # type: ignore[index]
        self.pages = [self.overview] if value == "__overview__" else build_pages(self.cats[value])
        self.page = 0
        self._sync_buttons()
        await interaction.response.edit_message(embed=self.pages[0], view=self)

    @discord.ui.button(label="◀", style=discord.ButtonStyle.secondary, row=1)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.page = max(0, self.page - 1)
        self._sync_buttons()
        await interaction.response.edit_message(embed=self.pages[self.page], view=self)

    @discord.ui.button(label="▶", style=discord.ButtonStyle.secondary, row=1)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.page = min(len(self.pages) - 1, self.page + 1)
        self._sync_buttons()
        await interaction.response.edit_message(embed=self.pages[self.page], view=self)


class HelpCog(commands.Cog, name="Help"):
    help_category = ("⚙️", "Utility")

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="help", description="Browse everything this bot can do")
    async def help(self, interaction: discord.Interaction) -> None:
        channel = interaction.channel
        in_dm = isinstance(channel, discord.DMChannel) or interaction.guild is None
        nsfw_ok = in_dm or bool(getattr(channel, "is_nsfw", lambda: False)())
        try:
            cats = ordered(collect(
                self.bot,
                guild=interaction.guild,
                perms=interaction.permissions,
                nsfw_ok=nsfw_ok,
                is_owner=await self.bot.is_owner(interaction.user),
            ))
        except Exception:
            logger.exception("help generation failed")
            await respond(interaction, "I couldn't build the help menu right now — please try again.", ephemeral=True)
            return
        view = HelpView(interaction.user.id, cats)
        await interaction.response.send_message(embed=view.overview, view=view, ephemeral=True)
        view.message = await interaction.original_response()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(HelpCog(bot))
