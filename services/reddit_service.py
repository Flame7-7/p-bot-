"""Reddit client: official API (OAuth app-only) with a public-JSON fallback.

Isolated from Discord on purpose — nothing here imports discord. The cog asks for posts,
this module deals with auth, caching, rate limits, filtering and Reddit's quirks.
"""
from __future__ import annotations

import asyncio
import base64
import html
import random
import re
import time
import uuid
from dataclasses import dataclass, field
from urllib.parse import urlparse

import aiohttp

from utils.config import get_config
from utils.cooldowns import cache_get, cache_set
from utils.http import get_http_session
from utils.logging import get_logger

logger = get_logger(__name__)

OAUTH_BASE = "https://oauth.reddit.com"
PUBLIC_BASE = "https://www.reddit.com"
TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=10)
LISTING_TTL = 300          # seconds a fetched listing is reused (buttons never hit the API)
LISTING_LIMIT = 50
SUBREDDIT_RE = re.compile(r"^[A-Za-z0-9_]{2,21}$")
IMAGE_EXT = (".jpg", ".jpeg", ".png", ".gif", ".webp")
SORTS = ("hot", "new", "top")
TIMEFRAMES = ("hour", "day", "week", "month", "year", "all")


# ── errors (each carries a message that is safe to show to a user) ──────────

class RedditError(Exception):
    user_message = "Reddit isn't working right now. Try again in a bit."

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.user_message)
        self.user_message = message or self.user_message


class InvalidSubreddit(RedditError):
    user_message = "That doesn't look like a subreddit name (letters, numbers and underscores, 2–21 characters)."


class SubredditNotFound(RedditError):
    user_message = "I couldn't find that subreddit."


class SubredditUnavailable(RedditError):
    user_message = "That subreddit is private, banned or quarantined, so I can't show it."


class NsfwBlocked(RedditError):
    user_message = "That subreddit is age-restricted. I only show those in age-restricted channels — never in DMs."


class RateLimited(RedditError):
    user_message = "Reddit is rate-limiting me. Try again in a minute."


class RedditUnavailable(RedditError):
    user_message = "Reddit isn't responding right now. Try again in a bit."


class NoPosts(RedditError):
    user_message = "There's nothing I can show from that subreddit right now."


# ── data ─────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class RedditPost:
    id: str
    subreddit: str
    title: str
    author: str
    score: int
    num_comments: int
    permalink: str                 # full https URL of the Reddit thread
    url: str                       # what the post links to
    over_18: bool
    kind: str                      # "image" | "video" | "text" | "link"
    image_url: str | None = None
    text: str = ""
    flair: str | None = None
    spoiler: bool = False


@dataclass
class _Token:
    value: str
    expires_at: float


@dataclass
class _State:
    token: _Token | None = None
    blocked_until: float = 0.0
    inflight: dict[str, asyncio.Task] = field(default_factory=dict)


def normalise_subreddit(raw: str) -> str:
    """'r/Cats', '/r/cats/', ' cats ' → 'cats'. Raises InvalidSubreddit."""
    name = raw.strip().strip("/")
    for prefix in ("r/", "R/"):
        if name.startswith(prefix):
            name = name[len(prefix):]
    name = name.strip("/")
    if not SUBREDDIT_RE.match(name):
        raise InvalidSubreddit()
    return name


def _clean(url: str | None) -> str | None:
    return html.unescape(url) if url else None


def _first_image(d: dict) -> str | None:
    """Best direct image for a post, or None."""
    url = _clean(d.get("url_overridden_by_dest") or d.get("url"))
    if url and urlparse(url).path.lower().endswith(IMAGE_EXT):
        return url
    if d.get("is_gallery") and d.get("media_metadata"):
        for item in d["media_metadata"].values():
            if item.get("status") == "valid" and item.get("s", {}).get("u"):
                return _clean(item["s"]["u"])
    previews = (d.get("preview") or {}).get("images") or []
    if previews and previews[0].get("source", {}).get("url"):
        return _clean(previews[0]["source"]["url"])
    thumb = d.get("thumbnail")
    if thumb and thumb.startswith("http"):
        return _clean(thumb)
    return None


def parse_post(child: dict) -> RedditPost | None:
    """Turn one listing child into a RedditPost; None for removed/deleted/unusable posts."""
    d = child.get("data") or {}
    if child.get("kind") not in (None, "t3") or not d.get("id") or not d.get("title"):
        return None
    if d.get("removed_by_category") or d.get("quarantine") or d.get("selftext") in ("[removed]", "[deleted]"):
        return None

    is_video = bool(d.get("is_video") or d.get("post_hint") in ("hosted:video", "rich:video"))
    direct = _first_image(d) if not is_video else None
    is_image = bool(direct) and (
        d.get("post_hint") == "image" or d.get("is_gallery") or urlparse(d.get("url") or "").path.lower().endswith(IMAGE_EXT)
    )
    if is_video:
        kind = "video"
    elif is_image:
        kind = "image"
    elif d.get("is_self"):
        kind = "text"
    else:
        kind = "link"

    preview = direct if kind != "video" else _first_image({"preview": d.get("preview"), "thumbnail": d.get("thumbnail")})
    return RedditPost(
        id=d["id"],
        subreddit=d.get("subreddit") or "",
        title=html.unescape(d["title"]),
        author=d.get("author") or "[deleted]",
        score=int(d.get("score") or 0),
        num_comments=int(d.get("num_comments") or 0),
        permalink=f"{PUBLIC_BASE}{d.get('permalink', '')}",
        url=_clean(d.get("url_overridden_by_dest") or d.get("url")) or f"{PUBLIC_BASE}{d.get('permalink', '')}",
        over_18=bool(d.get("over_18")),
        kind=kind,
        image_url=preview,
        text=html.unescape(d.get("selftext") or ""),
        flair=d.get("link_flair_text") or None,
        spoiler=bool(d.get("spoiler")),
    )


def filter_posts(posts: list[RedditPost], *, allow_nsfw: bool) -> list[RedditPost]:
    return [p for p in posts if allow_nsfw or not p.over_18]


class RedditService:
    """One instance per process. Safe for concurrent use."""

    def __init__(self) -> None:
        self._state = _State()
        self._token_lock = asyncio.Lock()

    # ── public API ───────────────────────────────────────────────────────────

    async def get_posts(
        self, subreddit: str, sort: str = "hot", timeframe: str = "week", *, allow_nsfw: bool = False
    ) -> list[RedditPost]:
        """Posts the caller may show, newest listing cached for LISTING_TTL seconds."""
        name = normalise_subreddit(subreddit)
        sort = sort if sort in SORTS else "hot"
        timeframe = timeframe if timeframe in TIMEFRAMES else "week"

        key = f"reddit:{name.lower()}:{sort}:{timeframe if sort == 'top' else '-'}"
        posts = cache_get(key)
        if posts is None:
            posts = await self._fetch_shared(key, name, sort, timeframe)
            cache_set(key, posts, ttl=LISTING_TTL)

        visible = filter_posts(posts, allow_nsfw=allow_nsfw)  # type: ignore[arg-type]
        if not visible:
            if posts and not allow_nsfw:
                raise NsfwBlocked()
            raise NoPosts()
        return visible

    async def random_post(self, subreddit: str, *, allow_nsfw: bool = False) -> RedditPost:
        return random.choice(await self.get_posts(subreddit, "hot", allow_nsfw=allow_nsfw))

    # ── internals ────────────────────────────────────────────────────────────

    async def _fetch_shared(self, key: str, name: str, sort: str, timeframe: str) -> list[RedditPost]:
        """Concurrent identical requests share one HTTP call."""
        inflight = self._state.inflight
        task = inflight.get(key)
        if task is None:
            task = asyncio.create_task(self._fetch(name, sort, timeframe))
            inflight[key] = task
            task.add_done_callback(lambda _t, k=key: inflight.pop(k, None))
        return await asyncio.shield(task)

    def _credentials(self) -> tuple[str, str] | None:
        cfg = get_config()
        if cfg.reddit_client_id and cfg.reddit_client_secret:
            return cfg.reddit_client_id, cfg.reddit_client_secret
        return None

    async def _get_token(self) -> str | None:
        creds = self._credentials()
        if creds is None:
            return None
        async with self._token_lock:
            tok = self._state.token
            if tok and tok.expires_at - 60 > time.monotonic():
                return tok.value
            basic = base64.b64encode(f"{creds[0]}:{creds[1]}".encode()).decode()
            try:
                async with get_http_session().post(
                    TOKEN_URL,
                    data={"grant_type": "client_credentials", "device_id": str(uuid.uuid4())},
                    headers={"Authorization": f"Basic {basic}", "User-Agent": get_config().reddit_user_agent},
                    timeout=REQUEST_TIMEOUT,
                ) as resp:
                    if resp.status in (401, 403):
                        logger.error("reddit rejected the configured credentials (HTTP %s)", resp.status)
                        raise RedditUnavailable("Reddit rejected my login. The owner needs to check the Reddit credentials.")
                    if resp.status == 429:
                        raise RateLimited()
                    if resp.status != 200:
                        raise RedditUnavailable()
                    data = await resp.json()
            except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
                logger.warning("reddit token request failed: %r", exc)
                raise RedditUnavailable() from exc
            token = data.get("access_token")
            if not token:
                raise RedditUnavailable()
            self._state.token = _Token(token, time.monotonic() + int(data.get("expires_in", 3600)))
            return token

    async def _fetch(self, name: str, sort: str, timeframe: str) -> list[RedditPost]:
        now = time.monotonic()
        if now < self._state.blocked_until:
            raise RateLimited()

        token = await self._get_token()
        base = OAUTH_BASE if token else PUBLIC_BASE
        headers = {"User-Agent": get_config().reddit_user_agent}
        if token:
            headers["Authorization"] = f"bearer {token}"
        suffix = "" if token else ".json"
        params = {"limit": str(LISTING_LIMIT), "raw_json": "1"}
        if sort == "top":
            params["t"] = timeframe

        try:
            async with get_http_session().get(
                f"{base}/r/{name}/{sort}{suffix}",
                params=params,
                headers=headers,
                timeout=REQUEST_TIMEOUT,
                allow_redirects=False,
            ) as resp:
                self._note_rate_limit(resp)
                status = resp.status
                if status in (301, 302, 303, 307, 308):
                    # Reddit redirects unknown subreddit names to its search page.
                    raise SubredditNotFound()
                if status == 404:
                    raise SubredditNotFound()
                if status == 403:
                    raise SubredditUnavailable()
                if status == 429:
                    raise RateLimited()
                if status >= 500 or status in (401, 408):
                    if status == 401:
                        self._state.token = None
                    raise RedditUnavailable()
                if status != 200:
                    logger.warning("unexpected reddit status %s for r/%s", status, name)
                    raise RedditUnavailable()
                data = await resp.json(content_type=None)
        except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
            logger.warning("reddit request failed: %r", exc)
            raise RedditUnavailable() from exc
        except ValueError as exc:  # invalid JSON
            raise RedditUnavailable() from exc

        children = (data.get("data") or {}).get("children") or []
        posts = [p for p in (parse_post(c) for c in children) if p is not None]
        if not posts:
            raise NoPosts()
        return posts

    def _note_rate_limit(self, resp: aiohttp.ClientResponse) -> None:
        """Honour Reddit's rate-limit headers so we back off before being blocked."""
        try:
            remaining = float(resp.headers.get("x-ratelimit-remaining", "1"))
            reset = float(resp.headers.get("x-ratelimit-reset", "0"))
        except ValueError:
            return
        retry = resp.headers.get("retry-after")
        if resp.status == 429:
            wait = float(retry) if retry and retry.replace(".", "", 1).isdigit() else (reset or 60.0)
            self._state.blocked_until = time.monotonic() + min(max(wait, 5.0), 600.0)
        elif remaining < 1 and reset > 0:
            self._state.blocked_until = time.monotonic() + min(reset, 600.0)


_service: RedditService | None = None


def get_reddit_service() -> RedditService:
    global _service
    if _service is None:
        _service = RedditService()
    return _service
