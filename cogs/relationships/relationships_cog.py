from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Button, View

from repositories.relationship_repository import RelationshipRepository
from views.embeds import build_relationship_embed, DiscordUIV2View
from utils.logging import get_logger

logger = get_logger(__name__)


class ProposalView(DiscordUIV2View):
    """Modern proposal view with Discord UI v2 styled buttons."""

    def __init__(self, proposer: discord.Member, proposal_id: int, repo: RelationshipRepository) -> None:
        super().__init__(timeout=86400)
        self.proposer = proposer
        self.proposal_id = proposal_id
        self.repo = repo

    @Button(label="💕 Accept", style=discord.ButtonStyle.success, custom_id="accept_proposal")
    async def accept(self, interaction: discord.Interaction, button: Button) -> None:
        """Accept the relationship proposal."""
        rel = await self.repo.accept_proposal(self.proposal_id)
        if not rel:
            await interaction.response.send_message("This proposal has expired.", ephemeral=True)
            return
        self.stop()
        embed = discord.Embed(
            title="💑 Relationship Started!",
            description=f"{self.proposer.mention} and {interaction.user.mention} are now partners! 💕",
            color=0xFF85A1,
        )
        embed.set_footer(text="Wishing you both happiness together!")
        embed.timestamp = discord.utils.utcnow()
        await interaction.response.edit_message(embed=embed, view=None)

    @Button(label="💔 Decline", style=discord.ButtonStyle.danger, custom_id="decline_proposal")
    async def decline(self, interaction: discord.Interaction, button: Button) -> None:
        """Decline the relationship proposal."""
        await self.repo.decline_proposal(self.proposal_id)
        self.stop()
        embed = discord.Embed(
            title="💔 Proposal Declined",
            description=f"{interaction.user.display_name} declined the proposal.",
            color=0xED4245,
        )
        embed.timestamp = discord.utils.utcnow()
        await interaction.response.edit_message(embed=embed, view=None)


class RelationshipsCog(commands.Cog, name="Relationships"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.repo = RelationshipRepository()

    @app_commands.command(name="propose", description="Propose a relationship to someone")
    @app_commands.describe(user="The user you want to propose to")
    async def propose(self, interaction: discord.Interaction, user: discord.Member) -> None:
        if user.id == interaction.user.id:
            await interaction.response.send_message("You can't propose to yourself!", ephemeral=True)
            return
        if user.bot:
            await interaction.response.send_message("You can't propose to a bot!", ephemeral=True)
            return
        if await self.repo.get_relationship(interaction.user.id):
            await interaction.response.send_message("You're already in a relationship!", ephemeral=True)
            return
        if await self.repo.get_relationship(user.id):
            await interaction.response.send_message(f"{user.display_name} is already in a relationship!", ephemeral=True)
            return

        proposal = await self.repo.create_proposal(interaction.user.id, user.id)
        embed = discord.Embed(
            title="💍 Proposal!",
            description=f"{interaction.user.mention} is proposing to {user.mention}!\n*Expires in 24 hours*",
            color=0xFFB347,
        )
        embed.set_footer(text="Choose wisely!")
        embed.timestamp = discord.utils.utcnow()
        view = ProposalView(interaction.user, proposal.id, self.repo)  # type: ignore[arg-type]
        await interaction.response.send_message(content=user.mention, embed=embed, view=view)

    @app_commands.command(name="partner", description="View your relationship")
    async def partner(self, interaction: discord.Interaction) -> None:
        rel = await self.repo.get_relationship(interaction.user.id)
        if not rel:
            await interaction.response.send_message("You're not in a relationship!", ephemeral=True)
            return
        partner_id = rel.user2_id if rel.user1_id == interaction.user.id else rel.user1_id
        partner = interaction.guild.get_member(partner_id) if interaction.guild else None
        if not partner:
            await interaction.response.send_message("Your partner isn't in this server!", ephemeral=True)
            return
        embed = build_relationship_embed(interaction.user, partner, rel)  # type: ignore[arg-type]
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="breakup", description="End your relationship")
    async def breakup(self, interaction: discord.Interaction) -> None:
        if not await self.repo.get_relationship(interaction.user.id):
            await interaction.response.send_message("You're not in a relationship!", ephemeral=True)
            return
        await self.repo.end_relationship(interaction.user.id)
        embed = discord.Embed(
            title="💔 Relationship Ended",
            description=f"{interaction.user.display_name} ended their relationship.",
            color=0xED4245,
        )
        embed.set_footer(text="New beginnings await...")
        embed.timestamp = discord.utils.utcnow()
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="anniversary", description="Check your relationship anniversary")
    async def anniversary(self, interaction: discord.Interaction) -> None:
        rel = await self.repo.get_relationship(interaction.user.id)
        if not rel:
            await interaction.response.send_message("You're not in a relationship!", ephemeral=True)
            return
        from datetime import datetime, timezone
        days = (datetime.now(timezone.utc) - rel.started_at.replace(tzinfo=timezone.utc)).days
        embed = discord.Embed(
            title="🗓️ Anniversary",
            description=f"You've been together for **{days} day{'s' if days != 1 else ''}**! 💕",
            color=0xFF85A1,
        )
        embed.add_field(name="Started", value=rel.started_at.strftime("%b %d, %Y"))
        embed.set_footer(text="May your bond grow stronger!")
        embed.timestamp = discord.utils.utcnow()
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(RelationshipsCog(bot))

+++ cogs/relationships/relationships_cog.py (修改后)
from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Button, View, button

from repositories.relationship_repository import RelationshipRepository
from views.embeds import build_relationship_embed, DiscordUIV2View
from utils.logging import get_logger

logger = get_logger(__name__)


class ProposalView(DiscordUIV2View):
    """Modern proposal view with Discord UI v2 styled buttons."""

    def __init__(self, proposer: discord.Member, proposal_id: int, repo: RelationshipRepository) -> None:
        super().__init__(timeout=86400)
        self.proposer = proposer
        self.proposal_id = proposal_id
        self.repo = repo

    @button(label="💕 Accept", style=discord.ButtonStyle.success, custom_id="accept_proposal")
    async def accept(self, interaction: discord.Interaction, button: Button) -> None:
        """Accept the relationship proposal."""
        rel = await self.repo.accept_proposal(self.proposal_id)
        if not rel:
            await interaction.response.send_message("This proposal has expired.", ephemeral=True)
            return
        self.stop()
        embed = discord.Embed(
            title="💑 Relationship Started!",
            description=f"{self.proposer.mention} and {interaction.user.mention} are now partners! 💕",
            color=0xFF85A1,
        )
        embed.set_footer(text="Wishing you both happiness together!")
        embed.timestamp = discord.utils.utcnow()
        await interaction.response.edit_message(embed=embed, view=None)

    @button(label="💔 Decline", style=discord.ButtonStyle.danger, custom_id="decline_proposal")
    async def decline(self, interaction: discord.Interaction, button: Button) -> None:
        """Decline the relationship proposal."""
        await self.repo.decline_proposal(self.proposal_id)
        self.stop()
        embed = discord.Embed(
            title="💔 Proposal Declined",
            description=f"{interaction.user.display_name} declined the proposal.",
            color=0xED4245,
        )
        embed.timestamp = discord.utils.utcnow()
        await interaction.response.edit_message(embed=embed, view=None)


class RelationshipsCog(commands.Cog, name="Relationships"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.repo = RelationshipRepository()

    @app_commands.command(name="propose", description="Propose a relationship to someone")
    @app_commands.describe(user="The user you want to propose to")
    async def propose(self, interaction: discord.Interaction, user: discord.Member) -> None:
        if user.id == interaction.user.id:
            await interaction.response.send_message("You can't propose to yourself!", ephemeral=True)
            return
        if user.bot:
            await interaction.response.send_message("You can't propose to a bot!", ephemeral=True)
            return
        if await self.repo.get_relationship(interaction.user.id):
            await interaction.response.send_message("You're already in a relationship!", ephemeral=True)
            return
        if await self.repo.get_relationship(user.id):
            await interaction.response.send_message(f"{user.display_name} is already in a relationship!", ephemeral=True)
            return

        proposal = await self.repo.create_proposal(interaction.user.id, user.id)
        embed = discord.Embed(
            title="💍 Proposal!",
            description=f"{interaction.user.mention} is proposing to {user.mention}!\n*Expires in 24 hours*",
            color=0xFFB347,
        )
        embed.set_footer(text="Choose wisely!")
        embed.timestamp = discord.utils.utcnow()
        view = ProposalView(interaction.user, proposal.id, self.repo)  # type: ignore[arg-type]
        await interaction.response.send_message(content=user.mention, embed=embed, view=view)

    @app_commands.command(name="partner", description="View your relationship")
    async def partner(self, interaction: discord.Interaction) -> None:
        rel = await self.repo.get_relationship(interaction.user.id)
        if not rel:
            await interaction.response.send_message("You're not in a relationship!", ephemeral=True)
            return
        partner_id = rel.user2_id if rel.user1_id == interaction.user.id else rel.user1_id
        partner = interaction.guild.get_member(partner_id) if interaction.guild else None
        if not partner:
            await interaction.response.send_message("Your partner isn't in this server!", ephemeral=True)
            return
        embed = build_relationship_embed(interaction.user, partner, rel)  # type: ignore[arg-type]
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="breakup", description="End your relationship")
    async def breakup(self, interaction: discord.Interaction) -> None:
        if not await self.repo.get_relationship(interaction.user.id):
            await interaction.response.send_message("You're not in a relationship!", ephemeral=True)
            return
        await self.repo.end_relationship(interaction.user.id)
        embed = discord.Embed(
            title="💔 Relationship Ended",
            description=f"{interaction.user.display_name} ended their relationship.",
            color=0xED4245,
        )
        embed.set_footer(text="New beginnings await...")
        embed.timestamp = discord.utils.utcnow()
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="anniversary", description="Check your relationship anniversary")
    async def anniversary(self, interaction: discord.Interaction) -> None:
        rel = await self.repo.get_relationship(interaction.user.id)
        if not rel:
            await interaction.response.send_message("You're not in a relationship!", ephemeral=True)
            return
        from datetime import datetime, timezone
        days = (datetime.now(timezone.utc) - rel.started_at.replace(tzinfo=timezone.utc)).days
        embed = discord.Embed(
            title="🗓️ Anniversary",
            description=f"You've been together for **{days} day{'s' if days != 1 else ''}**! 💕",
            color=0xFF85A1,
        )
        embed.add_field(name="Started", value=rel.started_at.strftime("%b %d, %Y"))
        embed.set_footer(text="May your bond grow stronger!")
        embed.timestamp = discord.utils.utcnow()
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(RelationshipsCog(bot))
