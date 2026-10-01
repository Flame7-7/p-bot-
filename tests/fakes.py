"""Minimal stand-ins for discord objects so game logic can run without a gateway."""
from __future__ import annotations

import discord


class FakeMessage:
    _next = 1000

    def __init__(self, owner: "FakeUser") -> None:
        FakeMessage._next += 1
        self.id = FakeMessage._next
        self.owner = owner
        self.embed: discord.Embed | None = None
        self.view: discord.ui.View | None = None
        self.jump_url = f"https://discord.com/channels/@me/1/{self.id}"

    async def edit(self, **kw) -> None:
        self.embed = kw.get("embed", self.embed)
        self.view = kw.get("view", self.view)


class FakeUser:
    def __init__(self, uid: int, name: str) -> None:
        self.id, self.display_name = uid, name
        self.dms: list[FakeMessage] = []

    async def send(self, embed=None, view=None, **kw) -> FakeMessage:
        m = FakeMessage(self)
        m.embed, m.view = embed, view
        self.dms.append(m)
        return m


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
