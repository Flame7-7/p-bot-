from __future__ import annotations

import os
from functools import lru_cache
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Discord
    token: str = os.environ["DISCORD_TOKEN"]
    client_id: int = int(os.environ["DISCORD_CLIENT_ID"])
    tenor_api_key: str | None = os.getenv("TENOR_API_KEY") or None
    tmdb_api_key: str | None = os.getenv("TMDB_API_KEY") or None

    # Database
    db_path: str = os.getenv("DB_PATH", "bot.db")

    # Roleplay
    default_cooldown: int = 15       # seconds
    affection_cooldown: int = 30     # seconds
    relationship_bonus: float = 1.5  # affection multiplier for partners

    # Progression
    base_xp: int = 100
    xp_multiplier: float = 1.5
    max_level: int = 100

    # Economy
    daily_xp: int = 50
    daily_affection: int = 10
    max_streak: int = 7
    streak_bonus_xp: int = 10


@lru_cache(maxsize=1)
def get_config() -> Config:
    return Config()
