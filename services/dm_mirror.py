from __future__ import annotations

import discord

from repositories.relationship_repository import RelationshipRepository
from utils.interactions import resolve_user, safe_dm

_rel_repo = RelationshipRepository()


async def get_dm_partner(interaction: discord.Interaction) -> discord.User | None:
    """The invoker's linked partner (see /propose) when the interaction happens in a DM."""
    if not isinstance(interaction.channel, discord.DMChannel):
        return None
    return await get_partner(interaction.client, interaction.user.id)


async def get_partner(client: discord.Client, user_id: int) -> discord.User | None:
    """The user's linked partner as a User object, or None if single / unresolvable."""
    partner_id = await _rel_repo.get_partner_id(user_id)
    return await resolve_user(client, partner_id) if partner_id else None


async def get_partner_id(user_id: int) -> int | None:
    return await _rel_repo.get_partner_id(user_id)


async def mirror_to_partner(interaction: discord.Interaction, **send_kwargs) -> discord.User | None:
    partner = await get_dm_partner(interaction)
    if partner and await safe_dm(partner, **send_kwargs):
        return partner
    return None
