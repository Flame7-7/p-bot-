"""Replying to a message in your DM shows as a reply in your partner's DM."""
import asyncio
from types import SimpleNamespace

import discord

import database.connection as dbc
from cogs.dmlink.dmlink_cog import DMLinkCog
from tests.fakes import FakeChannel, FakeUser, _Resp


def run(coro):
    return asyncio.run(coro)


async def setup_cog(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "d.db"))
    from utils.config import get_config
    get_config.cache_clear()
    await dbc.init_db()
    monkeypatch.setattr(discord, "DMChannel", FakeChannel)  # the cog checks isinstance(channel, DMChannel)
    a, b = FakeUser(1, "Him"), FakeUser(2, "Her")
    users = {1: a, 2: b}
    bot = SimpleNamespace(get_user=users.get)
    cog = DMLinkCog.__new__(DMLinkCog)
    cog.bot = bot
    from repositories.dm_relay_repository import DMRelayRepository

    class Rel:
        async def get_partner_id(self, uid):
            return 2 if uid == 1 else 1
    cog.rel_repo, cog.links = Rel(), DMRelayRepository()
    return cog, a, b


async def say(cog, user, text, reply_to=None):
    """`user` types `text` in their DM with the bot (optionally as a reply to message `reply_to`)."""
    posted = user.channel.post(content=text)
    msg = SimpleNamespace(
        id=posted.id, author=user, channel=user.channel, content=text, attachments=[],
        reference=SimpleNamespace(message_id=reply_to.id) if reply_to else None,
    )
    await cog.on_message(msg)
    return posted


def relayed(user):
    """The newest message the bot put in this user's DM."""
    return user.channel.messages[-1]


def test_plain_message_is_relayed_without_reference(tmp_path, monkeypatch):
    async def go():
        cog, a, b = await setup_cog(tmp_path, monkeypatch)
        await say(cog, a, "hi")
        copy = relayed(b)
        assert copy.embed.description == "hi" and copy.reference is None
    run(go())


def test_reply_to_partners_message_points_at_their_original(tmp_path, monkeypatch):
    async def go():
        cog, a, b = await setup_cog(tmp_path, monkeypatch)
        b_orig = await say(cog, b, "dinner?")           # Her message; copy lands in Him's DM
        copy_in_a = relayed(a)
        await say(cog, a, "yes!", reply_to=copy_in_a)   # Him replies to the copy
        out = relayed(b)
        assert out.embed.description == "yes!"
        assert out.reference.message_id == b_orig.id and out.reference.channel_id == b.channel.id
        assert out.reference.fail_if_not_exists is False
    run(go())


def test_reply_to_own_message_points_at_its_copy(tmp_path, monkeypatch):
    async def go():
        cog, a, b = await setup_cog(tmp_path, monkeypatch)
        a1 = await say(cog, a, "wait, actually…")
        copy_in_b = relayed(b)
        await say(cog, a, "I meant tomorrow", reply_to=a1)
        out = relayed(b)
        assert out.reference.message_id == copy_in_b.id and out.reference.channel_id == b.channel.id
    run(go())


def test_long_back_and_forth_keeps_threading(tmp_path, monkeypatch):
    async def go():
        cog, a, b = await setup_cog(tmp_path, monkeypatch)
        a1 = await say(cog, a, "one")
        c1 = relayed(b)
        b1 = await say(cog, b, "two", reply_to=c1)       # Her replies to the copy of "one"
        assert relayed(a).reference.message_id == a1.id   # in Him's DM it replies to his own "one"
        d1 = relayed(a)
        await say(cog, a, "three", reply_to=d1)           # Him replies to her reply
        assert relayed(b).reference.message_id == b1.id
    run(go())


def test_unknown_or_unlinked_target_is_sent_normally(tmp_path, monkeypatch):
    async def go():
        cog, a, b = await setup_cog(tmp_path, monkeypatch)
        game_msg = a.channel.post(content="a game message")           # a bot message with no link
        await say(cog, a, "hello", reply_to=game_msg)
        out = relayed(b)
        assert out.embed.description == "hello" and out.reference is None
        ghost = SimpleNamespace(id=999_999)
        await say(cog, a, "ghost", reply_to=ghost)
        assert relayed(b).reference is None
    run(go())


def test_message_still_arrives_if_discord_rejects_the_reference(tmp_path, monkeypatch):
    async def go():
        cog, a, b = await setup_cog(tmp_path, monkeypatch)
        a1 = await say(cog, a, "first")
        b.channel.reject_reference = discord.HTTPException(_Resp(400), "Unknown message")
        await say(cog, a, "second", reply_to=a1)
        out = relayed(b)
        assert out.embed.description == "second" and out.reference is None
    run(go())


def test_links_persist_and_old_ones_are_pruned(tmp_path, monkeypatch):
    async def go():
        cog, a, b = await setup_cog(tmp_path, monkeypatch)
        await say(cog, a, "x")
        from database.connection import get_session
        from sqlalchemy import text
        async with get_session() as s:
            await s.execute(text("UPDATE dm_relay_links SET created_at = datetime('now', '-40 days')"))
        await say(cog, a, "recent")
        assert await cog.links.prune(30) == 1
        async with get_session() as s:
            rows = (await s.execute(text("SELECT count(*) FROM dm_relay_links"))).scalar()
        assert rows == 1
    run(go())


def test_bot_and_guild_messages_are_ignored(tmp_path, monkeypatch):
    async def go():
        cog, a, b = await setup_cog(tmp_path, monkeypatch)
        bot_user = FakeUser(5, "Bot")
        bot_user.bot = True
        await cog.on_message(SimpleNamespace(id=1, author=bot_user, channel=a.channel, content="x", attachments=[], reference=None))
        await cog.on_message(SimpleNamespace(id=2, author=a, channel=object(), content="x", attachments=[], reference=None))
        assert b.channel.messages == []
    run(go())
