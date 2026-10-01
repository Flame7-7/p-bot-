from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean, DateTime, Float, ForeignKey,
    Index, Integer, String, Text, UniqueConstraint, func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)  # Discord user ID
    username: Mapped[str] = mapped_column(String(100))
    avatar_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False)

    profile: Mapped[Optional["Profile"]] = relationship(back_populates="user", uselist=False)
    stats: Mapped[Optional["Statistics"]] = relationship(back_populates="user", uselist=False)
    settings: Mapped[Optional["UserSettings"]] = relationship(back_populates="user", uselist=False)
    achievements: Mapped[list["UserAchievement"]] = relationship(back_populates="user")


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    level: Mapped[int] = mapped_column(Integer, default=1)
    xp: Mapped[int] = mapped_column(Integer, default=0)
    total_xp: Mapped[int] = mapped_column(Integer, default=0)
    affection: Mapped[int] = mapped_column(Integer, default=0)
    title: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    favorite_action: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    user: Mapped["User"] = relationship(back_populates="profile")

    __table_args__ = (
        Index("ix_profiles_level", "level"),
        Index("ix_profiles_affection", "affection"),
    )


class Relationship(Base):
    __tablename__ = "relationships"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user1_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    user2_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String(20), default="active")
    shared_affection: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_rel_user1", "user1_id"),
        Index("ix_rel_user2", "user2_id"),
    )


class RelationshipProposal(Base):
    __tablename__ = "relationship_proposals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    proposer_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    target_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime)


class Interaction(Base):
    __tablename__ = "interactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    author_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    target_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    guild_id: Mapped[int] = mapped_column(Integer)
    action: Mapped[str] = mapped_column(String(50))
    affection_given: Mapped[int] = mapped_column(Integer, default=0)
    xp_given: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("ix_inter_author", "author_id"),
        Index("ix_inter_action", "action"),
    )


class Achievement(Base):
    __tablename__ = "achievements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(100), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text)
    icon: Mapped[str] = mapped_column(String(10), default="🏆")
    category: Mapped[str] = mapped_column(String(50))
    is_hidden: Mapped[bool] = mapped_column(Boolean, default=False)
    is_rare: Mapped[bool] = mapped_column(Boolean, default=False)
    xp_reward: Mapped[int] = mapped_column(Integer, default=0)
    condition_type: Mapped[str] = mapped_column(String(50))
    condition_value: Mapped[int] = mapped_column(Integer, default=0)

    user_achievements: Mapped[list["UserAchievement"]] = relationship(back_populates="achievement")


class UserAchievement(Base):
    __tablename__ = "user_achievements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    achievement_id: Mapped[int] = mapped_column(Integer, ForeignKey("achievements.id", ondelete="CASCADE"))
    progress: Mapped[int] = mapped_column(Integer, default=0)
    unlocked_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    is_unlocked: Mapped[bool] = mapped_column(Boolean, default=False)

    user: Mapped["User"] = relationship(back_populates="achievements")
    achievement: Mapped["Achievement"] = relationship(back_populates="user_achievements")

    __table_args__ = (
        UniqueConstraint("user_id", "achievement_id", name="uq_user_achievement"),
    )


class GIF(Base):
    __tablename__ = "gifs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category: Mapped[str] = mapped_column(String(50))
    url: Mapped[str] = mapped_column(String(512))
    name: Mapped[str] = mapped_column(String(100), nullable=True)
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    is_disabled: Mapped[bool] = mapped_column(Boolean, default=False)
    source: Mapped[str] = mapped_column(String(50), default="manual")

    __table_args__ = (Index("ix_gifs_category", "category"),)


class Statistics(Base):
    __tablename__ = "statistics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    total_given: Mapped[int] = mapped_column(Integer, default=0)
    total_received: Mapped[int] = mapped_column(Integer, default=0)
    daily_given: Mapped[int] = mapped_column(Integer, default=0)
    weekly_given: Mapped[int] = mapped_column(Integer, default=0)
    favorite_action: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    last_daily_reset: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="stats")


class UserSettings(Base):
    __tablename__ = "user_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    allow_interactions: Mapped[bool] = mapped_column(Boolean, default=True)
    show_in_leaderboard: Mapped[bool] = mapped_column(Boolean, default=True)

    user: Mapped["User"] = relationship(back_populates="settings")


class RoleplayProfile(Base):
    """Persisted replacement for the old in-memory `user_profiles = {}` in
    verification.py. Not a FK to `users.id` (same pattern as
    Interaction.target_id / GuildSettings.guild_id below) so that setting
    a role/consent works even before a user has run any roleplay command
    that would create their `users` row via UserRepository.get_or_create.
    """
    __tablename__ = "roleplay_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, unique=True)
    gender: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    consent_given: Mapped[bool] = mapped_column(Boolean, default=False)
    consented_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (Index("ix_roleplay_profiles_user", "user_id"),)


class PersonaProfile(Base):
    """A user's texting-style description, used to generate auto-replies
    in their voice when AFK mode is on (see cogs/persona)."""

    __tablename__ = "persona_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, unique=True)
    persona_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    afk_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    auto_afk: Mapped[bool] = mapped_column(Boolean, default=True)
    label_replies: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (Index("ix_persona_profiles_user", "user_id"),)


class PersonaChannel(Base):
    """Per-guild persona setup: the one channel where persona replies happen."""

    __tablename__ = "persona_channels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    guild_id: Mapped[int] = mapped_column(Integer, unique=True)
    channel_id: Mapped[int] = mapped_column(Integer)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    configured_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class CoupleGameStat(Base):
    """Running score for a couple in one DM game. ``user_low_id`` < ``user_high_id``."""

    __tablename__ = "couple_game_stats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_low_id: Mapped[int] = mapped_column(Integer)
    user_high_id: Mapped[int] = mapped_column(Integer)
    game: Mapped[str] = mapped_column(String(40))
    plays: Mapped[int] = mapped_column(Integer, default=0)
    low_wins: Mapped[int] = mapped_column(Integer, default=0)
    high_wins: Mapped[int] = mapped_column(Integer, default=0)
    draws: Mapped[int] = mapped_column(Integer, default=0)
    points: Mapped[int] = mapped_column(Integer, default=0)  # co-op score (match %, trivia, ...)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (UniqueConstraint("user_low_id", "user_high_id", "game", name="uq_couple_game"),)


class CoupleMilestone(Base):
    """A date a couple wants to remember or count down to."""

    __tablename__ = "couple_milestones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_low_id: Mapped[int] = mapped_column(Integer)
    user_high_id: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(80))
    event_date: Mapped[datetime] = mapped_column(DateTime)
    yearly: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by: Mapped[int] = mapped_column(Integer)

    __table_args__ = (Index("ix_couple_milestones_pair", "user_low_id", "user_high_id"),)


class JournalEntry(Base):
    """A private shared-journal note, visible to the author's partner via /couple memories."""

    __tablename__ = "couple_journal"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_low_id: Mapped[int] = mapped_column(Integer)
    user_high_id: Mapped[int] = mapped_column(Integer)
    author_id: Mapped[int] = mapped_column(Integer)
    prompt: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (Index("ix_couple_journal_pair", "user_low_id", "user_high_id"),)


class CustomCommand(Base):
    """Guild-scoped, database-backed user/admin-created slash command."""

    __tablename__ = "custom_commands"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    guild_id: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String(32))
    response: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(String(100), default="Custom server command")
    category: Mapped[str] = mapped_column(String(50), default="custom")
    creator_id: Mapped[int] = mapped_column(Integer)
    cooldown_seconds: Mapped[int] = mapped_column(Integer, default=0)
    requires_target: Mapped[bool] = mapped_column(Boolean, default=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint("guild_id", "name", name="uq_custom_commands_guild_name"),
        Index("ix_custom_commands_guild", "guild_id"),
    )


class GuildSettings(Base):
    __tablename__ = "guild_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    guild_id: Mapped[int] = mapped_column(Integer, unique=True)
    roleplay_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    xp_multiplier: Mapped[float] = mapped_column(Float, default=1.0)


class NoFapStreak(Base):
    """Personal habit-tracking streak, entirely separate from the
    roleplay/consent system. Same `user_id`-keyed, no-FK pattern as
    RoleplayProfile so a user can `/nofap start` without needing a
    `users` row first.
    """
    __tablename__ = "nofap_streaks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, unique=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_reset_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    reset_count: Mapped[int] = mapped_column(Integer, default=0)
    best_streak_days: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    partner_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    __table_args__ = (Index("ix_nofap_streaks_user", "user_id"),)
