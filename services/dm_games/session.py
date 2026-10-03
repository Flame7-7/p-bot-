"""Reusable infrastructure for two-player DM games.

A game is a ``GameSession`` subclass that implements ``render(uid)``. The
framework gives every game, for free:

* both players identified in every embed, one message per player in their DM;
* only the two players can press buttons (``SessionView.interaction_check``);
* one active session per user (``GameManager``), with ``/gamequit``;
* the game message follows the conversation: after ``GAME_BUMP_DELAY`` quiet seconds in a
  player's DM it is re-posted at the bottom (see ``GameManager`` / ``GameSession.bump``);
* one lock per session so simultaneous clicks cannot corrupt state;
* idle expiry with a background sweeper, buttons disabled when a game ends;
* shared score recording through ``CoupleRepository``.
"""
from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

import discord

from repositories.couple_repository import CoupleRepository, GameMessageRepository
from services.dm_games import texts
from utils.config import get_config
from utils.interactions import GENERIC_ERROR, disable_all, respond, resolve_user, safe_dm, safe_edit
from utils.logging import get_logger

logger = get_logger(__name__)

PINK = 0xFF6FA5
GOLD = 0xFFD166
Handler = Callable[[discord.Interaction], Awaitable["bool | None"]]
Items = list[discord.ui.Item]


class SessionView(discord.ui.View):
    """One player's controls. Rebuilt on every render; old ones are stopped."""

    def __init__(self, session: GameSession, uid: int, items: Items) -> None:
        super().__init__(timeout=None)  # expiry is owned by GameManager, not by discord.py
        self.session = session
        self.uid = uid
        for item in items:
            self.add_item(item)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.uid or interaction.user.id not in self.session.players:
            await respond(interaction, texts.NOT_YOUR_GAME, ephemeral=True)
            return False
        if not self.session.active:
            await respond(interaction, texts.GAME_OVER, ephemeral=True)
            return False
        current = self.session.messages.get(self.uid)
        if interaction.message is not None and current is not None and interaction.message.id != current.id:
            await respond(interaction, texts.OLD_COPY, ephemeral=True)
            return False
        return True

    async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item) -> None:
        logger.error("game view error in %s", self.session.key, exc_info=error)
        await respond(interaction, GENERIC_ERROR, ephemeral=True)


class TextPrompt(discord.ui.Modal):
    """A one-field modal whose submission is processed under the session lock."""

    def __init__(
        self,
        session: GameSession,
        title: str,
        label: str,
        handler: Callable[[discord.Interaction, str], Awaitable["bool | None"]],
        *,
        placeholder: str | None = None,
        max_length: int = 100,
        min_length: int = 1,
    ) -> None:
        super().__init__(title=title[:45])
        self.session = session
        self._handler = handler
        self.field: discord.ui.TextInput = discord.ui.TextInput(
            label=label[:45], placeholder=placeholder, max_length=max_length, min_length=min_length
        )
        self.add_item(self.field)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        value = str(self.field.value).strip()
        await self.session.run(interaction, lambda: self._handler(interaction, value))

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        logger.error("game modal error in %s", self.session.key, exc_info=error)
        await respond(interaction, GENERIC_ERROR, ephemeral=True)


class GameSession:
    """Base class for one running game between two partners."""

    key = "game"
    title = "Game"
    emoji = "🎮"
    stats_game: str | None = None  # key used in couple_game_stats; None = not scored

    # Launcher metadata (/play). A subclass that defines `category` in its own body is
    # listed automatically — see services/dm_games/registry.py.
    category: str | None = None
    blurb: str = ""
    duration: str = ""
    players_label: str = "2 players"
    difficulty: str | None = None

    def __init__(self, manager: GameManager, p1: discord.User, p2: discord.User) -> None:
        self.manager = manager
        self.players: tuple[int, int] = (p1.id, p2.id)
        self.users: dict[int, discord.User] = {p1.id: p1, p2.id: p2}
        self.messages: dict[int, discord.Message] = {}
        self.views: dict[int, SessionView] = {}
        self.active = True
        self.ended_reason: str | None = None
        self.last_activity = time.monotonic()
        self._lock = asyncio.Lock()

    # ── to be implemented by games ───────────────────────────────────────────

    def render(self, uid: int) -> tuple[discord.Embed, Items]:
        raise NotImplementedError

    async def setup(self) -> None:
        """Called once before the first render (load content, shuffle, ...)."""

    # ── helpers for games ────────────────────────────────────────────────────

    def other(self, uid: int) -> int:
        return self.players[1] if uid == self.players[0] else self.players[0]

    def name(self, uid: int) -> str:
        return self.users[uid].display_name

    def mention(self, uid: int) -> str:
        return f"<@{uid}>"

    def embed(self, description: str, *, title: str | None = None, color: int = PINK) -> discord.Embed:
        e = discord.Embed(title=title or f"{self.emoji} {self.title}", description=description, color=color)
        a, b = self.players
        e.set_footer(text=f"💕 {self.name(a)} & {self.name(b)}")
        return e

    def button(
        self,
        label: str | None,
        handler: Handler,
        *,
        style: discord.ButtonStyle = discord.ButtonStyle.secondary,
        row: int | None = None,
        disabled: bool = False,
        emoji: str | None = None,
    ) -> discord.ui.Button:
        btn: discord.ui.Button = discord.ui.Button(label=label, style=style, row=row, disabled=disabled, emoji=emoji)

        async def callback(interaction: discord.Interaction) -> None:
            await self.run(interaction, lambda: handler(interaction))

        btn.callback = callback  # type: ignore[method-assign]
        return btn

    def select(
        self,
        placeholder: str,
        options: list[discord.SelectOption],
        handler: Callable[[discord.Interaction, str], Awaitable["bool | None"]],
        *,
        row: int | None = None,
        disabled: bool = False,
    ) -> discord.ui.Select:
        sel: discord.ui.Select = discord.ui.Select(
            placeholder=placeholder, options=options, row=row, disabled=disabled, min_values=1, max_values=1
        )

        async def callback(interaction: discord.Interaction) -> None:
            value = sel.values[0]
            await self.run(interaction, lambda: handler(interaction, value))

        sel.callback = callback  # type: ignore[method-assign]
        return sel

    def quit_button(self, row: int | None = None) -> discord.ui.Button:
        async def handler(interaction: discord.Interaction) -> bool:
            await self.end(interaction=interaction, reason=f"🚪 {self.name(interaction.user.id)} left the game.", record=False)
            return False

        return self.button("Quit", handler, style=discord.ButtonStyle.danger, row=row, emoji="🚪")

    async def ask(
        self,
        interaction: discord.Interaction,
        title: str,
        label: str,
        handler: Callable[[discord.Interaction, str], Awaitable["bool | None"]],
        **kwargs,
    ) -> bool:
        """Open a text modal; returns False so the caller's wrapper doesn't also respond."""
        await interaction.response.send_modal(TextPrompt(self, title, label, handler, **kwargs))
        return False

    def touch(self) -> None:
        self.last_activity = time.monotonic()

    # ── running handlers safely ──────────────────────────────────────────────

    async def run(self, interaction: discord.Interaction, fn: Callable[[], Awaitable["bool | None"]]) -> None:
        """Run a handler under the lock, then re-render. Handlers return False
        when they already answered the interaction themselves."""
        async with self._lock:
            if not self.active:
                await respond(interaction, texts.GAME_OVER, ephemeral=True)
                return
            self.touch()
            try:
                result = await fn()
            except Exception:
                logger.exception("game %s handler failed", self.key)
                await respond(interaction, GENERIC_ERROR, ephemeral=True)
                return
            if result is not False and self.active:
                await self.push(interaction)
            if self.active:
                self.manager.note_game_activity(self)
        if not interaction.response.is_done():
            try:
                await interaction.response.defer()
            except discord.HTTPException:
                pass

    async def push(self, interaction: discord.Interaction | None = None, *, final: bool = False) -> None:
        """Re-render every player's message. The clicker goes first so the
        interaction is acknowledged inside Discord's 3-second window."""
        order = sorted(self.players, key=lambda u: not (interaction and interaction.user.id == u))
        for uid in order:
            embed, items = self.render(uid)
            view = SessionView(self, uid, items)
            if final:
                disable_all(view)
            old = self.views.pop(uid, None)
            if old:
                old.stop()
            if not final:
                self.views[uid] = view

            delivered = False
            if interaction and interaction.user.id == uid and not interaction.response.is_done():
                try:
                    await interaction.response.edit_message(embed=embed, view=view)
                    delivered = True
                except (discord.NotFound, discord.HTTPException):
                    delivered = False
            if not delivered:
                await self._edit_or_resend(uid, embed, view, final)
            if final:
                view.stop()

    async def _edit_or_resend(self, uid: int, embed: discord.Embed, view: SessionView, final: bool) -> None:
        """Edit the player's game message; if they deleted it, post a fresh copy instead of losing the game."""
        msg = self.messages.get(uid)
        if msg is None:
            return
        try:
            await msg.edit(embed=embed, view=view)
            return
        except discord.NotFound:
            if final:
                return
            logger.info("game message %s was deleted; re-posting", msg.id)
        except discord.Forbidden:
            return
        except discord.HTTPException:
            logger.warning("could not edit game message %s", msg.id, exc_info=True)
            return
        try:
            new = await msg.channel.send(embed=embed, view=view)
        except (discord.Forbidden, discord.NotFound, discord.HTTPException):
            logger.warning("could not re-post game message for %s", uid, exc_info=True)
            return
        self.messages[uid] = new
        await self.manager.track(self, uid, new)

    async def bump(self, uid: int) -> bool:
        """Move this player's game message to the bottom of the DM, keeping all state.

        The replacement is sent *before* the old message is removed, so a failed send
        never leaves the player without a game. Runs under the session lock, so it can't
        interleave with a button press.
        """
        async with self._lock:
            old = self.messages.get(uid)
            if not self.active or old is None:
                return False
            embed, items = self.render(uid)
            view = SessionView(self, uid, items)
            try:
                new = await old.channel.send(embed=embed, view=view)
            except (discord.Forbidden, discord.NotFound, discord.HTTPException):
                view.stop()
                logger.warning("could not bump %s game for %s", self.key, uid, exc_info=True)
                return False
            prev = self.views.get(uid)
            self.views[uid] = view
            self.messages[uid] = new
            await self.manager.track(self, uid, new)
            if prev:
                prev.stop()
            try:
                await old.delete()
            except discord.NotFound:
                pass
            except (discord.Forbidden, discord.HTTPException):
                if prev:  # can't delete it: at least make the stale copy inert
                    disable_all(prev)
                    await safe_edit(old, view=prev)
            return True

    # ── ending ───────────────────────────────────────────────────────────────

    async def end(
        self,
        *,
        interaction: discord.Interaction | None = None,
        reason: str | None = None,
        winner: int | None = None,
        draw: bool = False,
        points: int = 0,
        record: bool = True,
    ) -> None:
        """Finish the game: lock buttons, record the score, free both players."""
        if not self.active:
            return
        self.active = False
        self.ended_reason = reason
        self.manager.release(self)  # also cancels bumping for both players
        await self.manager.clear_messages(self)
        if record and self.stats_game:
            try:
                await self.manager.repo.record_game(
                    self.players[0], self.players[1], self.stats_game, winner=winner, draw=draw, points=points
                )
            except Exception:
                logger.exception("could not record %s result", self.stats_game)
        await self.push(interaction, final=True)

    async def shutdown(self, reason: str) -> None:
        """End from outside a handler (quit command, expiry) without racing one."""
        async with self._lock:
            await self.end(reason=reason, record=False)


@dataclass
class _Track:
    """Bump bookkeeping for one player's game message."""

    session: GameSession
    uid: int
    channel_id: int
    message_id: int
    last_seen_id: int          # newest message in that DM channel we know about
    due: float                 # monotonic time at which a bump becomes due
    deleted: bool = False      # the player deleted the game message


class GameManager:
    """Owns every live session: one per user, expiring when idle, bumped when buried.

    One background loop serves everything — idle expiry and message bumping — so there
    is no task per message or per game. Chat activity only updates a timestamp (O(1)).
    """

    def __init__(self, bot: discord.Client) -> None:
        self.bot = bot
        self.repo = CoupleRepository()
        self.messages_repo = GameMessageRepository()
        self._by_user: dict[int, GameSession] = {}
        self._tracks: dict[int, _Track] = {}      # uid -> bump state
        self._by_channel: dict[int, int] = {}     # DM channel id -> uid
        self._game_msg_ids: set[int] = set()      # ids of messages the bot posted for games
        self._loop_task: asyncio.Task | None = None
        self.clock: Callable[[], float] = time.monotonic  # replaceable in tests

    # ── configuration ────────────────────────────────────────────────────────

    @property
    def bump_delay(self) -> int:
        return get_config().game_bump_delay

    @property
    def tick(self) -> float:
        delay = self.bump_delay
        return 1.0 if 0 < delay <= 4 else 5.0

    # ── lifecycle ────────────────────────────────────────────────────────────

    def start_sweeper(self) -> None:
        """Start the single maintenance loop (idempotent)."""
        if self._loop_task is None or self._loop_task.done():
            self._loop_task = asyncio.create_task(self._loop(), name="game-manager")

    async def stop(self) -> None:
        task, self._loop_task = self._loop_task, None
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        for session in list(self.sessions()):
            await session.shutdown("🛠️ The bot is restarting — this game was closed.")

    async def _loop(self) -> None:
        while True:
            await asyncio.sleep(self.tick)
            try:
                await self.run_once()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("game manager tick failed")

    async def run_once(self, now: float | None = None) -> None:
        """One maintenance pass: expire idle games, then bump buried game messages."""
        now = self.clock() if now is None else now
        idle_limit = get_config().game_idle_timeout
        for session in self.sessions():
            if now - session.last_activity > idle_limit:
                try:
                    await session.shutdown("⏰ This game timed out from inactivity.")
                except Exception:
                    logger.exception("failed to expire session %s", session.key)

        delay = self.bump_delay
        if delay <= 0:
            return
        for track in list(self._tracks.values()):
            buried = track.deleted or track.last_seen_id != track.message_id
            if not buried or now < track.due or not track.session.active:
                continue
            ok = await track.session.bump(track.uid)
            if not ok:
                current = self._tracks.get(track.uid)
                if current is track:  # still ours: back off instead of retrying every tick
                    track.due = now + max(delay * 5, 30)

    # ── session registry ─────────────────────────────────────────────────────

    def sessions(self) -> set[GameSession]:
        return set(self._by_user.values())

    def get(self, user_id: int) -> GameSession | None:
        return self._by_user.get(user_id)

    def release(self, session: GameSession) -> None:
        """Forget the session and cancel any pending bump for its players."""
        for uid in session.players:
            if self._by_user.get(uid) is session:
                del self._by_user[uid]
            track = self._tracks.pop(uid, None)
            if track:
                self._by_channel.pop(track.channel_id, None)
                self._game_msg_ids.discard(track.message_id)

    # ── message tracking / bump timers ───────────────────────────────────────

    async def track(self, session: GameSession, uid: int, message: discord.Message) -> None:
        """Record the message currently showing this player's game and restart its bump timer."""
        old = self._tracks.get(uid)
        if old:
            self._game_msg_ids.discard(old.message_id)
            self._by_channel.pop(old.channel_id, None)
        channel_id = message.channel.id
        self._tracks[uid] = _Track(
            session=session, uid=uid, channel_id=channel_id, message_id=message.id,
            last_seen_id=message.id, due=self.clock() + self.bump_delay,
        )
        self._by_channel[channel_id] = uid
        self._game_msg_ids.add(message.id)
        try:
            await self.messages_repo.upsert(uid, channel_id, message.id, session.key)
        except Exception:
            logger.exception("could not persist game message for %s", uid)

    async def clear_messages(self, session: GameSession) -> None:
        try:
            await self.messages_repo.delete_for(list(session.players))
        except Exception:
            logger.exception("could not clear persisted game messages")

    def note_message(self, channel_id: int, message_id: int) -> None:
        """A message appeared in a DM channel: if a game lives there, restart its quiet timer."""
        uid = self._by_channel.get(channel_id)
        if uid is None or message_id in self._game_msg_ids:
            return
        track = self._tracks.get(uid)
        if track:
            track.last_seen_id = max(track.last_seen_id, message_id)
            track.due = self.clock() + self.bump_delay

    def note_deleted(self, message_id: int) -> None:
        """The player deleted a game message: re-post it on the next pass."""
        for track in self._tracks.values():
            if track.message_id == message_id:
                track.deleted = True
                track.due = 0.0
                return

    def note_game_activity(self, session: GameSession) -> None:
        """Someone used the game: both players' quiet timers restart."""
        due = self.clock() + self.bump_delay
        for uid in session.players:
            track = self._tracks.get(uid)
            if track and track.session is session:
                track.due = due

    async def cleanup_stale_messages(self) -> int:
        """After a restart, disable game messages left behind by the previous process."""
        rows = await self.messages_repo.pop_all()
        for row in rows:
            channel = self.bot.get_partial_messageable(row.channel_id, type=discord.ChannelType.private)
            try:
                await channel.get_partial_message(row.message_id).edit(
                    content="⏹️ This game ended because the bot restarted. Start a new one with `/play`.",
                    view=None,
                )
            except (discord.NotFound, discord.Forbidden):
                pass
            except discord.HTTPException:
                logger.warning("could not close stale game message %s", row.message_id, exc_info=True)
        return len(rows)

    # starting
    async def start(
        self,
        interaction: discord.Interaction,
        partner: discord.User,
        game_cls: type[GameSession],
        **options,
    ) -> GameSession | None:
        me = interaction.user
        # Reserve both players before any await so two commands can't race each other.
        for uid in (me.id, partner.id):
            existing = self._by_user.get(uid)
            if existing:
                who = "You're" if uid == me.id else f"{partner.display_name} is"
                await respond(
                    interaction,
                    f"{who} already in a game of **{existing.title}**. Finish it or use `/gamequit` first.",
                    ephemeral=True,
                )
                return None

        session = game_cls(self, me, partner, **options)  # type: ignore[arg-type]
        self._by_user[me.id] = self._by_user[partner.id] = session
        try:
            await session.setup()
            for uid in session.players:
                embed, items = session.render(uid)
                view = SessionView(session, uid, items)
                msg = await safe_dm(session.users[uid], embed=embed, view=view)
                if msg is None:
                    raise _DMClosed(uid)
                session.messages[uid] = msg
                session.views[uid] = view
                await self.track(session, uid, msg)
        except _DMClosed as closed:
            who = "your" if closed.uid == me.id else f"{partner.display_name}'s"
            await session.shutdown("Couldn't start — a DM was closed.")
            await respond(
                interaction,
                f"I couldn't DM {who} account — open DMs from server members (or from me) and try again.",
                ephemeral=True,
            )
            return None
        except Exception:
            logger.exception("failed to start %s", game_cls.__name__)
            self.release(session)
            await self.clear_messages(session)
            await respond(interaction, GENERIC_ERROR, ephemeral=True)
            return None

        session.touch()
        jump = session.messages[me.id].jump_url
        await respond(interaction, f"💌 **{session.title}** is ready in your DMs — [open it]({jump})", ephemeral=True)
        return session

    async def quit(self, user_id: int) -> GameSession | None:
        session = self._by_user.get(user_id)
        if session:
            name = session.name(user_id)
            await session.shutdown(f"🚪 {name} ended the game.")
        return session


class _DMClosed(Exception):
    def __init__(self, uid: int) -> None:
        self.uid = uid


async def partner_user(bot: discord.Client, partner_id: int) -> discord.User | None:
    return await resolve_user(bot, partner_id)
