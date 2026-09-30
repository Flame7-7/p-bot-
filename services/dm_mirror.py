from __future__ import annotations

import discord

from repositories.relationship_repository import RelationshipRepository

_rel_repo = RelationshipRepository()


async def resolve_user(client: discord.Client, user_id: int) -> discord.User | None:
    user = client.get_user(user_id)
    if user:
        return user
    try:
        return await client.fetch_user(user_id)
    except discord.NotFound:
        return None


async def get_dm_partner(interaction: discord.Interaction) -> discord.User | None:
    """If this interaction is happening in a bot DM and the invoker has an
    active partner (see /propose), returns that partner's User object.
    Returns None in guild channels, or if there's no linked partner.
    """
    if not isinstance(interaction.channel, discord.DMChannel):
        return None
    partner_id = await _rel_repo.get_partner_id(interaction.user.id)
    if not partner_id:
        return None
    return await resolve_user(interaction.client, partner_id)


async def get_partner_id(user_id: int) -> int | None:
    return await _rel_repo.get_partner_id(user_id)


async def mirror_to_partner(interaction: discord.Interaction, **send_kwargs) -> discord.User | None:
    """Send the same content to the invoker's linked partner's DM, if any.
    Returns the partner (so callers can reuse it) or None if there wasn't one
    or delivery failed.
    """
    partner = await get_dm_partner(interaction)
    if not partner:
        return None
    try:
        await partner.send(**send_kwargs)
        return partner
    except discord.Forbidden:
        return None
