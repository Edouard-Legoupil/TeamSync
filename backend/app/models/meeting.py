from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, new_id, utcnow
from app.models.enums import MeetingStatus

if TYPE_CHECKING:
    from app.models.action_item import ActionItem
    from app.models.meeting_series import MeetingSeries
    from app.models.team import Team
    from app.models.user import User


class Meeting(TimestampMixin, Base):
    """A single meeting and its AI-derived structured Markdown content.

    Markdown is the source of truth: ``minutes_markdown``,
    ``action_items_markdown`` and ``next_agenda_markdown`` are all stored as
    raw Markdown strings. ``ai_metadata`` is internal-only (never rendered to
    users).
    """

    __tablename__ = "meetings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    team_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False, index=True
    )
    organizer_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    series_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("meeting_series.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(32), default=MeetingStatus.DRAFT.value, nullable=False
    )

    # --- content ------------------------------------------------------------
    raw_transcript: Mapped[str] = mapped_column(Text, nullable=False, default="")
    minutes_markdown: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    action_items_markdown: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    next_agenda_markdown: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Internal tracking only (confidence, model version, processing time).
    ai_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # --- relationships ------------------------------------------------------
    team: Mapped["Team"] = relationship(back_populates="meetings")
    organizer: Mapped[Optional["User"]] = relationship(back_populates="organized_meetings")
    series: Mapped[Optional["MeetingSeries"]] = relationship(back_populates="meetings")
    action_items: Mapped[list["ActionItem"]] = relationship(
        back_populates="meeting", cascade="all, delete-orphan"
    )
