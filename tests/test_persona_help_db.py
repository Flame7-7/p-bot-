import asyncio
from types import SimpleNamespace

import discord
from discord.ext import commands

import database.connection as dbc


def run(coro):
    return asyncio.run(coro)


class Perms(SimpleNamespace):
    view_channel = send_messages = embed_links = read_message_history = True


def make_message(*, guild_id=10, channel_id=20, author_id=1, mentions=(), content="hi", dm=False):
    sent = []

    async def reply(**kw):
        sent.append(kw)

    channel = SimpleNamespace(id=channel_id, permissions_for=lambda me: Perms(), typing=lambda: _Typing())
    guild = None if dm else SimpleNamespace(id=guild_id, me=object())
    author = SimpleNamespace(id=author_id, bot=False, display_name="Her")
    members = []
    for uid in mentions:
        m = SimpleNamespace(id=uid, bot=False, display_name=f"user{uid}",
                            display_avatar=SimpleNamespace(url="http://x/a.png"))
        members.append(m)
    msg = SimpleNamespace(author=author, guild=guild, channel=channel, mentions=members, content=content,
                          clean_content=content, reference=None, reply=reply)
    return msg, sent


class _Typing:
    async def __aenter__(self): return self
    async def __aexit__(self, *a): return False


async def setup_cog(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "t.db"))
    from utils.config import get_config
    get_config.cache_clear()
    dbc._engine = None  # force a fresh engine bound to the temp DB
    await dbc.init_db()
    from cogs.persona.persona_cog import PersonaCog
    cog = PersonaCog(commands.Bot(command_prefix="!", intents=discord.Intents.none()))
    await cog.persona_repo.set_persona_text(2, "lowercase, casual")
    await cog.persona_repo.set_afk(2, True)
    await cog.channel_repo.set(10, 20, 99)
    cog._channels = await cog.channel_repo.all_enabled()
    return cog


def patch_member(monkeypatch):
    # isinstance(m, discord.Member) in the cog: make our namespaces count as members
    import cogs.persona.persona_cog as pc
    monkeypatch.setattr(pc.discord, "Member", SimpleNamespace, raising=False)
    monkeypatch.setattr(pc, "_missing_perms", lambda ch, me: [])
    calls = []

    async def fake_generate(*a, **kw):
        calls.append((a, kw))
        return "hey you"
    monkeypatch.setattr(pc, "generate_persona_reply", fake_generate)
    return calls


def test_persona_only_replies_in_configured_channel_never_in_dms(tmp_path, monkeypatch):
    async def go():
        cog = await setup_cog(tmp_path, monkeypatch)
        calls = patch_member(monkeypatch)

        msg, sent = make_message(mentions=[2])
        await cog.on_message(msg)
        assert len(sent) == 1 and calls, "should reply in the configured channel"

        cog._last_reply.clear()
        other, sent2 = make_message(channel_id=21, mentions=[2])
        await cog.on_message(other)
        assert not sent2, "other channels are ignored"

        cog._last_reply.clear()
        dm, sent3 = make_message(dm=True, mentions=[2])
        await cog.on_message(dm)
        assert not sent3, "DMs never trigger persona"

        cog._last_reply.clear()
        nobody, sent4 = make_message(mentions=[])
        await cog.on_message(nobody)
        assert not sent4, "no mention/reply -> no persona"

        cog._last_reply.clear()
        await cog.persona_repo.set_afk(2, False)
        msg5, sent5 = make_message(mentions=[2])
        await cog.on_message(msg5)
        assert not sent5, "owner not AFK -> silent"
    run(go())


def test_persona_disable_and_deleted_channel(tmp_path, monkeypatch):
    async def go():
        cog = await setup_cog(tmp_path, monkeypatch)
        patch_member(monkeypatch)
        assert await cog.channel_repo.disable(10) is True
        cog._channels.pop(10)
        msg, sent = make_message(mentions=[2])
        await cog.on_message(msg)
        assert not sent
        assert await cog.channel_repo.all_enabled() == {}
        await cog.channel_repo.set(10, 20)
        cog._channels = await cog.channel_repo.all_enabled()
        gone = SimpleNamespace(id=20, guild=SimpleNamespace(id=10))
        await cog.on_guild_channel_delete(gone)
        assert cog._channels == {} and await cog.channel_repo.all_enabled() == {}
    run(go())


def test_persona_has_no_dm_code_paths():
    """DM-facing modules must not import persona code at all."""
    import ast
    import pathlib
    root = pathlib.Path(__file__).resolve().parent.parent
    for rel in ("cogs/dmlink/dmlink_cog.py", "services/dm_mirror.py", "cogs/dmgames/play_cog.py"):
        tree = ast.parse((root / rel).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.ImportFrom):
                names = [node.module or ""] + [a.name for a in node.names]
            elif isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            assert not any("persona" in n for n in names), (rel, names)


def test_legacy_dm_persona_data_is_preserved(tmp_path, monkeypatch):
    async def go():
        cog = await setup_cog(tmp_path, monkeypatch)
        p = await cog.persona_repo.get(2)
        assert p.persona_text == "lowercase, casual" and p.afk_enabled and p.label_replies is not None
    run(go())


# ── help ────────────────────────────────────────────────────────────────────

def _bot():
    from main import COGS, RoleplayBot
    return RoleplayBot(), COGS


def test_help_matches_registered_commands_and_hides_privileged(tmp_path, monkeypatch):
    async def go():
        monkeypatch.setenv("DB_PATH", str(tmp_path / "h.db"))
        from utils.config import get_config
        get_config.cache_clear()
        dbc._engine = None
        await dbc.init_db()
        bot, cogs = _bot()
        async with bot:
            for c in cogs:
                await bot.load_extension(c)
            from cogs.help.help_cog import collect, ordered, build_pages
            plain = discord.Permissions.none()
            normal = collect(bot, guild=None, perms=plain, nsfw_ok=False, is_owner=False)
            def usages(cats):
                return [e.usage for cat in cats.values() for e in cat.entries]

            def has(cats, name):
                return any(u == name or u.startswith(name + " ") for u in usages(cats))

            assert has(normal, "/help") and has(normal, "/roleplay")
            assert has(normal, "/play start") and has(normal, "/couple compliment") and has(normal, "/persona set")
            in_guild = collect(bot, guild=discord.Object(id=5), perms=plain, nsfw_ok=False, is_owner=False)
            assert has(in_guild, "/persona setup") and not has(normal, "/persona setup"), "guild-only commands hidden in DMs"
            assert "/play" not in usages(normal), "groups expand to their subcommands"
            assert not has(normal, "/gif add") and not has(normal, "/resetuser"), "owner commands hidden"
            assert not has(normal, "/intimate"), "nsfw-only hidden outside nsfw channels/DMs"
            assert "Owner" not in normal and "Moderation" not in normal
            # roleplay shows one command plus the action list, not 60 commands
            assert len(normal["Roleplay"].entries) <= 6 and normal["Roleplay"].notes

            owner = collect(bot, guild=None, perms=plain, nsfw_ok=True, is_owner=True)
            assert has(owner, "/gif list") and has(owner, "/intimate") and "Owner" in owner

            admin = collect(bot, guild=None, perms=discord.Permissions(administrator=True), nsfw_ok=False, is_owner=False)
            assert "Owner" not in admin  # admin permission alone does not expose owner category

            # every registered leaf appears for the owner (nothing silently dropped)
            registered = {f"/{c.qualified_name}" for top in bot.tree.get_commands()
                          for c in ([top] if hasattr(top, "callback") else top.walk_commands())}
            missing = {r for r in registered if not has(owner, r)}
            assert not missing, missing

            for cat in ordered(normal):
                for page in build_pages(cat):
                    assert len(page.description) <= 4096
    run(go())
