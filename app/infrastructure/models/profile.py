from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.enums import ProfileStatus
from app.infrastructure.models.base import Base


class ProfileModel(Base):
    __tablename__ = "profiles"
    # The unique constraint also serves lookups by user_id (it is the leading column), so there is no separate index.
    __table_args__ = (
        UniqueConstraint("user_id", "category_id", "role_id"),
        Index("ix_profiles_category_id_role_id_status", "category_id", "role_id", "status"),
        Index("ix_profiles_extra_attributes", "extra_attributes", postgresql_using="gin"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    # No ondelete on category/role: deleting a taxonomy row that profiles still use must fail, not wipe profiles.
    category_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("categories.id"), nullable=False)
    role_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("roles.id"), nullable=False)
    country_code: Mapped[str] = mapped_column(String(2), nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False)
    bio: Mapped[str] = mapped_column(Text, nullable=False)
    goals_description: Mapped[str] = mapped_column(Text, nullable=False)
    extra_attributes: Mapped[dict[str, str]] = mapped_column(JSONB, nullable=False)
    status: Mapped[ProfileStatus] = mapped_column(
        Enum(ProfileStatus, name="profile_status", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ProfileTagModel(Base):
    __tablename__ = "profile_tags"

    profile_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("profiles.id", ondelete="CASCADE"), primary_key=True
    )
    tag_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True, index=True
    )
