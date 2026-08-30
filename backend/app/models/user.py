from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, new_id
from app.models.enums import UserRole

if TYPE_CHECKING:
    from app.models.action_item import ActionItem
    from app.models.meeting import Meeting
    from app.models.team import Team, TeamMember


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    role: Mapped[str] = mapped_column(
        String(32), default=UserRole.MEMBER.value, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)

    # --- relationships ------------------------------------------------------
    teams_managed: Mapped[list["Team"]] = relationship(
        back_populates="manager", foreign_keys="Team.manager_id"
    )
    memberships: Mapped[list["TeamMember"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    organized_meetings: Mapped[list["Meeting"]] = relationship(back_populates="organizer")
    assigned_action_items: Mapped[list["ActionItem"]] = relationship(
        back_populates="assignee", foreign_keys="ActionItem.assignee_id"
    )
