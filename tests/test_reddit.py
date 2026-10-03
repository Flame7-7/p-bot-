import asyncio

import aiohttp
import discord
import pytest

import services.reddit_service as rs
from cogs.reddit.reddit_cog import RedditCog, RedditView, build_post_embed, compact
from services.reddit_service import (
    InvalidSubreddit, NoPosts, NsfwBlocked, RateLimited, RedditService, RedditUnavailable,
    SubredditNotFound, SubredditUnavailable, normalise_subreddit, parse_post,
)
from tests.fakes import FakeInteraction, FakeUser
from utils.cooldowns import cache_delete_prefix


def run(coro):
    return asyncio.run(coro)


# ── fake HTTP ────────────────────────────────────────────────────────────────

class FakeResp:
    def __init__(self, status=200, body=None, headers=None, bad_json=False):
        self.status, self.body, self.headers, self.bad_json = status, body, headers or {}, bad_json

    async def json(self, content_type=None):
        if self.bad_json:
            raise ValueError("not json")
        return self.body

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False


class FakeSession:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []
        self.delay = 0.0

    def _next(self, method, url, kw):
        self.calls.append((method, url, kw))
        r = self.responses[0] if len(self.responses) == 1 else self.responses.pop(0)
        if isinstance(r, Exception):
            raise r
        return r

    def get(self, url, **kw):
        return self._ctx("GET", url, kw)

    def post(self, url, **kw):
        return self._ctx("POST", url, kw)

    def _ctx(self, method, url, kw):
        session = self

        class Ctx:
            async def __aenter__(self_inner):
                if session.delay:
                    await asyncio.sleep(session.delay)
                return session._next(method, url, kw)

            async def __aexit__(self_inner, *a):
                return False
        return Ctx()


def child(**kw):
    d = {"id": kw.pop("id", "a1"), "title": "Title &amp; more", "author": "alice", "score": 12400, "num_comments": 324,
         "permalink": "/r/cats/comments/a1/x/", "subreddit": "cats", "over_18": False, "url": "https://example.com/a",
         "is_self": False, "is_video": False}
    d.update(kw)
    return {"kind": "t3", "data": d}


def listing(*children):
    return FakeResp(200, {"data": {"children": list(children)}})


IMAGE = child(id="img", url="https://i.redd.it/x.jpg", post_hint="image")
TEXT = child(id="txt", is_self=True, selftext="hello there " * 60, url="https://reddit.com/r/cats/comments/txt")
VIDEO = child(id="vid", is_video=True, url="https://v.redd.it/abc", preview={"images": [{"source": {"url": "https://preview.redd.it/p.jpg?a=1&amp;b=2"}}]})
LINK = child(id="lnk", url="https://news.example.com/story", thumbnail="https://b.thumbs.redditmedia.com/t.jpg")
GALLERY = child(id="gal", is_gallery=True, url="https://www.reddit.com/gallery/gal", media_metadata={"m1": {"status": "valid", "s": {"u": "https://preview.redd.it/g.jpg?x=1&amp;y=2"}}})
REMOVED = child(id="rem", removed_by_category="moderator")
REMOVED_TEXT = child(id="rem2", is_self=True, selftext="[removed]")
NSFW = child(id="nsfw", over_18=True, url="https://i.redd.it/n.jpg", post_hint="image")


@pytest.fixture(autouse=True)
def clean(monkeypatch):
    cache_delete_prefix("reddit:")
    monkeypatch.delenv("REDDIT_CLIENT_ID", raising=False)
    monkeypatch.delenv("REDDIT_CLIENT_SECRET", raising=False)
    from utils.config import get_config
    get_config.cache_clear()
    yield
    cache_delete_prefix("reddit:")
    get_config.cache_clear()


def use(monkeypatch, session):
    monkeypatch.setattr(rs, "get_http_session", lambda: session)
    return session


async def posts(svc, sub="cats", **kw):
    return await svc.get_posts(sub, **kw)


# ── parsing ──────────────────────────────────────────────────────────────────

def test_post_kinds_and_cleanup():
    img, txt, vid, lnk, gal = (parse_post(c) for c in (IMAGE, TEXT, VIDEO, LINK, GALLERY))
    assert img.kind == "image" and img.image_url == "https://i.redd.it/x.jpg"
    assert txt.kind == "text" and txt.image_url is None and txt.text.startswith("hello")
    assert vid.kind == "video" and vid.image_url == "https://preview.redd.it/p.jpg?a=1&b=2", "preview unescaped"
    assert lnk.kind == "link" and lnk.url == "https://news.example.com/story"
    assert gal.kind == "image" and gal.image_url == "https://preview.redd.it/g.jpg?x=1&y=2"
    assert img.title == "Title & more" and img.permalink == "https://www.reddit.com/r/cats/comments/a1/x/"


def test_removed_and_deleted_posts_are_dropped():
    assert parse_post(REMOVED) is None and parse_post(REMOVED_TEXT) is None
    assert parse_post({"kind": "t3", "data": {"id": "x"}}) is None
    assert parse_post({"kind": "t1", "data": {"id": "x", "title": "c"}}) is None
    assert parse_post(child(quarantine=True)) is None


def test_subreddit_name_validation():
    assert normalise_subreddit("r/Cats") == "Cats" and normalise_subreddit(" /r/cats/ ") == "cats"
    for bad in ("", "a", "has space", "semi;colon", "x" * 22, "../etc", "r/"):
        with pytest.raises(InvalidSubreddit):
            normalise_subreddit(bad)


def test_compact_numbers():
    assert [compact(n) for n in (7, 999, 1000, 12400, 15_000, 1_500_000)] == ["7", "999", "1k", "12.4k", "15k", "1.5m"]


# ── service behaviour ────────────────────────────────────────────────────────

def test_valid_subreddit_returns_usable_posts(monkeypatch):
    async def go():
        sess = use(monkeypatch, FakeSession(listing(IMAGE, TEXT, VIDEO, LINK, REMOVED, REMOVED_TEXT)))
        got = await posts(RedditService())
        assert [p.id for p in got] == ["img", "txt", "vid", "lnk"]
        method, url, kw = sess.calls[0]
        assert url == "https://www.reddit.com/r/cats/hot.json" and "User-Agent" in kw["headers"]
        assert kw["allow_redirects"] is False and kw["timeout"].total == 10
    run(go())


@pytest.mark.parametrize("resp,exc", [
    (FakeResp(404), SubredditNotFound),
    (FakeResp(302, headers={"location": "/subreddits/search?q=nope"}), SubredditNotFound),
    (FakeResp(403, {"reason": "private"}), SubredditUnavailable),
    (FakeResp(500), RedditUnavailable),
    (FakeResp(503), RedditUnavailable),
    (FakeResp(200, bad_json=True), RedditUnavailable),
    (FakeResp(418), RedditUnavailable),
    (listing(), NoPosts),
    (listing(REMOVED, REMOVED_TEXT), NoPosts),
    (asyncio.TimeoutError(), RedditUnavailable),
    (aiohttp.ClientConnectionError("boom"), RedditUnavailable),
])
def test_failure_modes_give_clean_errors(monkeypatch, resp, exc):
    async def go():
        use(monkeypatch, FakeSession(resp))
        with pytest.raises(exc) as info:
            await posts(RedditService())
        assert info.value.user_message and "Traceback" not in info.value.user_message
    run(go())


def test_rate_limit_backs_off_without_hammering(monkeypatch):
    async def go():
        sess = use(monkeypatch, FakeSession(FakeResp(429, headers={"retry-after": "30"})))
        svc = RedditService()
        with pytest.raises(RateLimited):
            await posts(svc)
        assert len(sess.calls) == 1
        for _ in range(3):
            with pytest.raises(RateLimited):
                await posts(svc, "dogs")           # different key, but still blocked: no network
        assert len(sess.calls) == 1
    run(go())


def test_rate_limit_headers_pre_emptively_pause(monkeypatch):
    async def go():
        sess = use(monkeypatch, FakeSession(FakeResp(200, {"data": {"children": [IMAGE]}}, headers={"x-ratelimit-remaining": "0", "x-ratelimit-reset": "40"})))
        svc = RedditService()
        await posts(svc)
        with pytest.raises(RateLimited):
            await posts(svc, "dogs")
        assert len(sess.calls) == 1
    run(go())


def test_nsfw_rules(monkeypatch):
    async def go():
        use(monkeypatch, FakeSession(listing(IMAGE, NSFW)))
        svc = RedditService()
        safe = await posts(svc, allow_nsfw=False)
        assert [p.id for p in safe] == ["img"]
        both = await posts(svc, allow_nsfw=True)           # same cached listing, no refetch
        assert {p.id for p in both} == {"img", "nsfw"}
        cache_delete_prefix("reddit:")
        use(monkeypatch, FakeSession(listing(NSFW)))
        with pytest.raises(NsfwBlocked):
            await posts(RedditService(), "nsfwsub", allow_nsfw=False)
    run(go())


def test_cache_and_single_flight(monkeypatch):
    async def go():
        sess = use(monkeypatch, FakeSession(listing(IMAGE, TEXT)))
        sess.delay = 0.05
        svc = RedditService()
        await asyncio.gather(*[posts(svc) for _ in range(6)])
        assert len(sess.calls) == 1, "six simultaneous requests share one HTTP call"
        for _ in range(10):
            await posts(svc)
        assert len(sess.calls) == 1, "cached"
        await posts(svc, sort="new")
        assert len(sess.calls) == 2
        await posts(svc, sort="top", timeframe="all")
        assert sess.calls[-1][2]["params"]["t"] == "all"
        await posts(svc, "CATS")                           # name case doesn't bypass the cache
        assert len(sess.calls) == 3
    run(go())


def test_oauth_flow_with_credentials(monkeypatch):
    async def go():
        monkeypatch.setenv("REDDIT_CLIENT_ID", "cid")
        monkeypatch.setenv("REDDIT_CLIENT_SECRET", "sec")
        monkeypatch.setenv("REDDIT_USER_AGENT", "python:p-bot:1.0 (by /u/me)")
        from utils.config import get_config
        get_config.cache_clear()
        sess = use(monkeypatch, FakeSession(
            FakeResp(200, {"access_token": "tok123", "expires_in": 3600}),
            listing(IMAGE),
            listing(TEXT),
        ))
        svc = RedditService()
        await posts(svc)
        await posts(svc, "dogs")
        token_call, first, second = sess.calls
        assert token_call[0] == "POST" and token_call[1] == rs.TOKEN_URL
        assert token_call[2]["headers"]["Authorization"].startswith("Basic ")
        assert first[1] == "https://oauth.reddit.com/r/cats/hot"
        assert first[2]["headers"]["Authorization"] == "bearer tok123"
        assert first[2]["headers"]["User-Agent"] == "python:p-bot:1.0 (by /u/me)"
        assert len(sess.calls) == 3, "token reused for the second subreddit"
    run(go())


def test_bad_credentials_give_clean_error_without_leaking(monkeypatch):
    async def go():
        monkeypatch.setenv("REDDIT_CLIENT_ID", "cid")
        monkeypatch.setenv("REDDIT_CLIENT_SECRET", "topsecret")
        from utils.config import get_config
        get_config.cache_clear()
        use(monkeypatch, FakeSession(FakeResp(401)))
        with pytest.raises(RedditUnavailable) as info:
            await posts(RedditService())
        assert "topsecret" not in info.value.user_message and "credentials" in info.value.user_message
    run(go())


def test_no_credentials_in_source():
    import pathlib
    src = pathlib.Path(rs.__file__).read_text() + pathlib.Path("cogs/reddit/reddit_cog.py").read_text()
    assert "client_secret=" not in src.lower() and "REDDIT_CLIENT_SECRET" not in src


# ── cog ──────────────────────────────────────────────────────────────────────

class StubService:
    def __init__(self, result):
        self.result, self.calls = result, []

    async def get_posts(self, name, sort, timeframe, *, allow_nsfw):
        self.calls.append((name, sort, timeframe, allow_nsfw))
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def make_cog(result):
    from discord.ext import commands
    stub = StubService(result)
    return RedditCog(commands.Bot(command_prefix="!", intents=discord.Intents.none()), stub), stub


def parsed(*children):
    return [parse_post(c) for c in children]


class Choice:
    def __init__(self, v):
        self.value = v


def test_command_shows_embed_with_fields_and_image_in_dm():
    async def go():
        cog, stub = make_cog(parsed(IMAGE, TEXT, VIDEO))
        inter = FakeInteraction(FakeUser(1, "Him"))
        await RedditCog.reddit.callback(cog, inter, "r/cats", None, None)
        sent = inter.response.sent[-1]
        embed = sent["embed"]
        assert embed.title == "Title & more" and embed.url.startswith("https://www.reddit.com/r/cats")
        assert embed.image.url == "https://i.redd.it/x.jpg" and embed.author.name == "r/cats"
        fields = {f.name: f.value for f in embed.fields}
        assert fields["⬆️ Upvotes"] == "12.4k" and fields["💬 Comments"] == "324" and fields["👤 Author"] == "u/alice"
        assert stub.calls == [("cats", "hot", "week", False)], "DMs never allow NSFW"
        labels = [getattr(c, "label", None) for c in sent["view"].children]
        assert {"Previous", "Next", "Random", "View Post"} <= set(labels)
    run(go())


def test_command_options_and_nsfw_channel():
    async def go():
        cog, stub = make_cog(parsed(IMAGE))
        inter = FakeInteraction(FakeUser(1, "Him"))
        inter.guild = object()
        inter.channel = type("Ch", (), {"is_nsfw": lambda self: True})()
        await RedditCog.reddit.callback(cog, inter, "cats", Choice("top"), Choice("month"))
        assert stub.calls == [("cats", "top", "month", True)]
        inter2 = FakeInteraction(FakeUser(1, "Him"))
        inter2.guild = object()
        inter2.channel = type("Ch", (), {"is_nsfw": lambda self: False})()
        await RedditCog.reddit.callback(cog, inter2, "cats", Choice("random"), None)
        assert stub.calls[-1] == ("cats", "hot", "week", False), "random picks from hot; SFW channel stays SFW"
    run(go())


@pytest.mark.parametrize("err,needle", [
    (SubredditNotFound(), "couldn't find"), (SubredditUnavailable(), "private"), (RateLimited(), "rate-limiting"),
    (RedditUnavailable(), "isn't responding"), (NsfwBlocked(), "age-restricted"), (NoPosts(), "nothing I can show"),
    (InvalidSubreddit(), "doesn't look like"), (RuntimeError("secret db path /etc"), "went wrong"),
])
def test_command_errors_are_friendly(err, needle):
    async def go():
        cog, _ = make_cog(err)
        inter = FakeInteraction(FakeUser(1, "Him"))
        await RedditCog.reddit.callback(cog, inter, "cats", None, None)
        msg = inter.response.sent[-1]["content"]
        assert needle in msg and "secret" not in msg and "Traceback" not in msg
    run(go())


def test_invalid_name_never_reaches_the_service():
    async def go():
        cog, stub = make_cog(parsed(IMAGE))
        inter = FakeInteraction(FakeUser(1, "Him"))
        await RedditCog.reddit.callback(cog, inter, "not a sub!", None, None)
        assert stub.calls == [] and "doesn't look like" in inter.response.sent[-1]["content"]
    run(go())


def test_view_navigation_uses_cached_posts_only():
    async def go():
        data = parsed(IMAGE, TEXT, VIDEO, LINK)
        me = FakeUser(1, "Him")
        view = RedditView(me.id, data)
        msg = me.channel.post()

        def press(label):
            btn = next(c for c in view.children if getattr(c, "label", None) == label)
            inter = FakeInteraction(me, msg)
            return btn, inter

        assert view.index == 0 and next(c for c in view.children if c.label == "Previous").disabled
        btn, inter = press("Next")
        await btn.callback(inter)
        assert view.index == 1 and msg.embed.title.startswith("Title") and "2/4" in msg.embed.footer.text
        for _ in range(5):
            btn, inter = press("Next") if not next(c for c in view.children if c.label == "Next").disabled else (None, None)
            if btn:
                await btn.callback(inter)
        assert view.index == 3 and next(c for c in view.children if c.label == "Next").disabled
        btn, inter = press("Previous")
        await btn.callback(inter)
        assert view.index == 2
        seen = set()
        for _ in range(30):
            btn, inter = press("Random")
            before = view.index
            await btn.callback(inter)
            assert view.index != before
            seen.add(view.index)
        assert len(seen) >= 3
        link = next(c for c in view.children if getattr(c, "url", None))
        assert link.url == view.post.permalink and len([c for c in view.children if getattr(c, "url", None)]) == 1
        assert await view.interaction_check(FakeInteraction(FakeUser(9, "Other"), msg)) is False
    run(go())


def test_embed_for_each_post_kind_and_missing_image():
    imgs = parsed(IMAGE, TEXT, VIDEO, LINK, child(id="noimg", url="https://example.com/x"))
    img, txt, vid, lnk, bare = (build_post_embed(p, 1, 5) for p in imgs)
    assert img.image.url and not img.description
    assert txt.description.endswith("…") and len(txt.description) <= 351 and not txt.image.url
    assert "Video post" in vid.description and vid.image.url
    assert lnk.description.startswith("🔗") and lnk.image.url
    assert bare.description.startswith("🔗") and not bare.image.url, "missing preview image is fine"
