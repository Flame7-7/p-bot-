"""/intimate and /intimate_female: routing, gating, and keeping adult actions out of public lists."""
import asyncio
import re
from types import SimpleNamespace

import discord
from discord.ext import commands

from cogs.roleplay.roleplay_cog import RoleplayCog
from services.action_registry import ADULT_CATEGORIES, get_all_actions
from tests.fakes import FakeInteraction, FakeUser
import database.connection as dbc


def run(coro):
    return asyncio.run(coro)


def names(category):
    return sorted(a.name for a in get_all_actions().values() if a.category == category)


def member(uid, name):
    return SimpleNamespace(id=uid, display_name=name, name=name, mention=f"<@{uid}>", bot=False,
                           display_avatar=SimpleNamespace(url="http://x/a.png"))


async def make_cog(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "a.db"))
    from utils.config import get_config
    get_config.cache_clear()
    dbc._engine = None
    await dbc.init_db()
    return RoleplayCog(commands.Bot(command_prefix="!", intents=discord.Intents.none()))


def interaction(channel_nsfw=None):
    """channel_nsfw None -> a DM (no guild); True/False -> a server channel."""
    inter = FakeInteraction(FakeUser(1, "Her"))
    if channel_nsfw is not None:
        inter.guild = object()
        inter.channel = type("Ch", (), {"is_nsfw": lambda self: channel_nsfw})()
    return inter


async def run_cmd(cmd, cog, inter, action, target):
    inter.user = member(1, "Her")
    await cmd.callback(cog, inter, action, target)
    return inter


def test_female_actions_exist_and_are_scoped():
    fem = names("intimate_female")
    assert fem and all(re.fullmatch(r"fem_[a-z0-9_]+", n) for n in fem), "snake_case names, no spaces"
    assert not set(fem) & set(names("intimate"))


def test_intimate_female_runs_each_action_in_dm(tmp_path, monkeypatch):
    async def go():
        cog = await make_cog(tmp_path, monkeypatch)
        for i, action in enumerate(names("intimate_female")):
            inter = await run_cmd(RoleplayCog.intimate_female, cog, interaction(), action, member(2, "Him"))
            sent = inter.response.sent
            assert any("embed" in m for m in sent), (action, sent)
            assert not any("don't know" in (m.get("content") or "") for m in sent), action
    run(go())


def test_intimate_female_forces_female_pronouns(tmp_path, monkeypatch):
    async def go():
        cog = await make_cog(tmp_path, monkeypatch)
        seen = {}
        orig = cog.service.execute

        async def spy(**kw):
            seen.update(kw)
            return await orig(**kw)
        cog.service.execute = spy
        await run_cmd(RoleplayCog.intimate_female, cog, interaction(), names("intimate_female")[0], member(2, "Him"))
        assert seen["force_author_gender"] == "female"
        seen.clear()
        await run_cmd(RoleplayCog.intimate, cog, interaction(), names("intimate")[0], member(2, "Him"))
        assert seen["force_author_gender"] is None
    run(go())


def test_channel_gate_applies_to_both_adult_commands(tmp_path, monkeypatch):
    async def go():
        cog = await make_cog(tmp_path, monkeypatch)
        for cmd, cat in ((RoleplayCog.intimate_female, "intimate_female"), (RoleplayCog.intimate, "intimate")):
            action = names(cat)[0]
            blocked = await run_cmd(cmd, cog, interaction(channel_nsfw=False), action, member(2, "Him"))
            assert "age-restricted" in blocked.last_text and not any("embed" in m for m in blocked.response.sent)
            ok = await run_cmd(cmd, cog, interaction(channel_nsfw=True), action, member(2, "Him"))
            assert any("embed" in m for m in ok.response.sent)
    run(go())


def test_wrong_category_is_rejected_by_each_command(tmp_path, monkeypatch):
    async def go():
        cog = await make_cog(tmp_path, monkeypatch)
        plain = next(a.name for a in get_all_actions().values() if a.category not in ADULT_CATEGORIES)
        for cmd, action in (
            (RoleplayCog.intimate_female, names("intimate")[0]),      # other adult category
            (RoleplayCog.intimate, names("intimate_female")[0]),
            (RoleplayCog.intimate_female, plain),                     # ordinary action
            (RoleplayCog.intimate, "no-such-action"),
        ):
            inter = await run_cmd(cmd, cog, interaction(), action, member(2, "Him"))
            assert "don't know that action" in inter.last_text
        # and /roleplay refuses every adult action even in a DM
        for action in names("intimate") + names("intimate_female"):
            inter = await run_cmd(RoleplayCog.roleplay, cog, interaction(), action, member(2, "Him"))
            assert "don't know that action" in inter.last_text, action
    run(go())


def test_autocomplete_never_mixes_categories():
    from cogs.roleplay.roleplay_cog import _autocomplete_for
    async def go():
        public = {c.value for c in await _autocomplete_for(None)(None, "")}
        male = {c.value for c in await _autocomplete_for("intimate")(None, "")}
        fem = {c.value for c in await _autocomplete_for("intimate_female")(None, "")}
        assert public and not public & (male | fem)
        assert fem and fem <= set(names("intimate_female")) and not fem & male
        assert {c.value for c in await _autocomplete_for("intimate_female")(None, "fem_k")} <= fem
    run(go())


def test_adult_actions_hidden_from_help_and_legacy_shortcuts(tmp_path, monkeypatch):
    async def go():
        from main import COGS, RoleplayBot
        from cogs.help.help_cog import collect
        monkeypatch.setenv("LEGACY_ROLEPLAY_COMMANDS", "true")
        monkeypatch.setenv("DB_PATH", str(tmp_path / "h.db"))
        from utils.config import get_config
        get_config.cache_clear()
        await dbc.init_db()
        bot = RoleplayBot()
        async with bot:
            for c in COGS:
                await bot.load_extension(c)
            top = {c.name for c in bot.tree.get_commands()}
            adult = {a.name for a in get_all_actions().values() if a.category in ADULT_CATEGORIES}
            assert not adult & top, "no ungated shortcut commands for adult actions"
            cats = collect(bot, guild=None, perms=discord.Permissions.none(), nsfw_ok=True, is_owner=True)
            notes = " ".join(n for c in cats.values() for n in c.notes)
            assert not any(n in notes for n in adult), "adult actions are not listed in /help"
            usages = [e.usage for c in cats.values() for e in c.entries]
            assert any(u.startswith("/intimate_female") for u in usages)
    run(go())
