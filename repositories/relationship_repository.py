from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import or_, select

from database.connection import get_session
from models.models import Relationship, RelationshipProposal
from utils.logging import get_logger

logger = get_logger(__name__)


class RelationshipRepository:
    async def get_relationship(self, user_id: int) -> Relationship | None:
        async with get_session() as session:
            r = await session.execute(
                select(Relationship).where(
                    Relationship.status == "active",
                    or_(
                        Relationship.user1_id == user_id,
                        Relationship.user2_id == user_id,
                    ),
                )
            )
            return r.scalar_one_or_none()

    async def get_partner_id(self, user_id: int) -> int | None:
        rel = await self.get_relationship(user_id)
        if not rel:
            return None
        return rel.user2_id if rel.user1_id == user_id else rel.user1_id

    async def create_proposal(
        self, proposer_id: int, target_id: int
    ) -> RelationshipProposal:
        async with get_session() as session:
            # Expire old pending proposals from this proposer
            r = await session.execute(
                select(RelationshipProposal).where(
                    RelationshipProposal.proposer_id == proposer_id,
                    RelationshipProposal.status == "pending",
                )
            )
            for old in r.scalars().all():
                old.status = "expired"

            proposal = RelationshipProposal(
                proposer_id=proposer_id,
                target_id=target_id,
                expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
            )
            session.add(proposal)
            await session.flush()
            return proposal

    async def get_pending_proposal(
        self, target_id: int
    ) -> RelationshipProposal | None:
        async with get_session() as session:
            r = await session.execute(
                select(RelationshipProposal).where(
                    RelationshipProposal.target_id == target_id,
                    RelationshipProposal.status == "pending",
                    RelationshipProposal.expires_at > datetime.now(timezone.utc),
                ).order_by(RelationshipProposal.created_at.desc())
            )
            return r.scalars().first()

    async def accept_proposal(self, proposal_id: int) -> Relationship | None:
        async with get_session() as session:
            r = await session.execute(
                select(RelationshipProposal).where(
                    RelationshipProposal.id == proposal_id
                )
            )
            proposal = r.scalar_one_or_none()
            if not proposal or proposal.status != "pending":
                return None
            proposal.status = "accepted"
            rel = Relationship(
                user1_id=proposal.proposer_id,
                user2_id=proposal.target_id,
            )
            session.add(rel)
            await session.flush()
            return rel

    async def decline_proposal(self, proposal_id: int) -> bool:
        async with get_session() as session:
            r = await session.execute(
                select(RelationshipProposal).where(
                    RelationshipProposal.id == proposal_id
                )
            )
            proposal = r.scalar_one_or_none()
            if not proposal:
                return False
            proposal.status = "declined"
            return True

    async def end_relationship(self, user_id: int) -> bool:
        async with get_session() as session:
            r = await session.execute(
                select(Relationship).where(
                    Relationship.status == "active",
                    or_(
                        Relationship.user1_id == user_id,
                        Relationship.user2_id == user_id,
                    ),
                )
            )
            rel = r.scalar_one_or_none()
            if not rel:
                return False
            rel.status = "ended"
            rel.ended_at = datetime.now(timezone.utc)
            return True

    async def add_shared_affection(self, user_id: int, amount: int) -> None:
        async with get_session() as session:
            r = await session.execute(
                select(Relationship).where(
                    Relationship.status == "active",
                    or_(
                        Relationship.user1_id == user_id,
                        Relationship.user2_id == user_id,
                    ),
                )
            )
            rel = r.scalar_one_or_none()
            if rel:
                rel.shared_affection += amount
