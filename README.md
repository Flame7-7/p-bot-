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
| `GAME_BUMP_DELAY` | | Quiet seconds before a game message moves to the bottom of the DM (default `60`, `0` = off) |
| `REDDIT_CLIENT_ID` / `REDDIT_CLIENT_SECRET` | for `/reddit` | Reddit API app credentials (see *Reddit*); optional but recommended |
| `REDDIT_USER_AGENT` | | Identifies the bot to Reddit, e.g. `python:p-bot:1.0 (by /u/yourname)` |
| `LEGACY_ROLEPLAY_COMMANDS` | | `true` also registers `/hug`, `/kiss`, … as separate commands (see below) |

Missing required variables stop startup with a clear message instead of a traceback.

---

## What it does

Run **`/help`** for the live list — it is generated from the commands actually registered, grouped by category, and only shows what *you* can use (owner/admin commands, guild-only commands, and age-restricted commands are hidden when they don't apply). Adding a cog with a `help_category = ("🎮", "Name")` attribute makes its commands show up automatically.

### 🎮 Couple games (in DMs)

**`/play`** opens a menu: pick a category (🧠 Brain · 🎲 Chance · ❤️ Relationship · 😂 Funny · ⚔️ Competitive), pick a game (each shows its description, estimated time, players and difficulty), press **Play**. The game is sent to **both partners' DMs**. Requires a linked partner (`/propose`).

`/play game:<name>` skips the menu (autocomplete), `/gamequit` leaves the current game, and the old shortcuts `/ttt`, `/connect4`, `/wyr`, `/truthordare` still work.

| Category | Games |
|---|---|
| 🧠 Brain | Memory, Hangman, Number Guessing, Trivia, Emoji Guessing, Word Guessing |
| 🎲 Chance | Rock Paper Scissors, Higher or Lower |
| ❤️ Relationship | Compatibility Quiz, Who Knows Who Better?, Guess My Favourite, Pick One for Tonight |
| 😂 Funny | Would You Rather, This or That, Who's More Likely To…, Truth or Dare |
| ⚔️ Competitive | Tic-Tac-Toe, Connect 4 |

The menu is built from the game classes themselves, so a new game appears in it automatically (see *Adding a game*).

**Guarantees** (handled once, in `services/dm_games/session.py`): only the two players can press a game's buttons; each user can be in one game at a time; clicks are processed under a per-game lock; games expire after `game_idle_timeout` (30 min) of inactivity and buttons are disabled when a game ends, expires, is quit, or the bot shuts down; if a DM can't be delivered the game aborts cleanly; scores are kept per couple (`/couple stats`).

#### Game message bumping

Chatting in the DM pushes the game message up the conversation, so the bot moves it back down:

- Every message in a player's DM (yours, hers, or the bot's relay of it) restarts a quiet timer for that DM. After `GAME_BUMP_DELAY` seconds (default **60**) with no new messages, the game is re-posted at the bottom — **only if something was said after it**; a game nobody has talked over is left alone.
- Using the game (a move, a button, an answer) restarts the timer too. Game state is untouched: the new message is rendered from the live session with fresh buttons, the old message is deleted (or, if Discord won't let it be deleted, disabled), and the stored message id is updated. Old copies can't be clicked.
- It all runs on **one** background loop owned by the game manager (no task per message or per game); chat activity only updates a timestamp. When a game ends, is quit, or expires, its timers are dropped.
- If a player deletes the game message, it is re-posted. If a re-post fails (DMs closed), the old message is kept and the bot backs off.
- Message ids are stored in the database (`active_game_messages`). Games live in memory, so after a restart the bot disables the leftover game messages ("this game ended because the bot restarted") instead of leaving dead buttons.
- `GAME_BUMP_DELAY=0` turns bumping off.

### 💕 `/couple`

`compliment`, `cutemessage`, `dateidea`, `challenge` (each with *Another* / *Send to partner* buttons), `mood` (tell your partner how you feel), `daily` (today's question — answers revealed together), `pickone`, `lovecalc`, `journal` + `memories` (shared journal), `milestone` / `countdown` / `unmilestone` (dates and anniversaries; also shows days together), `stats`.

### 🎭 Roleplay

One command instead of dozens:

```
/roleplay action:hug target:@her
```

Start typing in `action` for autocomplete; `/help` → Roleplay lists every action by category. In a DM with the bot, `target` defaults to your partner and the result is mirrored to them.

`/role` sets the pronouns used in roleplay messages (optional).

`/intimate` holds the adults-only actions. It only works in DMs or age-restricted server channels — Discord's own rule for adult content — and is hidden from `/help` elsewhere. The bot has no consent or verification step of its own; it's a private two-person bot.

Want the old per-action commands too? Set `LEGACY_ROLEPLAY_COMMANDS=true` — they are generated from the same content files. Mind Discord's 100 global command limit.

### 💬 Persona (server channel only)

Persona **no longer works in DMs.** It lives in one channel per server:

1. A server admin (Manage Server) runs `/persona setup channel:#chat`. The bot checks it can view/send/embed/read history there and explains how it works.
2. Each person runs `/persona set` (describe how you talk) and turns on `/afk on` when away (or leaves `/afk auto` on to follow your Discord status).
3. In that channel, anyone who mentions or replies to an away person gets an AI reply in their voice, tagged 🤖 unless they hide it (`/afk label`).

The bot ignores every other channel and all DMs. `/persona status` shows the current channel and any permission problems; `/persona disable` turns it off. Deleting the channel disables persona for that server automatically. Existing persona text and AFK settings are kept — they are per user and unchanged.

DMs between partners still work as a plain relay (text, gifs, images are forwarded to the partner).

### 🌐 Reddit

`/reddit subreddit:cats` shows a post as an embed (title, image, ⬆️ upvotes, 💬 comments, 👤 author, **View Post** link) with **⬅️ Previous / ➡️ Next / 🔄 Random** buttons. Options: `sort` = hot · top · new · random, `timeframe` for top. Image and gallery posts show the picture; text posts a preview; video and link posts show a preview image where Reddit has one plus a link. Removed/deleted posts are skipped.

- **NSFW:** age-restricted posts are shown **only in age-restricted server channels** — never in DMs or ordinary channels. If a subreddit has nothing else to show, the bot says so.
- **Setup:** go to <https://www.reddit.com/prefs/apps>, create an app (type *script*), and put its id and secret in `REDDIT_CLIENT_ID` / `REDDIT_CLIENT_SECRET`, plus a descriptive `REDDIT_USER_AGENT`. The bot then uses Reddit's official OAuth API (app-only token, refreshed automatically). Without credentials it falls back to Reddit's public `.json` endpoints, which Reddit often throttles or blocks — expect errors there.
- **Efficiency:** a listing is cached for 5 minutes and shared; the buttons only page through it, so pressing them never calls Reddit. Concurrent requests for the same subreddit share one call, and Reddit's rate-limit headers are honoured.
- **Errors** (unknown/private/banned subreddit, invalid name, rate limit, timeout, outage, empty feed) all produce a short, friendly message.
- The API code is `services/reddit_service.py`; the Discord side is `cogs/reddit/reddit_cog.py`.

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

**Adding a game:** subclass `GameSession` (or `TurnGame`) in `services/dm_games/`, implement `render(uid)`, and set `category`, `blurb`, `duration` (and optionally `difficulty`) on the class. If it's in a new module, add the module name to `GAME_MODULES` in `registry.py`. Locking, ownership checks, timeouts, scoring and message bumping come from the base class; `/play`, `/help` and `/couple stats` pick it up automatically.

## Database

Tables are created automatically; column additions to older databases run on startup (idempotent) — see `database/connection.py`. The tables added so far are `persona_channels`, `couple_game_stats`, `couple_milestones`, `couple_journal` and `active_game_messages`. Nothing existing is altered, so upgrading is just restarting. The unused `roleplay_profiles.consent_given` / `consented_at` columns remain in old databases (SQLite can't drop them safely) and are never read or written. Back up `bot.db` first as usual.

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
