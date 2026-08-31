from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, new_id

if TYPE_CHECKING:
    from app.models.meeting import Meeting


class MeetingFollowUp(TimestampMixin, Base):
    """An AI-suggested follow-up (meeting, email, document share, 1:1, ad hoc)."""

    __tablename__ = "meeting_follow_ups"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    meeting_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    follow_up_type: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    issue: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    participants: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="suggested")

    meeting: Mapped["Meeting"] = relationship(back_populates="follow_ups")
