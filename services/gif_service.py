from __future__ import annotations

import random
import aiohttp

from database.connection import get_session
from models.models import GIF
from utils.cooldowns import cache_get, cache_set
from utils.config import get_config
from utils.logging import get_logger
from sqlalchemy import select

logger = get_logger(__name__)

# One shared session reused for every Tenor request for the life of the
# process, instead of `async with aiohttp.ClientSession()` per call. The
# old version wasn't technically leaking (the `async with` did close each
# one), but spinning up a brand new TCP/TLS session for every single
# fallback lookup is wasteful, especially on a low-RAM free host. Closed
# once in main.py's close() via close_http_session().
_http_session: aiohttp.ClientSession | None = None


def get_http_session() -> aiohttp.ClientSession:
    global _http_session
    if _http_session is None or _http_session.closed:
        _http_session = aiohttp.ClientSession()
    return _http_session


async def close_http_session() -> None:
    global _http_session
    if _http_session and not _http_session.closed:
        await _http_session.close()
    _http_session = None


class GifService:
    def __init__(self) -> None:
        self.config = get_config()

    async def get_random_gif(self, category: str) -> str | None:
        cache_key = f"gifs:{category}"
        cached = cache_get(cache_key)
        if cached and isinstance(cached, list) and cached:
            return self._weighted_choice(cached)

        async with get_session() as session:
            result = await session.execute(
                select(GIF)
                .where(GIF.category == category, GIF.is_disabled == False)
            )
            gifs = result.scalars().all()

        if gifs:
            data = [{"url": g.url, "weight": g.weight} for g in gifs]
            cache_set(cache_key, data, ttl=3600)
            return self._weighted_choice(data)

        # Tenor fallback
        if self.config.tenor_api_key:
            url = await self._fetch_tenor(category)
            if url:
                return url

        return None

    def _weighted_choice(self, gifs: list[dict]) -> str:
        weights = [g.get("weight", 1.0) for g in gifs]
        return random.choices(gifs, weights=weights, k=1)[0]["url"]

    async def _fetch_tenor(self, category: str) -> str | None:
        try:
            params = {
                "q": f"anime {category}",
                "key": self.config.tenor_api_key,
                "limit": 10,
                "media_filter": "gif",
            }
            session = get_http_session()
            async with session.get(
                "https://tenor.googleapis.com/v2/search",
                params=params,
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    results = data.get("results", [])
                    if results:
                        return random.choice(results)["media_formats"]["gif"]["url"]
        except Exception as e:
            logger.warning("tenor fetch failed for %s: %s", category, e)
        return None

    async def gif_exists(self, category: str, url: str) -> bool:
        """Used by bulk-add so pasting the same link twice (or re-pasting
        a batch that partly succeeded) doesn't pile up duplicate rows --
        the `gifs` table has no unique constraint at the DB level."""
        async with get_session() as session:
            result = await session.execute(
                select(GIF.id).where(GIF.category == category, GIF.url == url)
            )
            return result.scalar_one_or_none() is not None

    async def add_gif(
        self, category: str, url: str, name: str | None = None, weight: float = 1.0
    ) -> GIF:
        async with get_session() as session:
            gif = GIF(
                category=category, url=url, name=name, weight=weight, source="manual"
            )
            session.add(gif)
            await session.flush()
            await session.refresh(gif)
        # Bust cache
        from utils.cooldowns import cache_delete
        cache_delete(f"gifs:{category}")
        return gif