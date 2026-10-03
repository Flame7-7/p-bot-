"""The catalogue of DM games, discovered from the game classes themselves.

A game appears in ``/play`` (and ``/help``, ``/couple stats``) as soon as its class
defines ``category`` in its own body and its module is imported below — there is no
list to edit and no menu to rewrite.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass

from services.dm_games.session import GameSession

# Importing a module registers its GameSession subclasses. A new game module only needs
# its name added here.
GAME_MODULES = ("services.dm_games.board", "services.dm_games.quiz")
for _module in GAME_MODULES:
    importlib.import_module(_module)

CATEGORIES: dict[str, tuple[str, str]] = {
    "Brain": ("🧠", "Puzzles, guessing and trivia"),
    "Chance": ("🎲", "Luck, nerve and quick picks"),
    "Relationship": ("❤️", "Get to know each other better"),
    "Funny": ("😂", "Silly dilemmas and dares"),
    "Competitive": ("⚔️", "Head-to-head, may the best one win"),
}


@dataclass(frozen=True)
class GameInfo:
    key: str
    label: str
    blurb: str
    cls: type[GameSession]
    category: str
    duration: str
    players: str
    difficulty: str | None


def _all_subclasses(cls: type[GameSession]) -> list[type[GameSession]]:
    out: list[type[GameSession]] = []
    for sub in cls.__subclasses__():
        out.append(sub)
        out.extend(_all_subclasses(sub))
    return out


def discover_games() -> tuple[GameInfo, ...]:
    games = []
    for cls in _all_subclasses(GameSession):
        if "category" not in cls.__dict__ or cls.category is None:
            continue
        games.append(
            GameInfo(
                key=cls.key, label=f"{cls.emoji} {cls.title}", blurb=cls.blurb, cls=cls,
                category=cls.category, duration=cls.duration, players=cls.players_label, difficulty=cls.difficulty,
            )
        )
    order = list(CATEGORIES)
    games.sort(key=lambda g: (order.index(g.category) if g.category in order else len(order), g.label))
    return tuple(games)


GAMES: tuple[GameInfo, ...] = discover_games()
BY_KEY = {g.key: g for g in GAMES}


def games_in(category: str) -> list[GameInfo]:
    return [g for g in GAMES if g.category == category]


def categories_in_use() -> list[str]:
    """Known categories first (in their display order), then any a new game introduced."""
    used = {g.category for g in GAMES}
    return [c for c in CATEGORIES if c in used] + sorted(used - set(CATEGORIES))
