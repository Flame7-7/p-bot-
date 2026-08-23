from __future__ import annotations

from sqlalchemy import delete, select

from database.connection import get_session
from models.models import CustomCommand


class CustomCommandRepository:
    """Async persistence for guild-scoped custom slash commands."""

    async def get(self, guild_id: int, name: str) -> CustomCommand | None:
        async with get_session() as session:
            result = await session.execute(
                select(CustomCommand).where(
                    CustomCommand.guild_id == guild_id,
                    CustomCommand.name == name,
                )
            )
            return result.scalar_one_or_none()

    async def get_by_id(self, command_id: int) -> CustomCommand | None:
        async with get_session() as session:
            result = await session.execute(
                select(CustomCommand).where(CustomCommand.id == command_id)
            )
            return result.scalar_one_or_none()

    async def list_for_guild(self, guild_id: int, include_disabled: bool = False) -> list[CustomCommand]:
        async with get_session() as session:
            stmt = select(CustomCommand).where(CustomCommand.guild_id == guild_id)
            if not include_disabled:
                stmt = stmt.where(CustomCommand.enabled.is_(True))
            stmt = stmt.order_by(CustomCommand.name)
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def create(
        self,
        guild_id: int,
        name: str,
        response: str,
        description: str,
        category: str,
        creator_id: int,
        cooldown_seconds: int,
        requires_target: bool,
    ) -> CustomCommand:
        async with get_session() as session:
            command = CustomCommand(
                guild_id=guild_id,
                name=name,
                response=response,
                description=description,
                category=category,
                creator_id=creator_id,
                cooldown_seconds=cooldown_seconds,
                requires_target=requires_target,
                enabled=True,
            )
            session.add(command)
            await session.flush()
            await session.refresh(command)
            return command

    async def update(self, command_id: int, **changes) -> CustomCommand | None:
        async with get_session() as session:
            result = await session.execute(
                select(CustomCommand).where(CustomCommand.id == command_id)
            )
            command = result.scalar_one_or_none()
            if not command:
                return None
            for key, value in changes.items():
                if value is not None:
                    setattr(command, key, value)
            await session.flush()
            await session.refresh(command)
            return command

    async def delete(self, command_id: int) -> bool:
        async with get_session() as session:
            result = await session.execute(
                delete(CustomCommand).where(CustomCommand.id == command_id)
            )
            return bool(result.rowcount)
