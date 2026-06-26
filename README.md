# 🌸 Discord Roleplay Bot (Lite)

Zero-dependency-server Discord roleplay bot. Uses **SQLite** (file-based) and **in-memory** cooldowns — no PostgreSQL, no Redis, no Docker required.

Runs under **150MB RAM** and deploys to any free host.

---

## ✨ Features

- **32 Roleplay Commands** — hug, pat, kiss, cuddle, poke, boop, headpat, nuzzle, snuggle, tackle, slap, punch, kick, bite, lick, tickle, pounce, throw, cry, wave, blush, smile, wink, dance, laugh, sigh, highfive, fistbump, handshake, bow, stare, glare
- **GIF support** — per-category DB storage + optional Tenor API fallback
- **Relationship system** — `/propose`, `/partner`, `/breakup`, `/anniversary`
- **Achievements** — 14 achievements, hidden/rare, XP rewards
- **Leveling & XP** — every command gives XP + affection
- **Daily rewards** — `/daily` with 7-day streak system
- **Leaderboards** — affection, level, interactions (paginated)
- **Profiles** — `/profile`, `/setbio`, `/stats`
- **Interactive Settings** — toggle interactions & leaderboard visibility with buttons
- **Moderation** — `/botban`, `/botunban`, `/resetuser`
- **Help** — `/help` with paginated category browser

---

## 🚀 Setup (5 minutes)

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env — fill in DISCORD_TOKEN and DISCORD_CLIENT_ID
```

### 3. Run

```bash
python main.py
```

The bot creates `bot.db` automatically on first run. No setup needed.

### 4. Sync slash commands

In Discord (bot owner only):

```
@YourBot sync
```

Done. All 32 commands are live.

---

## 🆓 Free Hosting

### Railway (recommended)
1. Push code to GitHub
2. New Project → Deploy from GitHub
3. Add env vars: `DISCORD_TOKEN`, `DISCORD_CLIENT_ID`
4. Deploy — no addons needed (SQLite is just a file)

### Discloud
1. Zip the project folder
2. Upload at discloud.app
3. Set `DISCORD_TOKEN` and `DISCORD_CLIENT_ID` in the dashboard

### Koyeb
1. Push to GitHub
2. New App → GitHub → select repo
3. Set env vars, deploy

> **Note:** On hosts that reset the filesystem on restart (some free tiers), the SQLite file will be wiped. If persistence matters, use Railway (persists files) or Discloud (persists files). Koyeb's free tier does persist the filesystem.

---

## 🖼️ Adding GIFs

### Single GIF
```
@YourBot addgif hug https://media.tenor.com/your-hug-gif.gif
@YourBot addgif kiss https://media.tenor.com/your-kiss-gif.gif
```

### Bulk Upload (Multiple Files)
Drag and drop up to 25 GIF files into Discord:
```
@YourBot addgifs <category> <name_prefix> [attachments...]
```
Example: `@YourBot addgifs hug cuddle` with 10 GIF attachments → creates `cuddle_1`, `cuddle_2`, etc.

### Bulk Upload from URL List
Create a `urls.txt` file with one GIF URL per line:
```
@YourBot addgifsfromlist <category> <name_prefix> [text_file]
```
Example: `@YourBot addgifsfromlist pat pat` with `urls.txt` containing 20 URLs → creates `pat_1`, `pat_2`, etc.

Or set `TENOR_API_KEY` in `.env` for automatic GIF fetching as fallback when no local GIFs exist.

---

## ➕ Adding a New Command

Edit `services/action_registry.py` — add one `register(ActionConfig(...))` block:

```python
register(ActionConfig(
    name="myaction",
    category="affection",       # affection | playful | emotional | social
    affection_gain=10,
    xp_gain=15,
    cooldown_seconds=30,
    gif_category="myaction",
    self_targetable=False,
    requires_target=True,
    description="Do my action",
    response_templates=[
        "**{author}** did myaction to **{target}**! 💫",
        # 4 more...
    ],
))
```

The `/myaction` slash command is created automatically. Nothing else to change.

---

## 👑 Owner Commands (prefix)

| Command | Description |
|---|---|
| `@Bot sync` | Sync slash commands |
| `@Bot seed` | Re-seed achievements |
| `@Bot addgif <category> <url>` | Add a single GIF |
| `@Bot addgifs <category> <prefix> [files...]` | Bulk add up to 25 GIFs from attachments |
| `@Bot addgifsfromlist <category> <prefix> [file.txt]` | Add GIFs from URL list file |
| `@Bot clearcache [prefix]` | Clear in-memory cache |
| `@Bot botstats` | View bot statistics |

---

## 📁 Structure

```
bot_lite/
├── main.py                     # Entry point
├── requirements.txt            # 5 dependencies
├── .env.example
│
├── cogs/
│   ├── roleplay/roleplay_cog.py   # All 32 commands (auto-generated)
│   ├── profile/profile_cog.py     # /profile /setbio /stats
│   ├── relationships/             # /propose /partner /breakup /anniversary
│   ├── achievements/              # /achievements
│   ├── economy/economy_cog.py     # /daily /top
│   ├── settings/settings_cog.py   # /settings (interactive panel)
│   ├── moderation/                # /botban /botunban /resetuser
│   └── owner/                     # sync, seed, addgif, tasks, help
│
├── models/models.py            # SQLAlchemy models (SQLite)
├── database/connection.py      # aiosqlite async engine
├── repositories/               # All DB queries
├── services/
│   ├── action_registry.py      # All 32 actions defined here
│   ├── roleplay_service.py     # Core execution engine
│   └── gif_service.py          # GIF lookup + Tenor fallback
├── views/embeds.py             # Embed builders + PaginatedView
└── utils/
    ├── config.py               # Env-based config
    ├── cooldowns.py            # In-memory cooldowns + cache
    └── logging.py              # Simple stdout logging
```
