import asyncio
import discord
from discord.ext import commands

from cogs.dmgames.play_cog import LauncherView, PlayCog
from services.dm_games import registry
from services.dm_games.registry import GAMES, categories_in_use, games_in
from services.dm_games.session import GameSession
from tests.fakes import FakeChannel, FakeInteraction, FakeUser
from tests.test_games import MemMessages, NullRepo


def run(coro):
    return asyncio.run(coro)


def fake_msg():
    return FakeChannel(7, None).post()


def make_cog(monkeypatch, partner):
    cog = PlayCog(commands.Bot(command_prefix="!", intents=discord.Intents.none()))
    cog.manager.repo, cog.manager.messages_repo = NullRepo(), MemMessages()

    async def fake_partner(bot, uid):
        return partner
    import cogs.dmgames.play_cog as pc
    monkeypatch.setattr(pc, "get_partner", fake_partner)
    return cog


def select_values(inter_user, view, values):
    """Drive a view's select the way Discord does: set interaction data, call the item callback."""
    inter = FakeInteraction(inter_user, fake_msg())
    inter.data = {"values": values}
    return inter


async def pump(view, item_index, values, user):
    inter = select_values(user, view, values)
    assert await view.interaction_check(inter)
    await view.children[item_index].callback(inter)
    return inter


def test_registry_is_discovered_and_complete():
    assert len(GAMES) == 18
    assert categories_in_use() == ["Brain", "Chance", "Relationship", "Funny", "Competitive"]
    assert sum(len(games_in(c)) for c in categories_in_use()) == 18
    for g in GAMES:
        assert g.blurb and g.duration and g.players and g.category, g.key
    assert len({g.key for g in GAMES}) == 18


def test_new_game_appears_without_touching_the_menu():
    class Dummy(GameSession):
        key, title, emoji = "dummy", "Dummy", "🧪"
        category, blurb, duration = "Chance", "A test game", "~1 min"

        def render(self, uid):
            return self.embed("x"), []
    try:
        found = registry.discover_games()
        assert any(g.key == "dummy" and g.category == "Chance" for g in found)
    finally:
        GameSession.__subclasses__()  # noqa
        # unregister by removing the class from the subclass graph
        del Dummy
        import gc
        gc.collect()


def test_launcher_flow_category_game_play(monkeypatch):
    async def go():
        me, her = FakeUser(1, "Him"), FakeUser(2, "Her")
        cog = make_cog(monkeypatch, her)
        view = LauncherView(cog, me.id)

        home = view.embed()
        assert home.title == "🎮 COUPLE GAMES" and "Choose a category" in home.description
        for cat in ("Brain", "Chance", "Relationship", "Funny", "Competitive"):
            assert cat in home.description
        assert len(view.children) == 1

        inter = await pump(view, 0, ["Competitive"], me)
        page = inter.response.done and view.embed()
        assert "Tic-Tac-Toe" in [f.name for f in page.fields][0] or any("Tic-Tac-Toe" in f.name for f in page.fields)
        field = next(f for f in page.fields if "Tic-Tac-Toe" in f.name)
        assert "⏱" in field.value and "👥 2 players" in field.value
        assert len(view.children) == 3, "category select + game select + Back"

        await pump(view, 1, ["ttt"], me)
        detail = view.embed()
        assert detail.title == "⭕ Tic-Tac-Toe" and "~3–5 min" in detail.description and "Easy" in detail.description
        play = next(c for c in view.children if getattr(c, "label", "") == "Play")

        inter = FakeInteraction(me, fake_msg())
        await play.callback(inter)
        session = cog.manager.get(1)
        assert session is not None and type(session).__name__ == "TicTacToe"
        assert len(me.dms) == 1 and len(her.dms) == 1, "game sent to both DMs"
        assert any("ready in your DMs" in (m.get("content") or "") for m in inter.response.sent)
        await cog.manager.stop()
    run(go())


def test_launcher_back_and_only_owner_can_use_it(monkeypatch):
    async def go():
        me, her = FakeUser(1, "Him"), FakeUser(2, "Her")
        cog = make_cog(monkeypatch, her)
        view = LauncherView(cog, me.id)
        stranger = FakeInteraction(FakeUser(99, "X"), fake_msg())
        assert await view.interaction_check(stranger) is False
        await pump(view, 0, ["Brain"], me)
        back = next(c for c in view.children if getattr(c, "label", "") == "Back")
        inter = FakeInteraction(me, fake_msg())
        await back.callback(inter)
        assert view.category is None and view.embed().title == "🎮 COUPLE GAMES"
    run(go())


def test_play_command_variants(monkeypatch):
    async def go():
        me, her = FakeUser(1, "Him"), FakeUser(2, "Her")
        cog = make_cog(monkeypatch, her)

        inter = FakeInteraction(me)
        inter.guild = None
        await PlayCog.play.callback(cog, inter, None)
        assert inter.response.sent[-1]["view"] is not None and "GAMES" in inter.response.sent[-1]["embed"].title

        inter2 = FakeInteraction(me)
        await PlayCog.play.callback(cog, inter2, "connect4")      # direct start
        assert type(cog.manager.get(1)).__name__ == "Connect4"
        inter3 = FakeInteraction(me)
        await PlayCog.gamequit.callback(cog, inter3)
        assert cog.manager.get(1) is None and "Ended" in inter3.last_text

        lonely = make_cog(monkeypatch, None)
        inter4 = FakeInteraction(me)
        await PlayCog.play.callback(lonely, inter4, None)
        assert "partner" in inter4.last_text
        await cog.manager.stop()
    run(go())


def test_every_existing_alias_command_still_starts_its_game(monkeypatch):
    async def go():
        me, her = FakeUser(1, "Him"), FakeUser(2, "Her")
        cog = make_cog(monkeypatch, her)
        for cmd, cls in (("ttt", "TicTacToe"), ("connect4", "Connect4"), ("wyr", "WouldYouRather"), ("truthordare", "TruthOrDare")):
            inter = FakeInteraction(me)
            await getattr(PlayCog, cmd).callback(cog, inter)
            assert type(cog.manager.get(1)).__name__ == cls, cmd
            await cog.manager.quit(1)
        await cog.manager.stop()
    run(go())


def test_autocomplete_lists_games(monkeypatch):
    async def go():
        cog = make_cog(monkeypatch, None)
        out = await cog._game_autocomplete(None, "tic")
        assert [c.value for c in out] == ["ttt"]
        assert len(await cog._game_autocomplete(None, "")) == 18
        assert {c.value for c in await cog._game_autocomplete(None, "brain")} >= {"trivia", "hangman"}
    run(go())
