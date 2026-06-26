from __future__ import annotations

import time
from collections import defaultdict

# {user_id: {action: expiry_timestamp}}
_cooldowns: dict[int, dict[str, float]] = defaultdict(dict)

# {user_id: {key: (value, expiry_timestamp)}}
_cache: dict[str, tuple[object, float]] = {}


def check_cooldown(user_id: int, action: str) -> int:
    """Returns remaining cooldown seconds, 0 if none."""
    expiry = _cooldowns[user_id].get(action, 0)
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
    _cache[key] = (value, time.monotonic() + ttl)


def cache_delete(key: str) -> None:
    _cache.pop(key, None)


def cache_delete_prefix(prefix: str) -> int:
    keys = [k for k in _cache if k.startswith(prefix)]
    for k in keys:
        del _cache[k]
    return len(keys)
