from __future__ import annotations

import aiohttp

# One shared session for the life of the process (Tenor, TMDB, Groq). Closed
# once from RoleplayBot.close().
_session: aiohttp.ClientSession | None = None


def get_http_session() -> aiohttp.ClientSession:
    global _session
    if _session is None or _session.closed:
        _session = aiohttp.ClientSession()
    return _session


async def close_http_session() -> None:
    global _session
    if _session and not _session.closed:
        await _session.close()
    _session = None
