"""Minimal stand-ins for discord objects so game logic can run without a gateway."""
from __future__ import annotations

import discord


class FakeChannel:
    """A DM channel: remembers its messages in order so tests can see what is 'at the bottom'."""

    _next_id = 5000

    def __init__(self, cid: int, owner: "FakeUser") -> None:
        self.id, self.owner = cid, owner
        self.messages: list[FakeMessage] = []
        self.fail_send: Exception | None = None
        self.reject_reference: Exception | None = None

    async def send(self, content=None, embed=None, view=None, reference=None, **kw) -> "FakeMessage":
        if self.fail_send:
            raise self.fail_send
        if reference is not None and self.reject_reference is not None:
            raise self.reject_reference
        return self.post(embed=embed, view=view, content=content, reference=reference)

    def post(self, embed=None, view=None, content=None, author_is_bot=True, reference=None) -> "FakeMessage":
        FakeMessage._next += 1
        m = FakeMessage(self, FakeMessage._next)
        m.embed, m.view, m.content, m.reference = embed, view, content, reference
        self.messages.append(m)
        return m

    @property
    def last(self) -> "FakeMessage | None":
        return self.messages[-1] if self.messages else None


class FakeMessage:
    _next = 1000

    def __init__(self, channel: FakeChannel, mid: int) -> None:
        self.id = mid
        self.channel = channel
        self.embed: discord.Embed | None = None
        self.view: discord.ui.View | None = None
        self.content: str | None = None
        self.reference = None
        self.deleted = False
        self.fail_delete: Exception | None = None
        self.jump_url = f"https://discord.com/channels/@me/{channel.id}/{mid}"

    async def edit(self, **kw) -> None:
        if self.deleted:
            raise discord.NotFound(_Resp(404), "Unknown Message")
        self.embed = kw.get("embed", self.embed)
        self.view = kw.get("view", self.view)

    async def delete(self) -> None:
        if self.fail_delete:
            raise self.fail_delete
        if self.deleted:
            raise discord.NotFound(_Resp(404), "Unknown Message")
        self.deleted = True
        self.channel.messages.remove(self)


class _Resp:
    def __init__(self, status: int) -> None:
        self.status, self.reason = status, "x"


class FakeUser:
    def __init__(self, uid: int, name: str) -> None:
        self.id, self.display_name = uid, name
        self.bot = False
        self.display_avatar = type("Av", (), {"url": "http://x/a.png"})()
        self.channel = FakeChannel(uid * 100, self)

    @property
    def dms(self) -> list[FakeMessage]:
        return self.channel.messages

    async def send(self, embed=None, view=None, **kw) -> FakeMessage:
        return await self.channel.send(embed=embed, view=view, **kw)


class FakeResponse:
    def __init__(self, inter: "FakeInteraction") -> None:
        self.inter = inter
        self.done = False
        self.sent: list[dict] = []
        self.modal = None

    def is_done(self) -> bool:
        return self.done

    async def edit_message(self, **kw) -> None:
        self.done = True
        msg = self.inter.message
        if msg:
            await msg.edit(**kw)

    async def autocomplete(self, *a, **k) -> None:  # pragma: no cover - not used
        self.done = True

    async def send_message(self, content=None, **kw) -> None:
        self.done = True
        self.sent.append({"content": content, **kw})

    async def defer(self, **kw) -> None:
        self.done = True

    async def send_modal(self, modal) -> None:
        self.done = True
        self.modal = modal


class FakeFollowup:
    def __init__(self, inter) -> None:
        self.inter = inter

    async def send(self, content=None, **kw) -> None:
        self.inter.response.sent.append({"content": content, **kw})


class FakeInteraction:
    def __init__(self, user: FakeUser, message: FakeMessage | None = None) -> None:
        self.user = user
        self.message = message
        self.response = FakeResponse(self)
        self.followup = FakeFollowup(self)
        self.id = 1
        self.guild = None
        self.guild_id = None
        self.channel = None
        self.data: dict = {}

    async def edit_original_response(self, **kw) -> None:
        self.response.sent.append({"edited": True, **kw})

    async def original_response(self) -> "FakeMessage":
        if self.message is None:
            self.message = FakeChannel(7, self.user).post()
        return self.message

    @property
    def last_text(self) -> str:
        return (self.response.sent[-1]["content"] or "") if self.response.sent else ""


def find(view: discord.ui.View, label_part: str):
    for child in view.children:
        if getattr(child, "label", None) and label_part in child.label and not child.disabled:
            return child
    raise LookupError(f"no enabled item containing {label_part!r}: {[getattr(c, 'label', None) for c in view.children]}")


async def click(session, user: FakeUser, label_part: str) -> FakeInteraction:
    """Press a button the way Discord would: interaction_check first, then the callback."""
    view = session.views[user.id]
    item = find(view, label_part)
    inter = FakeInteraction(user, session.messages[user.id])
    if await view.interaction_check(inter):
        await item.callback(inter)
    return inter


async def submit(modal, user: FakeUser, text: str, session) -> FakeInteraction:
    """Fill in and submit a modal through its real on_submit (so the session lock/push run)."""
    modal.field._value = text
    inter = FakeInteraction(user, session.messages[user.id])
    await modal.on_submit(inter)
    return inter
