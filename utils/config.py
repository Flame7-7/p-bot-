from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache

from dotenv import load_dotenv

from utils.logging import get_logger

load_dotenv()
logger = get_logger(__name__)


class ConfigError(RuntimeError):
    """Raised when required configuration is missing or invalid."""


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int, *, minimum: int = 0) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return max(minimum, int(raw))
    except ValueError:
        logger.warning("%s=%r is not a whole number; using %d", name, raw, default)
        return default


@dataclass(frozen=True)
class Config:
    # Discord
    token: str
    client_id: int
    tenor_api_key: str | None = None
    tmdb_api_key: str | None = None
    groq_api_key: str | None = None

    # Reddit (official API). Without credentials the public JSON endpoints are used,
    # which Reddit may throttle or block; see README.
    reddit_client_id: str | None = None
    reddit_client_secret: str | None = None
    reddit_user_agent: str = "python:p-bot:1.0 (private couple bot)"

    # Database
    db_path: str = "bot.db"

    # Roleplay
    relationship_bonus: float = 1.5
    # Register one slash command per roleplay action (/hug, /kiss, ...) in
    # addition to /roleplay. Off by default: Discord caps bots at 100 global
    # slash commands and the consolidated /roleplay command covers everything.
    legacy_roleplay_commands: bool = False

    # Persona (server-channel auto-replies)
    persona_model: str = "openai/gpt-oss-120b"
    persona_reply_cooldown: int = 6   # seconds between persona replies per user

    # DM games
    game_invite_timeout: int = 300    # seconds a game invite stays open
    game_idle_timeout: int = 1800     # seconds of inactivity before a game expires
    game_bump_delay: int = 60         # quiet seconds in the DM before the game message moves to the bottom (0 = off)

    # Progression
    base_xp: int = 100
    xp_multiplier: float = 1.5
    max_level: int = 100

    # Economy
    daily_xp: int = 50
    daily_affection: int = 10
    max_streak: int = 7
    streak_bonus_xp: int = 10

    extra: dict[str, str] = field(default_factory=dict)


@lru_cache(maxsize=1)
def get_config() -> Config:
    token = os.getenv("DISCORD_TOKEN", "").strip()
    client_id = os.getenv("DISCORD_CLIENT_ID", "").strip()
    missing = [n for n, v in (("DISCORD_TOKEN", token), ("DISCORD_CLIENT_ID", client_id)) if not v]
    if missing:
        raise ConfigError(f"Missing required environment variable(s): {', '.join(missing)} (see .env.example)")
    try:
        client_id_int = int(client_id)
    except ValueError as exc:
        raise ConfigError("DISCORD_CLIENT_ID must be a numeric application ID") from exc

    return Config(
        token=token,
        client_id=client_id_int,
        tenor_api_key=os.getenv("TENOR_API_KEY") or None,
        tmdb_api_key=os.getenv("TMDB_API_KEY") or None,
        groq_api_key=os.getenv("GROQ_API_KEY") or None,
        reddit_client_id=os.getenv("REDDIT_CLIENT_ID") or None,
        reddit_client_secret=os.getenv("REDDIT_CLIENT_SECRET") or None,
        reddit_user_agent=os.getenv("REDDIT_USER_AGENT") or Config.reddit_user_agent,
        game_bump_delay=_env_int("GAME_BUMP_DELAY", 60, minimum=0),
        db_path=os.getenv("DB_PATH", "bot.db"),
        legacy_roleplay_commands=_env_bool("LEGACY_ROLEPLAY_COMMANDS"),
        persona_model=os.getenv("PERSONA_MODEL", "openai/gpt-oss-120b"),
    )
