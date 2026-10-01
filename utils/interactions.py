"""Shared helpers for interaction handling, error replies and owned views."""
from __future__ import annotations

from collections.abc import Iterable

import discord

from utils.logging import get_logger

logger = get_logger(__name__)

GENERIC_ERROR = "Something went wrong on my side. Please try again in a moment 💔"


async def respond(
    interaction: discord.Interaction,
    content: str | None = None,
    *,
    ephemeral: bool = False,
    **kwargs,
) -> None:
    """Reply to an interaction whether or not it was already answered.

    Swallows the errors that happen when the interaction has expired or the
    channel/message is gone — there is nothing useful left to do in those cases.
    """
    try:
        if interaction.response.is_done():
            await interaction.followup.send(content, ephemeral=ephemeral, **kwargs)
        else:
            await interaction.response.send_message(content, ephemeral=ephemeral, **kwargs)
    except (discord.NotFound, discord.Forbidden):
        logger.debug("could not respond to interaction %s", interaction.id)
    except discord.HTTPException:
        logger.warning("HTTP error responding to interaction %s", interaction.id, exc_info=True)


async def safe_edit(message: discord.Message | None, **kwargs) -> bool:
    """Edit a message, tolerating deletion / permission loss. Returns success."""
    if message is None:
        return False
    try:
        await message.edit(**kwargs)
        return True
    except (discord.NotFound, discord.Forbidden):
        return False
    except discord.HTTPException:
        logger.warning("could not edit message %s", message.id, exc_info=True)
        return False


async def safe_dm(user: discord.abc.User, **kwargs) -> discord.Message | None:
    """DM a user; ``None`` if their DMs are closed or the account is gone."""
    try:
        return await user.send(**kwargs)
    except (discord.Forbidden, discord.NotFound):
        return None
    except discord.HTTPException:
        logger.warning("could not DM user %s", getattr(user, "id", "?"), exc_info=True)
        return None


async def resolve_user(client: discord.Client, user_id: int) -> discord.User | None:
    user = client.get_user(user_id)
    if user:
        return user
    try:
        return await client.fetch_user(user_id)
    except (discord.NotFound, discord.HTTPException):
        return None


def disable_all(view: discord.ui.View) -> None:
    for child in view.children:
        if hasattr(child, "disabled"):
            child.disabled = True  # type: ignore[attr-defined]


class OwnedView(discord.ui.View):
    """A view only its owners may use; buttons lock when it times out.

    ``owners`` are the user IDs allowed to interact. Anyone else gets a polite
    ephemeral refusal instead of silently controlling someone else's UI.
    """

    def __init__(self, owners: Iterable[int], *, timeout: float | None = 180.0) -> None:
        super().__init__(timeout=timeout)
        self.owners: set[int] = set(owners)
        self.message: discord.Message | None = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id in self.owners:
            return True
        await respond(interaction, "This one belongs to someone else 💕", ephemeral=True)
        return False

    async def on_timeout(self) -> None:
        disable_all(self)
        await safe_edit(self.message, view=self)

    async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item) -> None:
        logger.error("view error in %s (%s)", type(self).__name__, type(item).__name__, exc_info=error)
        await respond(interaction, GENERIC_ERROR, ephemeral=True)
