import asyncio

import pytest

from services.dm_games import session as session_mod
from services.dm_games.board import (
    Connect4, Hangman, HigherLower, MemoryGame, NumberGuess, RockPaperScissors, TicTacToe, ttt_result,
)
from services.dm_games.quiz import (
    Compatibility, DailyQuestion, EmojiGuess, GuessFavourite, KnowGame, MostLikely, PickOne, ThisOrThat, Trivia,
    TruthOrDare, WordScramble, WouldYouRather, fuzzy_match,
)
from services.dm_games.registry import GAMES
from services.dm_games.session import GameManager
from tests.fakes import FakeInteraction, FakeUser, click, find, submit


class NullRepo:
    def __init__(self):
        self.records = []

    async def record_game(self, a, b, game, **kw):
        self.records.append((game, kw))


class MemMessages:
    """In-memory stand-in for GameMessageRepository."""

    def __init__(self):
        self.rows = {}

    async def upsert(self, user_id, channel_id, message_id, game_key):
        self.rows[user_id] = (channel_id, message_id, game_key)

    async def delete_for(self, user_ids):
        for u in user_ids:
            self.rows.pop(u, None)

    async def pop_all(self):
        from types import SimpleNamespace
        rows = [SimpleNamespace(user_id=u, channel_id=c, message_id=m, game_key=g) for u, (c, m, g) in self.rows.items()]
        self.rows.clear()
        return rows


def run(coro):
    return asyncio.run(coro)


async def begin(cls, **opts):
    me, her = FakeUser(1, "Him"), FakeUser(2, "Her")
    mgr = GameManager(None)
    mgr.repo = NullRepo()
    mgr.messages_repo = MemMessages()
    inter = FakeInteraction(me)
    session = await mgr.start(inter, her, cls, **opts)
    assert session is not None, inter.last_text
    return mgr, session, me, her


# ── engines ─────────────────────────────────────────────────────────────────

def test_ttt_result_detects_wins_and_draws():
    assert ttt_result(["❌"] * 3 + [None] * 6) == "❌"
    assert ttt_result([None, "⭕", None, None, "⭕", None, None, "⭕", None]) == "⭕"
    assert ttt_result(["❌", "⭕", "❌", "❌", "⭕", "⭕", "⭕", "❌", "❌"]) == "draw"
    assert ttt_result([None] * 9) is None


def test_fuzzy_match():
    assert fuzzy_match("Pizza", "pizza!") and fuzzy_match("blue", "dark blue") and not fuzzy_match("red", "green")


def test_connect4_layout_fits_discord_rows():
    async def go():
        _, s, me, _ = await begin(Connect4)
        rows = {}
        for item in s.views[me.id].children:
            rows[item.row] = rows.get(item.row, 0) + 1
        assert max(rows.values()) <= 5
    run(go())


def test_connect4_vertical_win():
    async def go():
        mgr, s, me, her = await begin(Connect4)
        for _ in range(3):
            await click(s, me, "1")
            await click(s, her, "2")
        await click(s, me, "1")
        assert not s.active and "wins" in s.ended_reason and mgr.get(1) is None
        assert mgr.repo.records[0][0] == "connect4" and mgr.repo.records[0][1]["winner"] == 1
    run(go())


# ── access control and turn order ───────────────────────────────────────────

def test_third_party_cannot_press_buttons():
    async def go():
        _, s, me, her = await begin(TicTacToe)
        stranger = FakeUser(99, "Stranger")
        view = s.views[me.id]
        inter = FakeInteraction(stranger, s.messages[me.id])
        assert await view.interaction_check(inter) is False
        assert "belongs to someone else" in inter.last_text
        assert all(c is None for c in s.board)
    run(go())


def test_partner_cannot_press_other_players_view():
    async def go():
        _, s, me, her = await begin(TicTacToe)
        view = s.views[me.id]  # her pressing HIS message's buttons
        inter = FakeInteraction(her, s.messages[me.id])
        assert await view.interaction_check(inter) is False
    run(go())


def test_turn_order_enforced():
    async def go():
        _, s, me, her = await begin(TicTacToe)
        # her view has all cells disabled on his turn, so call the handler directly like a stale click
        handler = s._play(0)
        inter = FakeInteraction(her, s.messages[her.id])
        await s.run(inter, lambda: handler(inter))
        assert s.board[0] is None and "Not your turn" in inter.last_text
        await click(s, me, "\u200b")
        assert s.board.count("❌") == 1 and s.turn == 2
    run(go())


def test_ttt_full_game_to_win_disables_buttons_and_records():
    async def go():
        mgr, s, me, her = await begin(TicTacToe)
        s._play  # sanity
        for uid, idx in [(1, 0), (2, 3), (1, 1), (2, 4), (1, 2)]:
            u = me if uid == 1 else her
            handler = s._play(idx)
            inter = FakeInteraction(u, s.messages[uid])
            await s.run(inter, lambda h=handler, i=inter: h(i))
        assert not s.active
        for uid in (1, 2):
            assert all(c.disabled for c in s.messages[uid].view.children)
        assert mgr.repo.records == [("tictactoe", {"winner": 1, "draw": False, "points": 0})]
        late = FakeInteraction(me, s.messages[1])
        await s.run(late, lambda: s._play(5)(late))
        assert "already ended" in late.last_text
    run(go())


# ── sessions: one per user, quit, expiry ────────────────────────────────────

def test_one_active_game_per_user_and_quit():
    async def go():
        mgr, s, me, her = await begin(TicTacToe)
        again = FakeInteraction(me)
        assert await mgr.start(again, her, Connect4) is None
        assert "already in a game" in again.last_text
        await mgr.quit(2)
        assert mgr.get(1) is None and mgr.get(2) is None and not s.active
        assert all(c.disabled for c in s.messages[1].view.children)
        assert await mgr.start(FakeInteraction(me), her, Connect4) is not None
    run(go())


def test_idle_sessions_expire_and_lock_buttons():
    async def go():
        mgr, s, me, her = await begin(Hangman)
        s.last_activity -= 10_000
        # run one sweep iteration without the sleep
        now = session_mod.time.monotonic()
        for sess in mgr.sessions():
            if now - sess.last_activity > session_mod.get_config().game_idle_timeout:
                await sess.shutdown("⏰ This game timed out from inactivity.")
        assert not s.active and mgr.sessions() == set()
        assert all(c.disabled for c in s.messages[1].view.children)
        assert "timed out" in s.messages[1].embed.description
    run(go())


def test_dm_closed_aborts_cleanly():
    async def go():
        me, her = FakeUser(1, "Him"), FakeUser(2, "Her")
        async def refuse(**kw):
            return None
        her.send = refuse
        mgr = GameManager(None)
        mgr.messages_repo = MemMessages()
        inter = FakeInteraction(me)
        assert await mgr.start(inter, her, TicTacToe) is None
        assert mgr.sessions() == set() and "DM" in inter.last_text
    run(go())


def test_concurrent_clicks_do_not_corrupt_state():
    async def go():
        _, s, me, her = await begin(RockPaperScissors)
        view = s.views[me.id]
        rock, paper = find(view, "Rock"), find(view, "Paper")
        her_scissors = find(s.views[her.id], "Scissors")
        inters = [FakeInteraction(me, s.messages[1]), FakeInteraction(me, s.messages[1]), FakeInteraction(her, s.messages[2])]
        # stale double-click from the same player plus the partner's pick, all at once
        await asyncio.gather(rock.callback(inters[0]), paper.callback(inters[1]), her_scissors.callback(inters[2]))
        assert s.score == {1: 1, 2: 0}  # rock beat scissors; his second pick was rejected
        assert "already chose" in inters[1].last_text
    run(go())


# ── individual game flows ───────────────────────────────────────────────────

def test_rps_match_to_two():
    async def go():
        mgr, s, me, her = await begin(RockPaperScissors)
        for _ in range(2):
            await click(s, me, "Rock")
            await click(s, her, "Scissors")
        assert not s.active and mgr.repo.records[0][1]["winner"] == 1
    run(go())


def test_hangman_flow_and_secret_stays_hidden():
    async def go():
        _, s, me, her = await begin(Hangman)
        inter = await click(s, me, "Choose the word")
        assert inter.response.modal is not None
        await submit(inter.response.modal, me, "love", s)
        assert s.word == "LOVE"
        assert "LOVE" not in s.messages[2].embed.description.replace("\\_", "")
        for ch in "LOVE":
            menu = next(
                c for c in s.views[2].children
                if (getattr(c, "placeholder", "") or "").startswith("Letters") and any(o.value == ch for o in c.options)
            )
            menu._values = [ch]
            await menu.callback(FakeInteraction(her, s.messages[2]))
        assert not s.active and "solved" in s.ended_reason
    run(go())


def test_hangman_rejects_bad_word():
    async def go():
        _, s, me, _ = await begin(Hangman)
        inter = await click(s, me, "Choose the word")
        sub = await submit(inter.response.modal, me, "a1", s)
        assert s.word is None and "3–20 letters" in sub.last_text
    run(go())


def test_number_guess_wrong_turn_and_win():
    async def go():
        mgr, s, me, her = await begin(NumberGuess)
        s.secret = 42
        inter = await click(s, me, "Guess")
        await submit(inter.response.modal, me, "50", s)
        assert s.turn == 2 and "lower" in s.history[0]
        inter = await click(s, her, "Guess")
        await submit(inter.response.modal, her, "42", s)
        assert not s.active and mgr.repo.records[0][1]["winner"] == 2
    run(go())


def test_memory_pair_scoring():
    async def go():
        _, s, me, her = await begin(MemoryGame)
        s.FLIP_BACK_DELAY = 0
        s.cards = ["a", "a", "b", "b"] + ["c", "c", "d", "d", "e", "e", "f", "f", "g", "g", "h", "h"]
        for idx in (0, 1):
            inter = FakeInteraction(me, s.messages[1])
            await s.run(inter, lambda i=inter, n=idx: s._flip(n)(i))
        assert s.score[1] == 1 and s.turn == 1
        for idx in (2, 4):
            inter = FakeInteraction(me, s.messages[1])
            await s.run(inter, lambda i=inter, n=idx: s._flip(n)(i))
        assert s.turn == 2 and s.flipped == []
    run(go())


def test_higher_lower_streak_and_end():
    async def go():
        mgr, s, me, her = await begin(HigherLower)
        s.card = (7, "♠️")
        s._draw = staticmethod(lambda: (10, "♥️"))
        await click(s, me, "Higher")
        assert s.streak == 1 and s.turn == 2
        s._draw = staticmethod(lambda: (2, "♥️"))
        await click(s, her, "Higher")
        assert not s.active and mgr.repo.records[0][1]["points"] == 1
    run(go())


@pytest.mark.parametrize("cls", [WouldYouRather, ThisOrThat, Compatibility, MostLikely, Trivia])
def test_choice_games_play_through(cls):
    async def go():
        mgr, s, me, her = await begin(cls)
        total = len(s.rounds)
        for _ in range(total):
            await click(s, me, "A" if cls is not MostLikely else "Him")
            # nothing leaks before both answer
            assert not s.revealed
            await click(s, her, "B" if cls is not MostLikely else "Her")
            assert s.revealed
            await click(s, me, "Finish" if s.index == total - 1 else "Next")
        assert not s.active
        assert mgr.repo.records and mgr.repo.records[0][0] == cls.stats_game
    run(go())


def test_choice_game_cannot_answer_twice():
    async def go():
        _, s, me, her = await begin(WouldYouRather)
        await click(s, me, "A")
        with pytest.raises(LookupError):  # all of his buttons are disabled after answering
            await click(s, me, "B")
    run(go())


def test_know_me_two_phase():
    async def go():
        mgr, s, me, her = await begin(KnowGame)
        for _ in range(len(s.rounds)):
            await click(s, me, "A)")
            await click(s, her, "A)")
            assert s.phase == "guess"
            await click(s, me, "A)")
            await click(s, her, "A)")
            assert s.phase == "reveal"
            await click(s, me, "Finish" if s.index == len(s.rounds) - 1 else "Next")
        assert not s.active and mgr.repo.records[0][1]["draw"] is True
    run(go())


def test_guess_favourite_uses_text_and_fuzzy_scoring():
    async def go():
        _, s, me, her = await begin(GuessFavourite)
        for user, text in ((me, "Pizza"), (her, "Blue")):
            inter = await click(s, user, "Answer")
            await submit(inter.response.modal, user, text, s)
        for user, text in ((me, "blue"), (her, "pizza!")):
            inter = await click(s, user, "Answer")
            await submit(inter.response.modal, user, text, s)
        assert s.phase == "reveal" and s.score == {1: 1, 2: 1}
    run(go())


@pytest.mark.parametrize("cls", [EmojiGuess, WordScramble])
def test_guess_rounds(cls):
    async def go():
        mgr, s, me, her = await begin(cls)
        for i in range(len(s.puzzles)):
            answer = s.puzzles[i][1][0]
            inter = await click(s, me, "Guess")
            await submit(inter.response.modal, me, answer.lower(), s)
            assert s.round_over and s.score[1] == i + 1
            await click(s, her, "Finish" if i == len(s.puzzles) - 1 else "Next")
        assert not s.active and mgr.repo.records[0][1]["winner"] == 1
    run(go())


def test_truth_or_dare_turns():
    async def go():
        _, s, me, her = await begin(TruthOrDare)
        await click(s, me, "Truth")
        assert s.prompt and s.kind == "truth"
        first = s.prompt
        await click(s, me, "Another")
        assert s.prompt != first or len(s._seen) >= 1
        await click(s, me, "Done")
        assert s.turn == 2 and s.done["truth"] == 1
        await click(s, her, "Dare")
        assert s.kind == "dare"
    run(go())


def test_pick_one_and_daily_question():
    async def go():
        _, s, me, her = await begin(PickOne)
        await click(s, me, "A)")
        await click(s, her, "B)")
        assert "dice say" in s.messages[1].embed.description
    run(go())

    async def daily():
        mgr, s, me, her = await begin(DailyQuestion, question="Best day?")
        for user, text in ((me, "today"), (her, "yesterday")):
            inter = await click(s, user, "Answer")
            await submit(inter.response.modal, user, text, s)
        assert not s.active
        desc = s.messages[1].embed.description
        assert "today" in desc and "yesterday" in desc
    run(daily())


def test_every_registered_game_starts_and_renders_for_both_players():
    async def go():
        for info in GAMES:
            mgr, s, me, her = await begin(info.cls)
            for u in (me, her):
                assert s.messages[u.id].embed.description, info.key
                assert len(s.views[u.id].children) <= 25
                rows = {}
                for c in s.views[u.id].children:
                    rows[c.row] = rows.get(c.row, 0) + 1
                assert all(n <= 5 for n in rows.values()), (info.key, rows)
            await mgr.quit(1)
    run(go())
