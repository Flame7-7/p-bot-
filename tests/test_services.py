import asyncio
from datetime import date, datetime
from types import SimpleNamespace

import database.connection as dbc


def run(coro):
    return asyncio.run(coro)


async def fresh_db(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "s.db"))
    from utils.config import get_config
    get_config.cache_clear()
    dbc._engine = None
    await dbc.init_db()


def member(uid, name):
    return SimpleNamespace(id=uid, display_name=name, name=name, mention=f"<@{uid}>",
                           display_avatar=SimpleNamespace(url="http://x/a.png"), bot=False)


def test_roleplay_action_end_to_end(tmp_path, monkeypatch):
    async def go():
        await fresh_db(tmp_path, monkeypatch)
        from services.roleplay_service import RoleplayService
        svc = RoleplayService()
        res = await svc.execute("hug", member(1, "Him"), member(2, "Her"), 10)
        assert not isinstance(res, str), res
        for _ in range(5):  # no cooldown: the same action can be repeated immediately
            again = await svc.execute("hug", member(1, "Him"), member(2, "Her"), 10)
            assert not isinstance(again, str), again
        missing = await svc.execute("hug", member(1, "Him"), None, 10)
        assert isinstance(missing, str)
        assert isinstance(await svc.execute("nonexistent", member(1, "Him"), member(2, "Her"), 10), str)
    run(go())


def test_couple_repository_stats_milestones_journal(tmp_path, monkeypatch):
    async def go():
        await fresh_db(tmp_path, monkeypatch)
        from repositories.couple_repository import CoupleRepository
        r = CoupleRepository()
        await r.record_game(5, 3, "tictactoe", winner=5)
        await r.record_game(3, 5, "tictactoe", winner=3)
        await r.record_game(3, 5, "tictactoe", draw=True)
        await r.record_game(3, 5, "compat", points=80)
        stats = {s.game: s for s in await r.get_stats(5, 3)}
        t = stats["tictactoe"]
        assert (t.plays, t.low_wins, t.high_wins, t.draws) == (3, 1, 1, 1)  # same row regardless of who asks
        assert stats["compat"].points == 80
        m = await r.add_milestone(5, 3, "First date", datetime(2025, 2, 14), True, 5)
        assert len(await r.list_milestones(3, 5)) == 1
        assert not await r.remove_milestone(5, 99, m.id)  # another couple can't delete it
        assert await r.remove_milestone(3, 5, m.id)
        await r.add_journal(5, 3, 5, "hello", "prompt")
        assert (await r.list_journal(3, 5))[0].text == "hello"
    run(go())


def test_milestone_countdown_math():
    from cogs.couple.couple_cog import _days_until
    today = date(2026, 10, 1)
    assert _days_until(datetime(2025, 10, 1), True, today)[0] == 0
    assert _days_until(datetime(2025, 10, 2), True, today)[0] == 1
    assert _days_until(datetime(2025, 9, 30), True, today) == (364, date(2027, 9, 30))
    assert _days_until(datetime(2026, 9, 1), False, today)[0] == -30
    assert _days_until(datetime(2024, 2, 29), True, today)[1] == date(2027, 3, 1)  # leap-day safe


def test_gif_list_survives_long_urls(tmp_path, monkeypatch):
    """Regression: 20 long URLs overflowed the 4096-char embed limit and /gif list errored."""
    async def go():
        await fresh_db(tmp_path, monkeypatch)
        from discord.ext import commands
        import discord
        from database.connection import get_session
        from models.models import GIF
        from cogs.owner.owner_cog import OwnerCog
        async with get_session() as s:
            for i in range(60):
                s.add(GIF(category="hug", url=f"https://media.tenor.com/{'x' * 480}/{i}.gif"))
        cog = OwnerCog(commands.Bot(command_prefix="!", intents=discord.Intents.none()))
        sent = {}

        class Resp:
            def is_done(self): return False
            async def send_message(self, content=None, **kw): sent.update(content=content, **kw)

        inter = SimpleNamespace(response=Resp())
        await cog.gif_list.callback(cog, inter, "hug")
        embed = sent["embed"]
        assert len(embed.description) <= 4096 and "60" in embed.title and "more" in embed.description
        await cog.gif_list.callback(cog, inter, "nothing-here")
        assert "No gifs" in sent["content"]
    run(go())
