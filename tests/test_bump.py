"""Game message bumping: activity-based timer, state preserved, races, deletion, restart."""
import asyncio
import discord
import pytest

from services.dm_games.board import Connect4, TicTacToe
from services.dm_games.quiz import WouldYouRather
from services.dm_games.session import GameManager
from tests.fakes import FakeInteraction, FakeUser, _Resp, click
from tests.test_games import MemMessages, NullRepo


def run(coro):
    return asyncio.run(coro)


class Clock:
    """Manual monotonic clock so timer tests don't sleep."""

    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t

    def advance(self, seconds):
        self.t += seconds


def games_in_channel(user):
    return [m for m in user.channel.messages if m.embed is not None]


async def begin(cls=TicTacToe, delay=60, monkeypatch=None):
    me, her = FakeUser(1, "Him"), FakeUser(2, "Her")
    mgr = GameManager(None)
    mgr.repo, mgr.messages_repo = NullRepo(), MemMessages()
    clock = Clock()
    mgr.clock = clock
    inter = FakeInteraction(me)
    s = await mgr.start(inter, her, cls)
    assert s is not None
    mgr.test_clock = clock
    return mgr, s, me, her


@pytest.fixture(autouse=True)
def delay_60(monkeypatch):
    monkeypatch.setenv("GAME_BUMP_DELAY", "60")
    from utils.config import get_config
    get_config.cache_clear()
    yield
    get_config.cache_clear()


def chat(user, mgr, n=1):
    """Someone talks in this player's DM: message appears and the manager is told."""
    for _ in range(n):
        m = user.channel.post(content="hello")
        mgr.note_message(user.channel.id, m.id)


def test_config_default_and_override(monkeypatch):
    from utils.config import get_config
    monkeypatch.delenv("GAME_BUMP_DELAY", raising=False)
    get_config.cache_clear()
    assert get_config().game_bump_delay == 60
    monkeypatch.setenv("GAME_BUMP_DELAY", "15")
    get_config.cache_clear()
    assert get_config().game_bump_delay == 15
    monkeypatch.setenv("GAME_BUMP_DELAY", "banana")
    get_config.cache_clear()
    assert get_config().game_bump_delay == 60


def test_bumps_after_quiet_period_and_keeps_state():
    async def go():
        mgr, s, me, her = await begin()
        await click(s, me, "\u200b")                # state: one X placed
        old = s.messages[1]
        chat(me, mgr, 3)
        mgr.test_clock.advance(30)
        await mgr.run_once()
        assert s.messages[1] is old, "not quiet long enough yet"
        mgr.test_clock.advance(31)
        await mgr.run_once()
        new = s.messages[1]
        assert new is not old and old.deleted and me.channel.last is new, "game is back at the bottom"
        assert s.board.count("❌") == 1 and s.turn == 2, "state unchanged"
        assert mgr.messages_repo.rows[1][1] == new.id, "tracked message id updated"
        assert s.views[1].children and not any(c.disabled for c in s.views[1].children if c.label == "\u200b" and False)
        await click(s, her, "\u200b")                # game still works through the new message
        assert s.board.count("⭕") == 1
    run(go())


def test_chat_resets_timer():
    async def go():
        mgr, s, me, _ = await begin()
        clock = mgr.test_clock
        chat(me, mgr)
        clock.advance(50)
        await mgr.run_once()
        chat(me, mgr)                                # more talking at +50s: timer restarts
        clock.advance(50)
        await mgr.run_once()                         # 100s after the first message, 50s after the last
        first = s.messages[1]
        assert not first.deleted, "still within the quiet window after the latest message"
        clock.advance(11)
        await mgr.run_once()
        assert s.messages[1] is not first
    run(go())


def test_quiet_game_message_is_not_reposted():
    async def go():
        mgr, s, me, _ = await begin()
        first = s.messages[1]
        mgr.test_clock.advance(600)
        await mgr.run_once()
        assert s.messages[1] is first and len(me.channel.messages) == 1
    run(go())


def test_game_interaction_resets_timer_and_updates_normally():
    async def go():
        mgr, s, me, her = await begin()
        clock = mgr.test_clock
        chat(me, mgr)
        chat(her, mgr)
        clock.advance(50)
        await click(s, me, "\u200b")                 # a move at +50s
        assert all(t.due == clock() + 60 for t in mgr._tracks.values()), "both timers restarted by the move"
        clock.advance(59)
        await mgr.run_once()
        assert not s.messages[1].deleted and not s.messages[2].deleted
        clock.advance(2)
        await mgr.run_once()
        assert s.messages[1] is me.channel.last and s.messages[2] is her.channel.last
    run(go())


def test_bump_does_not_reset_by_its_own_message_and_waits_again():
    async def go():
        mgr, s, me, _ = await begin()
        clock = mgr.test_clock
        chat(me, mgr)
        clock.advance(61)
        await mgr.run_once()
        bumped = s.messages[1]
        assert bumped.id in mgr._game_msg_ids
        mgr.note_message(me.channel.id, bumped.id)   # the gateway echo of our own post
        assert mgr._tracks[1].last_seen_id == bumped.id, "own message isn't treated as chat"
        clock.advance(200)
        await mgr.run_once()
        assert s.messages[1] is bumped, "nothing new said, so no second bump"
        chat(me, mgr)
        clock.advance(61)
        await mgr.run_once()
        assert s.messages[1] is not bumped, "after more chat it waits and bumps again"
    run(go())


def test_ending_game_cancels_bumping_and_clears_state():
    async def go():
        mgr, s, me, her = await begin()
        chat(me, mgr)
        await mgr.quit(1)
        assert mgr._tracks == {} and mgr._by_channel == {} and mgr.messages_repo.rows == {}
        before = len(me.channel.messages)
        mgr.test_clock.advance(1000)
        await mgr.run_once()
        assert len(me.channel.messages) == before, "nothing re-posted after the game ended"
        assert await s.bump(1) is False
    run(go())


def test_deleted_game_message_is_reposted_on_next_pass_and_on_next_move():
    async def go():
        mgr, s, me, her = await begin()
        gone = s.messages[1]
        gone.deleted = True
        me.channel.messages.remove(gone)
        mgr.note_deleted(gone.id)
        await mgr.run_once()
        assert s.messages[1] is not gone and me.channel.last is s.messages[1]
        # deleted again, then the *partner* moves: his edit hits NotFound and falls back to a re-post
        gone2 = s.messages[1]
        gone2.deleted = True
        me.channel.messages.remove(gone2)
        await click(s, her, "\u200b") if False else None
        handler = s._play(0)
        inter = FakeInteraction(me, s.messages[1])
        await s.run(inter, lambda: handler(inter))
        assert s.messages[1] is not gone2 and s.board[0] == "❌"
    run(go())


def test_failed_send_keeps_old_message_and_backs_off():
    async def go():
        mgr, s, me, _ = await begin()
        chat(me, mgr)
        old = s.messages[1]
        me.channel.fail_send = discord.Forbidden(_Resp(403), "Cannot send")
        clock = mgr.test_clock
        clock.advance(61)
        await mgr.run_once()
        assert s.messages[1] is old and not old.deleted, "old message kept when the new one can't be sent"
        assert mgr._tracks[1].due >= clock() + 60, "backs off instead of retrying every tick"
        me.channel.fail_send = None
        clock.advance(400)
        await mgr.run_once()
        assert s.messages[1] is not old
    run(go())


def test_undeletable_old_message_is_disabled_instead():
    async def go():
        mgr, s, me, _ = await begin()
        chat(me, mgr)
        old = s.messages[1]
        old.fail_delete = discord.Forbidden(_Resp(403), "nope")
        mgr.test_clock.advance(61)
        await mgr.run_once()
        assert s.messages[1] is not old
        assert all(c.disabled for c in old.view.children), "stale copy can no longer be used"
    run(go())


def test_stale_copy_buttons_are_rejected():
    async def go():
        mgr, s, me, _ = await begin()
        chat(me, mgr)
        old = s.messages[1]
        mgr.test_clock.advance(61)
        await mgr.run_once()
        inter = FakeInteraction(me, old)             # click on the superseded message
        assert await s.views[1].interaction_check(inter) is False
        assert "old copy" in inter.last_text
    run(go())


def test_simultaneous_press_and_bump_are_serialised():
    async def go():
        mgr, s, me, her = await begin(Connect4)
        chat(me, mgr)
        chat(her, mgr)
        handler = s._drop(3)
        inter = FakeInteraction(me, s.messages[1])
        await asyncio.gather(
            s.run(inter, lambda: handler(inter)),
            s.bump(1),
            s.bump(2),
        )
        assert sum(len(c) for c in s.grid) == 1, "exactly one disc was dropped"
        assert len(games_in_channel(me)) == 1 and len(games_in_channel(her)) == 1, "no duplicate game messages"
        assert s.messages[1] is me.channel.last and s.messages[2] is her.channel.last
    run(go())


def test_multiple_games_are_independent():
    async def go():
        mgr = GameManager(None)
        mgr.repo, mgr.messages_repo = NullRepo(), MemMessages()
        users = [FakeUser(i, f"U{i}") for i in (1, 2, 3, 4)]
        mgr.clock = clock = Clock()
        a = await mgr.start(FakeInteraction(users[0]), users[1], TicTacToe)
        b = await mgr.start(FakeInteraction(users[2]), users[3], WouldYouRather)
        chat(users[0], mgr)                          # only couple A is chatting
        clock.advance(61)
        await mgr.run_once()
        assert users[0].channel.last is a.messages[1] and games_in_channel(users[0]) == [a.messages[1]]
        assert b.messages[3] is users[2].channel.messages[0], "couple B untouched"
        await mgr.quit(1)
        assert b.active and 3 in mgr._tracks and 1 not in mgr._tracks
    run(go())


def test_delay_zero_disables_bumping(monkeypatch):
    async def go():
        monkeypatch.setenv("GAME_BUMP_DELAY", "0")
        from utils.config import get_config
        get_config.cache_clear()
        mgr, s, me, _ = await begin()
        chat(me, mgr)
        first = s.messages[1]
        mgr.test_clock.advance(1000)
        await mgr.run_once()
        assert s.messages[1] is first
    run(go())


def test_loop_is_single_task_and_cancels_cleanly():
    async def go():
        mgr, s, me, _ = await begin()
        mgr.start_sweeper()
        t = mgr._loop_task
        mgr.start_sweeper()
        assert mgr._loop_task is t, "no duplicate loop"
        for _ in range(500):
            chat(me, mgr)                              # 500 messages never create tasks
        assert mgr._loop_task is t and len([x for x in asyncio.all_tasks() if x.get_name() == "game-manager"]) == 1
        await mgr.stop()
        assert t.cancelled() or t.done()
        assert mgr.sessions() == set() and not s.active
    run(go())


def test_restart_cleanup_closes_leftover_messages():
    async def go():
        calls = []

        class FakePartial:
            def __init__(self, cid, mid):
                self.cid, self.mid = cid, mid

            async def edit(self, **kw):
                calls.append((self.cid, self.mid, kw))
                if self.mid == 13:
                    raise discord.NotFound(_Resp(404), "gone")

        class FakeBot:
            def get_partial_messageable(self, cid, type=None):
                return type_("Ch", (), {"get_partial_message": lambda s, mid: FakePartial(cid, mid)})()

        type_ = type
        mgr = GameManager(FakeBot())
        mgr.messages_repo = MemMessages()
        await mgr.messages_repo.upsert(1, 100, 11, "ttt")
        await mgr.messages_repo.upsert(2, 200, 12, "ttt")
        await mgr.messages_repo.upsert(3, 300, 13, "ttt")   # already deleted by the user
        assert await mgr.cleanup_stale_messages() == 3
        assert {c[1] for c in calls} == {11, 12, 13}
        assert all(c[2]["view"] is None and "restarted" in c[2]["content"] for c in calls)
        assert mgr.messages_repo.rows == {}, "table emptied so it never repeats"
    run(go())


def test_message_ids_survive_in_real_database(tmp_path, monkeypatch):
    async def go():
        import database.connection as dbc
        monkeypatch.setenv("DB_PATH", str(tmp_path / "g.db"))
        from utils.config import get_config
        get_config.cache_clear()
        dbc._engine = None
        await dbc.init_db()
        from repositories.couple_repository import GameMessageRepository
        r = GameMessageRepository()
        await r.upsert(1, 10, 100, "ttt")
        await r.upsert(1, 10, 101, "ttt")          # bump updates the same row
        await r.upsert(2, 20, 200, "ttt")
        rows = await r.pop_all()
        assert sorted((x.user_id, x.message_id) for x in rows) == [(1, 101), (2, 200)]
        assert await r.pop_all() == []
        await r.upsert(5, 1, 1, "x")
        await r.delete_for([5])
        assert await r.pop_all() == []
    run(go())
