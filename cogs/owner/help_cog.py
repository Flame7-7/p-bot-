from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from services.action_registry import get_by_category
from views.embeds import PaginatedView

DISCORD_BLURPLE = 0x5865F2
DISCORD_GOLD = 0xFEE75C
NOFAP_COLOR = 0xE67E22
MOVIE_COLOR = 0x01B4E4

# Only the SFW categories are documented/browsable here on purpose --
# Explicit response text is not reproduced in help; shared roleplay infrastructure still applies to every registered action.
CATEGORY_INFO = {
    "affection": ("Affection", "💕", 0xF47FFF),
    "playful":   ("Playful", "😄", 0xFFB347),
    "emotional": ("Emotional", "💭", 0x58B6FF),
    "social":    ("Social", "🤝", 0x77D958),
}


def _footer(embed: discord.Embed) -> discord.Embed:
    embed.timestamp = discord.utils.utcnow()
    return embed


class HelpCog(commands.Cog, name="Help"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="help", description="View all bot commands")
    async def help(self, interaction: discord.Interaction) -> None:
        pages: list[discord.Embed] = []

        # ── Page 1: Getting Started ─────────────────────────────────────
        overview = discord.Embed(
            title="🌸 Roleplay Bot",
            description=(
                "A social roleplay bot with relationships, achievements, leveling, and "
                "leaderboards!"
            ),
            color=DISCORD_BLURPLE,
        )
        overview.add_field(
            name="🚀 Getting Started",
            value=(
                "`/help` -- this menu.\n"
                "`/consent` -- set your role (Male / Female / Non-Binary) and confirm the "
                "community guidelines. Optional for most roleplay commands, but unlocks "
                "gendered wording (`he`/`she`/`they`) and is required by anything using the "
                "`requires_verification()` check.\n"
                "`/verify` -- alias for `/consent`.\n"
                "`/consentstatus` -- check your current role/consent without opening the setup flow."
            ),
            inline=False,
        )
        overview.add_field(
            name="Browse by Category",
            value=(
                "💕 **Affection** -- show love and care\n"
                "😄 **Playful** -- have fun together\n"
                "💭 **Emotional** -- express yourself\n"
                "🤝 **Social** -- greet and interact"
            ),
            inline=True,
        )
        overview.add_field(
            name="Other Features",
            value=(
                "👤 Profile & Stats · 💑 Relationships\n"
                "🏆 Achievements · 📊 Leaderboards\n"
                "🎁 Economy · ⚙️ Settings\n"
                "🔥 No-Fap Tracker · 🎬 Movies"
            ),
            inline=True,
        )
        overview.add_field(
            name="⚡ Quick Start",
            value="`/consent` → `/hug @user` · `/profile` · `/propose @user` · `/top`",
            inline=False,
        )
        pages.append(_footer(overview))

        # ── Pages 2-5: Roleplay commands, one page per SFW category ────
        for cat_key, (cat_label, emoji, color) in CATEGORY_INFO.items():
            actions = get_by_category(cat_key)
            if not actions:
                continue

            embed = discord.Embed(
                title=f"{emoji} {cat_label} Commands",
                description=(
                    f"Browse all {cat_label.lower()} roleplay actions. Use `/consent` first "
                    f"if you want responses to use your chosen pronouns -- it isn't required "
                    f"to run these."
                ),
                color=color,
            )
            for action in actions:
                note = " *(target optional)*" if not action.requires_target else ""
                embed.add_field(
                    name=f"/{action.name} @target{note}",
                    value=(
                        f"{action.description}\n"
                        f"💕 `+{action.affection_gain}` • ✨ `+{action.xp_gain} XP` "
                        f"• ⏱️ `{action.cooldown_seconds}s`"
                    ),
                    inline=False,
                )
            pages.append(_footer(embed))

        # ── Page: Sync Commands ─────────────────────────────────────────
        sync_embed = discord.Embed(
            title="🔁 Sync Commands",
            description=(
                "Syncing pushes this bot's slash command definitions to Discord, so "
                "new/changed commands actually show up when you type `/`. You only need "
                "this after the bot's code changes -- not for normal use."
            ),
            color=DISCORD_BLURPLE,
        )
        sync_embed.add_field(
            name="Command",
            value=(
                "`!sync` *(owner only, text command, mention-prefixed)*\n"
                "- Registers every currently-loaded slash command with Discord globally.\n"
                "- Can take up to an hour to propagate globally after running it."
            ),
            inline=False,
        )
        sync_embed.add_field(name="Requirements", value="Must be run by the bot owner.", inline=False)
        sync_embed.add_field(name="Example", value="`@RoleplayBot sync`", inline=False)
        pages.append(_footer(sync_embed))

        # ── Page: GIF Commands ───────────────────────────────────────────
        gif_embed = discord.Embed(
            title="🎬 GIF Commands",
            description=(
                "Every roleplay command above automatically attaches a random GIF from that "
                "action's category (falls back to a Tenor search if the library has none saved)."
            ),
            color=DISCORD_BLURPLE,
        )
        gif_embed.add_field(
            name="Managing the GIF Library (owner only)",
            value=(
                "`/gif add <category> <urls>` -- add one or more direct `.gif` links "
                "(space/comma/newline separated). Autocompletes the category field.\n"
                "`/gif list <category>` -- see how many GIFs a category has and preview the URLs.\n"
                "`!addgif <category> <url>` -- add a single GIF via text command.\n"
                "`!addgifs <category> <name_prefix>` + attachments -- bulk add up to 25 GIFs/"
                "images/videos.\n"
                "`!addgifsfromlist <category> <name_prefix>` + a `.txt` attachment -- bulk add "
                "URLs from a text file, one per line."
            ),
            inline=False,
        )
        gif_embed.add_field(
            name="Notes",
            value=(
                "Categories match the roleplay action names (`hug`, `pat`, `slap`, etc.).\n"
                "No arguments are required to trigger a GIF -- it's automatic on every "
                "roleplay command."
            ),
            inline=False,
        )
        pages.append(_footer(gif_embed))

        # ── Page: Custom Commands ────────────────────────────────────────
        custom_embed = discord.Embed(
            title="🧩 Custom Commands",
            description=(
                "Server administrators (or the bot owner) can create database-backed custom "
                "slash commands without editing Python source code. Commands are stored per "
                "server and survive bot restarts."
            ),
            color=DISCORD_BLURPLE,
        )
        custom_embed.add_field(
            name="Management",
            value=(
                "`/addcommand` -- create a custom command with a response, description, "
                "category, cooldown, and optional target requirement.\n"
                "`/editcommand` -- change an existing custom command or disable/enable it.\n"
                "`/removecommand` -- delete a custom command.\n"
                "`/customcommands` -- list this server's custom commands."
            ),
            inline=False,
        )
        custom_embed.add_field(
            name="Response placeholders",
            value=(
                "`{user}` / `{author}` -- caller's display name\n"
                "`{mention}` -- caller's mention\n"
                "`{target}` / `{target_mention}` -- selected member\n"
                "`{server}` -- server name\n"
                "Unsupported placeholders are rejected on create/edit."
            ),
            inline=False,
        )
        custom_embed.add_field(
            name="Cooldowns & targets",
            value=(
                "Each custom command can have a 0-3600 second per-user cooldown, independent "
                "per user and per command. Mark a command as requiring a target when it should "
                "always receive a member."
            ),
            inline=False,
        )
        custom_embed.add_field(
            name="Example",
            value=(
                "`/addcommand name:welcome response:Welcome {target} to {server}! "
                "description:Welcome someone category:social cooldown:10 requires_target:True`\n\n"
                "Custom command names cannot replace built-in commands such as `/help`, `/hug`, "
                "or `/profile`, and are registered only in the server where they were created."
            ),
            inline=False,
        )
        pages.append(_footer(custom_embed))

        # ── Page: Configuration ─────────────────────────────────────────
        config_embed = discord.Embed(title="⚙️ Configuration", color=DISCORD_BLURPLE)
        config_embed.add_field(
            name="Your Role & Consent",
            value=(
                "`/consent` -- opens role selection (Male / Female / Non-Binary), then asks "
                "you to confirm. If you've already set up, this shows your current status "
                "with buttons to **Change Role** or **Reset** instead.\n"
                "`/consentstatus` -- read-only view of your current role/consent.\n"
                "Changing your role always clears consent, so you re-confirm the guidelines "
                "after switching."
            ),
            inline=False,
        )
        config_embed.add_field(
            name="Resetting",
            value=(
                "Use the **Reset** button on `/consent` -- this deletes your saved "
                "role/consent entirely, back to the \"not started\" state."
            ),
            inline=False,
        )
        config_embed.add_field(
            name="What Happens on Bot Restart",
            value=(
                "Your role/consent is stored in the bot's SQLite database, not in memory, so "
                "it **survives restarts**."
            ),
            inline=False,
        )
        config_embed.add_field(
            name="/settings",
            value=(
                "Separate from `/consent` -- toggles whether others can target you with "
                "roleplay commands, and whether you appear on leaderboards."
            ),
            inline=False,
        )
        pages.append(_footer(config_embed))

        # ── Page: Cooldowns ──────────────────────────────────────────────
        cooldown_embed = discord.Embed(
            title="⏱️ Cooldowns",
            description=(
                "Registered roleplay actions have a per-user, per-command cooldown (shown on "
                "each category page where applicable) to stop spam. `/consent`'s role-change "
                "buttons have their own short 10s cooldown for the same reason."
            ),
            color=DISCORD_BLURPLE,
        )
        cooldown_embed.add_field(
            name="What you'll see",
            value="If you're on cooldown, the bot replies with how long is left, e.g. \"⏳ Cooldown! Try again in **12s**.\"",
            inline=False,
        )
        cooldown_embed.add_field(
            name="What's *not* on cooldown",
            value=(
                "`/help`, `/consent`, `/consentstatus`, `/profile`, `/settings`, and admin/mod "
                "commands are never rate-limited by the roleplay cooldown system -- only the "
                "roleplay action commands are."
            ),
            inline=False,
        )
        pages.append(_footer(cooldown_embed))

        # ── Page: Other utility commands ─────────────────────────────────
        other_embed = discord.Embed(title="🛠️ Other Commands", color=DISCORD_BLURPLE)
        other_embed.add_field(name="👤 Profile", value="`/profile [user]` `/setbio` `/stats [user]`", inline=False)
        other_embed.add_field(name="💑 Relationships", value="`/propose @user` `/partner` `/breakup` `/anniversary`", inline=False)
        other_embed.add_field(name="🏆 Achievements", value="`/achievements [user]`", inline=False)
        other_embed.add_field(name="📊 Leaderboard", value="`/top affection|level|interactions`", inline=False)
        other_embed.add_field(name="🎁 Economy", value="`/daily`", inline=False)
        other_embed.add_field(name="⚙️ Settings", value="`/settings`", inline=False)
        other_embed.add_field(
            name="🎮 Games",
            value="`/rps` `/rps_pvp` `/coinflip` `/slots` `/trivia` `/roll` `/guess`",
            inline=False,
        )
        pages.append(_footer(other_embed))

        # ── Page: No-Fap Tracker ─────────────────────────────────────────
        nofap_embed = discord.Embed(
            title="🔥 No-Fap Tracker",
            description=(
                "A personal streak tracker, completely separate from the roleplay/consent "
                "system -- just a self-improvement tool. Only you can see and manage your "
                "own streak."
            ),
            color=NOFAP_COLOR,
        )
        nofap_embed.add_field(name="/nofap start", value="Begin tracking your streak. Does nothing if you already have one running.", inline=False)
        nofap_embed.add_field(name="/nofap status", value="See your current streak length, start date, and last reset.", inline=False)
        nofap_embed.add_field(name="/nofap stats", value="See your best-ever streak, total resets, and how long you've been tracking.", inline=False)
        nofap_embed.add_field(
            name="/nofap reset",
            value=(
                "Record a relapse. Asks for confirmation first, then banks your finished "
                "streak as a new best (if it is one) and starts a fresh streak from now."
            ),
            inline=False,
        )
        nofap_embed.set_footer(text="Your streak survives bot restarts -- stored in the same SQLite database as everything else.")
        pages.append(_footer(nofap_embed))

        # ── Page: Movie Recommendations ────────────────────────────────────
        movie_embed = discord.Embed(
            title="🎬 Movie Recommendations",
            color=MOVIE_COLOR,
        )
        movie_embed.add_field(
            name="/movie recommend [genre]",
            value=(
                "Get a random, reasonably popular movie recommendation, pulled live from "
                "TMDB. Leave `genre` blank for any genre, or pick one from the list (Action, "
                "Comedy, Horror, Romance, Sci-Fi, and more). Shows the title, year, a short "
                "synopsis, poster, and rating."
            ),
            inline=False,
        )
        movie_embed.set_footer(
            text="Requires the bot owner to have configured a free TMDB API key."
        )
        pages.append(_footer(movie_embed))

        # ── Page: Admin / Moderator Commands ──────────────────────────────
        admin_embed = discord.Embed(
            title="🛡️ Admin / Moderator Commands",
            description=(
                "These require Administrator permission on the server (or bot-owner status, "
                "where noted) -- everyone else will get a permission error if they try."
            ),
            color=DISCORD_GOLD,
        )
        admin_embed.add_field(
            name="Moderation (server admin)",
            value=(
                "`/botban @user` -- block a user from using the bot.\n"
                "`/botunban @user` -- restore their access.\n"
                "`/resetuser @user` -- wipe a user's level/XP/affection/stats back to defaults."
            ),
            inline=False,
        )
        admin_embed.add_field(
            name="Owner-only (bot owner account)",
            value=(
                "`!sync` -- push slash command changes to Discord.\n"
                "`!seed` -- (re)seed the achievements table.\n"
                "`/gif add`, `/gif list`, `!addgif`, `!addgifs`, `!addgifsfromlist` -- manage "
                "the GIF library.\n"
                "`!clearcache [prefix]` -- clear in-memory cache entries.\n"
                "`!botstats` -- guild/user/latency stats."
            ),
            inline=False,
        )
        pages.append(_footer(admin_embed))

        await interaction.response.send_message(embed=pages[0], view=PaginatedView(pages))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(HelpCog(bot))
