from __future__ import annotations

import random
from dataclasses import dataclass

import aiohttp

from utils.http import get_http_session
from utils.config import get_config
from utils.cooldowns import cache_get, cache_set
from utils.logging import get_logger

logger = get_logger(__name__)

TMDB_BASE = "https://api.themoviedb.org/3"
TMDB_POSTER_BASE = "https://image.tmdb.org/t/p/w500"
TMDB_MAX_PAGE = 500  # TMDB's own hard cap on paginated results

# Official TMDB movie genre IDs -- static, TMDB doesn't rename/renumber
# these, so no need to hit the /genre/movie/list endpoint at runtime.
GENRES: dict[str, int] = {
    "Action": 28,
    "Adventure": 12,
    "Animation": 16,
    "Comedy": 35,
    "Crime": 80,
    "Documentary": 99,
    "Drama": 18,
    "Family": 10751,
    "Fantasy": 14,
    "History": 36,
    "Horror": 27,
    "Music": 10402,
    "Mystery": 9648,
    "Romance": 10749,
    "Science Fiction": 878,
    "TV Movie": 10770,
    "Thriller": 53,
    "War": 10752,
    "Western": 37,
}


@dataclass
class Movie:
    title: str
    overview: str
    release_date: str | None
    vote_average: float
    vote_count: int
    poster_url: str | None
    tmdb_url: str


class MovieService:
    def __init__(self) -> None:
        self.config = get_config()

    @property
    def enabled(self) -> bool:
        return bool(self.config.tmdb_api_key)

    async def random_movie(self, genre: str | None = None) -> Movie | None:
        """Fetch a random reasonably-well-known movie, optionally filtered
        by genre name (must be a key in GENRES). Returns None if the API
        isn't configured or nothing suitable was found."""
        if not self.enabled:
            return None

        genre_id = GENRES.get(genre) if genre else None
        total_pages = await self._get_total_pages(genre_id)
        if total_pages <= 0:
            return None

        page = random.randint(1, min(total_pages, TMDB_MAX_PAGE))
        results = await self._discover(genre_id, page)
        if not results:
            # Page count is cached and can go stale; one retry on page 1
            # covers the common case of a genre with very few results.
            results = await self._discover(genre_id, 1)
        if not results:
            return None

        pick = random.choice(results)
        poster_path = pick.get("poster_path")
        return Movie(
            title=pick.get("title") or "Unknown title",
            overview=(pick.get("overview") or "No synopsis available.").strip(),
            release_date=pick.get("release_date") or None,
            vote_average=float(pick.get("vote_average") or 0.0),
            vote_count=int(pick.get("vote_count") or 0),
            poster_url=f"{TMDB_POSTER_BASE}{poster_path}" if poster_path else None,
            tmdb_url=f"https://www.themoviedb.org/movie/{pick.get('id')}",
        )

    async def _get_total_pages(self, genre_id: int | None) -> int:
        cache_key = f"movie:total_pages:{genre_id}"
        cached = cache_get(cache_key)
        if isinstance(cached, int):
            return cached

        data = await self._discover_raw(genre_id, page=1)
        total_pages = int(data.get("total_pages") or 0) if data else 0
        cache_set(cache_key, total_pages, ttl=3600)
        return total_pages

    async def _discover(self, genre_id: int | None, page: int) -> list[dict]:
        data = await self._discover_raw(genre_id, page)
        return data.get("results", []) if data else []

    async def _discover_raw(self, genre_id: int | None, page: int) -> dict | None:
        params = {
            "api_key": self.config.tmdb_api_key,
            "sort_by": "popularity.desc",
            "vote_count.gte": "100",
            "include_adult": "false",
            "page": str(page),
        }
        if genre_id:
            params["with_genres"] = str(genre_id)

        try:
            session = get_http_session()
            async with session.get(
                f"{TMDB_BASE}/discover/movie",
                params=params,
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                logger.warning("tmdb discover failed: status=%s", resp.status)
        except Exception as e:
            logger.warning("tmdb discover error: %s", e)
        return None
