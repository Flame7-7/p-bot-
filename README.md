# 💕 p-bot

A private Discord bot for two: roleplay actions, couple games played in DMs, cute daily touches, relationship tracking, and an optional AI "persona" that answers for you in one server channel.

Built on discord.py 2.x, SQLite (SQLAlchemy async) and in-memory cooldowns — no Redis, no Docker, runs happily on a free host.

---

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env        # fill in DISCORD_TOKEN and DISCORD_CLIENT_ID
python main.py
```

The database (`bot.db`) is created and migrated automatically on start. Then, in Discord, as the bot owner:

```
@YourBot sync
```

**Required Discord settings** (Developer Portal → Bot → Privileged Gateway Intents): **Server Members**, **Presence**, **Message Content**.

### Environment variables

| Variable | Required | Purpose |
|---|---|---|
| `DISCORD_TOKEN` | ✅ | Bot token |
| `DISCORD_CLIENT_ID` | ✅ | Application ID (numeric) |
| `DB_PATH` | | SQLite file, default `bot.db` |
| `GROQ_API_KEY` | for persona | Free key from console.groq.com; without it `/afk on` explains it can't run |
| `PERSONA_MODEL` | | Model for persona replies (default `openai/gpt-oss-120b`) |
| `TENOR_API_KEY` | | Automatic GIF fallback |
| `TMDB_API_KEY` | | `/movie recommend` |
| `LEGACY_ROLEPLAY_COMMANDS` | | `true` also registers `/hug`, `/kiss`, … as separate commands (see below) |

Missing required variables stop startup with a clear message instead of a traceback.

---

## What it does

Run **`/help`** for the live list — it is generated from the commands actually registered, grouped by category, and only shows what *you* can use (owner/admin commands, guild-only commands, and age-restricted commands are hidden when they don't apply). Adding a cog with a `help_category = ("🎮", "Name")` attribute makes its commands show up automatically.

### 🎮 Couple games (in DMs)

`/play start <game>` sends the game to **both partners' DMs**. Requires a linked partner (`/propose`).

| Game | | Game | |
|---|---|---|---|
| ⭕ Tic-Tac-Toe | `/ttt` | 🔍 Who Knows Who Better? | answer, then guess each other |
| 🔴 Connect 4 | `/connect4` | 💝 Guess My Favourite | free-text, fuzzy matched |
| ✂️ Rock Paper Scissors | best of 3, secret picks | 🧩 Trivia | higher score wins |
| 🧠 Memory | emoji pairs | 😎 Emoji Guessing | decode first |
| 🪢 Hangman | one sets a word | 🔤 Word Guessing | unscramble first |
| 🔢 Number Guessing | find it together | 🃏 Higher or Lower | team streak |
| 🎭 Truth or Dare | `/truthordare` | 🤍 Would You Rather | `/wyr` |
| ⚡ This or That | | 🙋 Who's More Likely To… | |
| 💘 Compatibility Quiz | match % | 🌙 Pick One for Tonight | tie-break included |

`/play list` shows them in Discord, `/play quit` leaves the current game.

**Guarantees** (all handled once, in `services/dm_games/session.py`): only the two players can press a game's buttons; each user can be in one game at a time; clicks are processed under a per-game lock; games expire after `game_idle_timeout` (30 min) of inactivity and buttons are disabled when a game ends, expires, is quit, or the bot shuts down; if a DM can't be delivered the game aborts cleanly; scores are kept per couple (`/couple stats`).

### 💕 `/couple`

`compliment`, `cutemessage`, `dateidea`, `challenge` (each with *Another* / *Send to partner* buttons), `mood` (tell your partner how you feel), `daily` (today's question — answers revealed together), `pickone`, `lovecalc`, `journal` + `memories` (shared journal), `milestone` / `countdown` / `unmilestone` (dates and anniversaries; also shows days together), `stats`.

### 🎭 Roleplay

One command instead of dozens:

```
/roleplay action:hug target:@her
```

Start typing in `action` for autocomplete; `/help` → Roleplay lists every action by category. In a DM with the bot, `target` defaults to your partner and the result is mirrored to them.

`/role` sets the pronouns used in roleplay messages (optional, no setup or consent step).

`/intimate` holds the adults-only actions. It only works in DMs or age-restricted channels, and is hidden from `/help` elsewhere.

Want the old per-action commands too? Set `LEGACY_ROLEPLAY_COMMANDS=true` — they are generated from the same content files. Mind Discord's 100 global command limit.

### 💬 Persona (server channel only)

Persona **no longer works in DMs.** It lives in one channel per server:

1. A server admin (Manage Server) runs `/persona setup channel:#chat`. The bot checks it can view/send/embed/read history there and explains how it works.
2. Each person runs `/persona set` (describe how you talk) and turns on `/afk on` when away (or leaves `/afk auto` on to follow your Discord status).
3. In that channel, anyone who mentions or replies to an away person gets an AI reply in their voice, tagged 🤖 unless they hide it (`/afk label`).

The bot ignores every other channel and all DMs. `/persona status` shows the current channel and any permission problems; `/persona disable` turns it off. Deleting the channel disables persona for that server automatically. Existing persona text and AFK settings are kept — they are per user and unchanged.

DMs between partners still work as a plain relay (text, gifs, images are forwarded to the partner).

### Other features

Relationships (`/propose`, `/partner`, `/breakup`, `/anniversary`), profiles and stats, achievements, economy (`/daily`, `/top`, `/slots`, `/blackjack`, `/heist`…), server games, `/movie`, `/nofap`, per-user `/settings`, per-server custom commands (`/addcommand`, …), and an owner-only `/resetuser`.

---

## Editing content (no Python needed)

Everything text-heavy lives in `content/` as Markdown:

```
content/
├── roleplay/actions.md     # every /roleplay action: stats + response templates
├── roleplay/intimate.md    # /intimate actions
├── couple/*.md             # truth, dare, would_you_rather, trivia, compliments, date ideas, …
└── persona/system_prompt.md
```

**Roleplay action** — add a block to `roleplay/actions.md`:

```markdown
## myaction
category: affection        # affection | playful | emotional | social
description: Do my action
affection: 10
xp: 15
cooldown: 30
gif: myaction
target: required           # or optional
self: no                   # may the user target themselves?
- **{author}** did myaction to **{target}**! 💫
- another response…
```

Placeholders: `{author} {target} {target_mention} {author_pronoun} {author_pronoun_obj} {author_possessive} {target_pronoun} {target_pronoun_obj} {target_possessive}`.

**Lists** (compliments, dares, …) are one `- item` per line. **Pair/row files** use `|`: would-you-rather `A | B`; trivia `question | correct | wrong | wrong | wrong`; emoji puzzles `🎬🎬 | Answer / Alt answer`.

Apply edits with `@YourBot reload` (no restart) — or just restart. Run the tests after big edits: they validate the format.

## Owner commands (`@YourBot <command>`)

`sync`, `seed`, `reload`, `addgif`, `addgifs`, `addgifsfromlist`, `clearcache`, `botstats`.

### Adding GIFs

```
@YourBot addgif hug https://media.tenor.com/....gif
@YourBot addgifs <category> <prefix> [attachments…]        # up to 25 files
@YourBot addgifsfromlist <category> <prefix> [urls.txt]    # one URL per line
```

---

## Project layout

```
main.py                 entry point, cog list, global error + ban handling
cogs/                   thin Discord layer: commands → services
  couple/ dmgames/ roleplay/ persona/ help/ …
services/               business logic
  dm_games/             session.py (reusable manager) · board.py · quiz.py · registry.py
repositories/           all database queries
models/ database/       SQLAlchemy models, engine, additive migrations
utils/                  config, content loader, interaction helpers, cooldowns, http
views/                  shared embeds and paginators
content/                Markdown content (above)
tests/                  pytest suite
docs/command-ideas.md   brainstorm of future features (not implemented docs)
```

**Adding a game:** subclass `GameSession` (or `TurnGame`) in `services/dm_games/`, implement `render(uid)`, and add one line to `registry.py`. Locking, ownership checks, timeouts and scoring come from the base class; `/play`, `/play list` and `/couple stats` pick it up automatically.

## Database

Tables are created automatically; column additions to older databases run on startup (idempotent) — see `database/connection.py`. This update **adds** four tables (`persona_channels`, `couple_game_stats`, `couple_milestones`, `couple_journal`) and changes nothing existing, so upgrading is just restarting. Back up `bot.db` first as usual.

## Development

```bash
pip install -r requirements-dev.txt
python -m pytest -q tests
python -m pyflakes .
```

## Content scope

The adults-only action text was moved verbatim into `content/roleplay/intimate.md` and is not expanded; no new explicit content is part of this project.

## Free hosting notes

Railway, Discloud and Koyeb all work (set `DISCORD_TOKEN` and `DISCORD_CLIENT_ID`; SQLite is just a file). On hosts that wipe the filesystem on restart the database will be wiped too — pick one that persists files.
