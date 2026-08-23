from __future__ import annotations

import time
from collections import defaultdict

# {user_id: {action: expiry_timestamp}}
_cooldowns: dict[int, dict[str, float]] = defaultdict(dict)

# {key: (value, expiry_timestamp)}
_cache: dict[str, tuple[object, float]] = {}


def check_cooldown(user_id: int, action: str) -> int:
    """Returns remaining cooldown seconds, 0 if none.

    Reads with .get() instead of indexing the defaultdict directly --
    _cooldowns[user_id] would silently create a permanent empty entry for
    every user who merely *checks* a cooldown, even if they never trigger
    one. On a bot with many members that's an entry that lives for the
    life of the process for no reason.
    """
    user_cooldowns = _cooldowns.get(user_id)
    if not user_cooldowns:
        return 0
    expiry = user_cooldowns.get(action, 0)
    remaining = expiry - time.monotonic()
    return max(0, int(remaining))


def set_cooldown(user_id: int, action: str, seconds: int) -> None:
    _cooldowns[user_id][action] = time.monotonic() + seconds


def cache_get(key: str) -> object | None:
    entry = _cache.get(key)
    if not entry:
        return None
    value, expiry = entry
    if time.monotonic() > expiry:
        del _cache[key]
        return None
    return value


def cache_set(key: str, value: object, ttl: int = 300) -> None:
    # Several call sites (e.g. games_cog's guessing game) do
    # cache_set(key, None) to mean "clear this". Previously that stored a
    # (None, expiry) tuple that sat in _cache forever, since only
    # cache_get() on that *exact* key ever removes an entry, and nothing
    # re-reads a finished game's key. Treat None as a real delete instead.
    if value is None:
        cache_delete(key)
        return
    _cache[key] = (value, time.monotonic() + ttl)


def cache_delete(key: str) -> None:
    _cache.pop(key, None)


def cache_delete_prefix(prefix: str) -> int:
    keys = [k for k in _cache if k.startswith(prefix)]
    for k in keys:
        del _cache[k]
    return len(keys)


def prune_expired() -> tuple[int, int]:
    """Sweep both in-memory stores for stale data.

    Without this, both dicts only ever grow:
    - _cache: an entry that expires but is never cache_get()'d again just
      sits there forever (the lazy expiry check in cache_get only fires
      when someone reads that exact key).
    - _cooldowns: once a user's cooldown for an action expires, nothing
      ever removes that {action: timestamp} entry, or the user's outer
      dict once it's empty.

    On a long-running process with many users this is unbounded memory
    growth. Call this periodically (see cogs/owner/tasks_cog.py).

    Returns (cache_entries_removed, cooldown_entries_removed).
    """
    now = time.monotonic()

    expired_cache_keys = [k for k, (_, expiry) in _cache.items() if now > expiry]
    for k in expired_cache_keys:
        del _cache[k]

    removed_cooldowns = 0
    empty_users = []
    for user_id, actions in _cooldowns.items():
        expired_actions = [a for a, expiry in actions.items() if now > expiry]
        for a in expired_actions:
            del actions[a]
            removed_cooldowns += 1
        if not actions:
            empty_users.append(user_id)
    for user_id in empty_users:
        del _cooldowns[user_id]

    return len(expired_cache_keys), removed_cooldowns