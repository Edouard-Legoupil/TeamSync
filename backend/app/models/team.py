from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, new_id
from app.models.enums import TeamMemberRole

if TYPE_CHECKING:
    from app.models.meeting import Meeting
    from app.models.user import User


class Team(TimestampMixin, Base):
    __tablename__ = "teams"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    manager_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    # Self-referential hierarchy for the Organigramme structure.
    parent_team_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("teams.id", ondelete="SET NULL"), nullable=True
    )
    # Workspace kind: team | personal | project | donor | operation.
    kind: Mapped[str] = mapped_column(String(32), nullable=False, default="team")

    # --- relationships ------------------------------------------------------
    manager: Mapped[Optional["User"]] = relationship(
        back_populates="teams_managed", foreign_keys=[manager_id]
    )
    parent_team: Mapped[Optional["Team"]] = relationship(
        remote_side=[id], back_populates="child_teams"
    )
    child_teams: Mapped[list["Team"]] = relationship(back_populates="parent_team")
    members: Mapped[list["TeamMember"]] = relationship(
        back_populates="team", cascade="all, delete-orphan"
    )
    meetings: Mapped[list["Meeting"]] = relationship(
        back_populates="team", cascade="all, delete-orphan"
    )


class TeamMember(TimestampMixin, Base):
    __tablename__ = "team_members"
    __table_args__ = (
        UniqueConstraint("team_id", "user_id", name="uq_team_membership"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    team_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(
        String(32), default=TeamMemberRole.VIEWER.value, nullable=False
    )

    # --- relationships ------------------------------------------------------
    team: Mapped["Team"] = relationship(back_populates="members")
    user: Mapped["User"] = relationship(back_populates="memberships")
