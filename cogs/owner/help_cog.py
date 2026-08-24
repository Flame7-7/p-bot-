from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from services.action_registry import get_by_category
from views.embeds import PaginatedViewMarkdown

# Only the SFW categories are documented/browsable here on purpose --
# Explicit response text is not reproduced in help; shared roleplay infrastructure still applies to every registered action.
CATEGORY_INFO = {
    "affection": ("Affection", "💕"),
    "playful":   ("Playful", "😄"),
    "emotional": ("Emotional", "💭"),
    "social":    ("Social", "🤝"),
}


class HelpCog(commands.Cog, name="Help"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="help", description="View all bot commands")
    async def help(self, interaction: discord.Interaction) -> None:
        pages: list[str] = []

        # ── Page 1: Getting Started ─────────────────────────────────────
        pages.append(
            "# 🌸 Roleplay Bot\n\n"
            "A social roleplay bot with relationships, achievements, leveling, and leaderboards!\n\n"
            "## 🚀 Getting Started\n"
            "- `/help` -- this menu.\n"
            "- `/consent` -- set your role (Male / Female / Non-Binary) and confirm the "
            "community guidelines. Optional: you can use every roleplay command below without "
            "it, but it's what unlocks gendered wording (`he`/`she`/`they`) in responses, and "
            "it's required by anything using the `requires_verification()` check.\n"
            "- `/verify` -- alias for `/consent`.\n"
            "- `/consentstatus` -- check your current role/consent without opening the setup flow.\n\n"
            "## Browse by Category\n"
            "• 💕 **Affection** -- show love and care\n"
            "• 😄 **Playful** -- have fun together\n"
            "• 💭 **Emotional** -- express yourself\n"
            "• 🤝 **Social** -- greet and interact\n\n"
            "## Other Features\n"
            "• 👤 Profile & Stats · 💑 Relationships · 🏆 Achievements\n"
            "• 📊 Leaderboards · 🎁 Economy · ⚙️ Settings\n"
            "• 🔥 No-Fap Tracker · 🎬 Movie Recommendations\n\n"
            "### ⚡ Quick Start\n"
            "`/consent` → `/hug @user` · `/profile` · `/propose @user` · `/top`"
        )

        # ── Pages 2-5: Roleplay commands, one page per SFW category ────
        for cat_key, (cat_label, emoji) in CATEGORY_INFO.items():
            actions = get_by_category(cat_key)
            if not actions:
                continue

            page_content = (
                f"# {emoji} {cat_label} Commands\n\n"
                f"Browse all {cat_label.lower()} roleplay actions. Use `/consent` first if you "
                f"want responses to use your chosen pronouns -- it isn't required to run these.\n\n"
            )
            for action in actions:
                note = " *(target optional)*" if not action.requires_target else ""
                page_content += (
                    f"## `/{action.name} @target`{note}\n"
                    f"{action.description}\n"
                    f"- 💕 `+{action.affection_gain}` • ✨ `+{action.xp_gain} XP` "
                    f"• ⏱️ cooldown: `{action.cooldown_seconds}s`\n\n"
                )
            pages.append(page_content)

        # Intimate actions intentionally have an overview rather than a command-by-command
        # directory. The actual registered commands remain untouched, but their execution is
        # protected by the shared RoleplayService gates.
        if get_by_category("intimate"):
            pages.append(
                "# 🔞 Intimate Roleplay\n\n"
                "Intimate roleplay actions use the same roleplay system as the other categories, "
                "with additional safeguards.\n\n"
                "## Requirements\n"
                "- 🔒 **Both participants must complete `/consent`.**\n"
                "- 🔞 **The action must be used in an NSFW Discord channel.**\n"
                "- 🛑 A user who has disabled interactions cannot be targeted.\n\n"
                "## Privacy & consent\n"
                "Consent is stored per user in the existing SQLite database. It is never inferred "
                "from a channel setting, and another user's consent cannot be changed by someone "
                "else.\n\n"
                "The individual intimate commands remain available through Discord's slash-command "
                "interface for eligible users; this help page deliberately avoids reproducing the "
                "explicit action catalogue."
            )

        # ── Page: Sync Commands ─────────────────────────────────────────
        pages.append(
            "# 🔁 Sync Commands\n\n"
            "Syncing pushes this bot's slash command definitions to Discord, so new/changed "
            "commands actually show up when you type `/`. You only need this after the bot's "
            "code changes -- not for normal use.\n\n"
            "## Command\n"
            "`!sync` *(owner only, text command, mention-prefixed)*\n"
            "- Registers every currently-loaded slash command with Discord globally.\n"
            "- Can take up to an hour to propagate globally on Discord's side after running it.\n\n"
            "## Requirements\n"
            "- Must be run by the bot owner (`commands.is_owner()`).\n\n"
            "## Example\n"
            "`@RoleplayBot sync`"
        )

        # ── Page: GIF Commands ───────────────────────────────────────────
        pages.append(
            "# 🎬 GIF Commands\n\n"
            "Every roleplay command above automatically attaches a random GIF from that "
            "action's category (falls back to a Tenor search if the library has none saved).\n\n"
            "## Managing the GIF Library *(owner only)*\n"
            "- `/gif add <category> <urls>` -- add one or more direct `.gif` links to a "
            "category (space/comma/newline separated). Autocompletes the category field.\n"
            "- `/gif list <category>` -- see how many GIFs a category has and preview the URLs.\n"
            "- `!addgif <category> <url>` -- add a single GIF via text command.\n"
            "- `!addgifs <category> <name_prefix>` + attachments -- bulk add up to 25 GIFs/"
            "images/videos from attached files.\n"
            "- `!addgifsfromlist <category> <name_prefix>` + a `.txt` attachment -- bulk add "
            "URLs from a text file, one per line.\n\n"
            "## Notes\n"
            "- Categories match the roleplay action names (`hug`, `pat`, `slap`, etc.) -- see "
            "the category pages above for the full list.\n"
            "- No arguments are required to trigger a GIF -- it's automatic on every roleplay command."
        )

        # ── Page: Custom Commands ────────────────────────────────────────
        pages.append(
            "# 🧩 Custom Commands\n\n"
            "Server administrators (or the bot owner) can create database-backed custom slash "
            "commands without editing Python source code. Commands are stored per server and "
            "survive bot restarts.\n\n"
            "## Management\n"
            "- `/addcommand` -- create a custom command with a response, description, category, "
            "cooldown, and optional target requirement.\n"
            "- `/editcommand` -- change an existing custom command or disable/enable it.\n"
            "- `/removecommand` -- delete a custom command.\n"
            "- `/customcommands` -- list this server's custom commands.\n\n"
            "## Response placeholders\n"
            "Use `{user}` or `{author}` for the caller's display name, `{mention}` for the "
            "caller's mention, `{target}` or `{target_mention}` for the selected member, and "
            "`{server}` for the server name. Unsupported placeholders are rejected when a "
            "command is created or edited.\n\n"
            "## Cooldowns & targets\n"
            "- Each custom command can have a 0-3600 second per-user cooldown.\n"
            "- Mark a command as requiring a target when it should always receive a member.\n"
            "- Cooldowns are independent per user and per custom command.\n\n"
            "## Example\n"
            "`/addcommand name:welcome response:Welcome {target} to {server}! "
            "description:Welcome someone category:social cooldown:10 requires_target:True`\n\n"
            "Custom command names cannot replace built-in commands such as `/help`, `/hug`, "
            "or `/profile`, and commands are registered only in the server where they were created."
        )

        # ── Page: Configuration ─────────────────────────────────────────
        pages.append(
            "# ⚙️ Configuration\n\n"
            "## Your Role & Consent\n"
            "- `/consent` -- opens role selection (Male / Female / Non-Binary), then asks you "
            "to confirm. If you've already set up, this shows your current status with buttons "
            "to **Change Role** or **Reset** instead of restarting the whole flow.\n"
            "- `/consentstatus` -- read-only view of your current role/consent.\n"
            "- Changing your role always clears consent, so you re-confirm the guidelines "
            "after switching.\n\n"
            "## Resetting\n"
            "- Use the **Reset** button on `/consent` -- this deletes your saved role/consent "
            "entirely, back to the \"not started\" state.\n\n"
            "## What Happens on Bot Restart\n"
            "- Your role/consent is stored in the bot's SQLite database, not in memory, so it "
            "**survives restarts**. You won't need to redo `/consent` after an update or reboot.\n\n"
            "## `/settings`\n"
            "- Separate from `/consent` -- toggles whether others can target you with roleplay "
            "commands, and whether you appear on leaderboards."
        )

        # ── Page: Cooldowns ──────────────────────────────────────────────
        pages.append(
            "# ⏱️ Cooldowns\n\n"
            "Registered roleplay actions have a per-user, per-command cooldown (shown on each "
            "category page where applicable) to stop spam. This uses the same shared cooldown "
            "system across the roleplay action registry, including existing categories that are "
            "not expanded or reproduced in this help text. `/consent`'s role-change "
            "buttons have their own short 10s cooldown for the same reason.\n\n"
            "## What you'll see\n"
            "If you're on cooldown, the bot replies with how long is left, e.g.:\n"
            "> ⏳ Cooldown! Try again in **12s**.\n\n"
            "## What's *not* on cooldown\n"
            "`/help`, `/consent`, `/consentstatus`, `/profile`, `/settings`, and admin/mod "
            "commands are never rate-limited by the roleplay cooldown system -- only the "
            "roleplay action commands are."
        )

        # ── Page: Other utility commands ─────────────────────────────────
        pages.append(
            "# 🛠️ Other Commands\n\n"
            "## 👤 Profile\n"
            "`/profile [user]` `/setbio` `/stats [user]`\n\n"
            "## 💑 Relationships\n"
            "`/propose @user` `/partner` `/breakup` `/anniversary`\n\n"
            "## 🏆 Achievements\n"
            "`/achievements [user]`\n\n"
            "## 📊 Leaderboard\n"
            "`/top affection|level|interactions`\n\n"
            "## 🎁 Economy\n"
            "`/daily`\n\n"
            "## ⚙️ Settings\n"
            "`/settings`\n\n"
            "## 🎮 Games\n"
            "`/rps` `/rps_pvp` `/coinflip` `/slots` `/trivia` `/roll` `/guess`"
        )

        # ── Page: No-Fap Tracker ─────────────────────────────────────────
        pages.append(
            "# 🔥 No-Fap Tracker\n\n"
            "A personal streak tracker, completely separate from the roleplay/consent "
            "system -- just a self-improvement tool. Only you can see and manage your own "
            "streak.\n\n"
            "## `/nofap start`\n"
            "Begin tracking your streak. Does nothing if you already have one running.\n\n"
            "## `/nofap status`\n"
            "See your current streak length, start date, and last reset.\n\n"
            "## `/nofap stats`\n"
            "See your best-ever streak, total resets, and how long you've been tracking.\n\n"
            "## `/nofap reset`\n"
            "Record a relapse. Asks for confirmation first, then banks your finished streak "
            "as a new best (if it is one) and starts a fresh streak from now.\n\n"
            "Your streak survives bot restarts -- it's stored in the same SQLite database as "
            "everything else."
        )

        # ── Page: Movie Recommendations ────────────────────────────────────
        pages.append(
            "# 🎬 Movie Recommendations\n\n"
            "## `/movie recommend [genre]`\n"
            "Get a random, reasonably popular movie recommendation, pulled live from TMDB. "
            "Leave `genre` blank for any genre, or pick one from the list (Action, Comedy, "
            "Horror, Romance, Sci-Fi, and more).\n\n"
            "Shows the title, year, a short synopsis, poster, and rating.\n\n"
            "*(Requires the bot owner to have configured a free TMDB API key -- if you see a "
            "setup message instead of a movie, that hasn't been done yet.)*"
        )

        # ── Page: Admin / Moderator Commands ──────────────────────────────
        pages.append(
            "# 🛡️ Admin / Moderator Commands\n\n"
            "These require Administrator permission on the server (or bot-owner status, "
            "where noted) -- everyone else will get a permission error if they try.\n\n"
            "## Moderation *(server admin)*\n"
            "- `/botban @user` -- block a user from using the bot.\n"
            "- `/botunban @user` -- restore their access.\n"
            "- `/resetuser @user` -- wipe a user's level/XP/affection/stats back to defaults.\n\n"
            "## Owner-only *(bot owner account)*\n"
            "- `!sync` -- push slash command changes to Discord.\n"
            "- `!seed` -- (re)seed the achievements table.\n"
            "- `/gif add`, `/gif list`, `!addgif`, `!addgifs`, `!addgifsfromlist` -- manage "
            "the GIF library (see 🎬 GIF Commands).\n"
            "- `!clearcache [prefix]` -- clear in-memory cache entries (leaderboards, games, "
            "etc.), optionally by key prefix.\n"
            "- `!botstats` -- guild/user/latency stats.\n\n"
            "These are intentionally separate from everyday roleplay/profile commands so a "
            "regular member's `/help` browsing doesn't get cluttered with things they can't run."
        )

        await interaction.response.send_message(
            content=pages[0], view=PaginatedViewMarkdown(pages)
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(HelpCog(bot))
