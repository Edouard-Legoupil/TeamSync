from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Date, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, new_id
from app.models.enums import ActionItemPriority, ActionItemStatus

if TYPE_CHECKING:
    from app.models.meeting import Meeting
    from app.models.user import User


class ActionItem(TimestampMixin, Base):
    """A trackable action item derived from a meeting transcript.

    This exists for tracking/completion only. The canonical text still lives
    inside ``Meeting.action_items_markdown``; ``source_markdown`` points back
    to the exact table row so edits can be synced back to Markdown.
    """

    __tablename__ = "action_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    meeting_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    assignee_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    priority: Mapped[str] = mapped_column(
        String(32), default=ActionItemPriority.MEDIUM.value, nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(32), default=ActionItemStatus.OPEN.value, nullable=False
    )
    source_markdown: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Points at an existing open ActionItem (in another meeting) that this one
    # duplicates. Deduplication keeps the tracker free of double-counted items.
    duplicate_of_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("action_items.id", ondelete="SET NULL"), nullable=True
    )

    # --- relationships ------------------------------------------------------
    meeting: Mapped["Meeting"] = relationship(back_populates="action_items")
    assignee: Mapped[Optional["User"]] = relationship(
        back_populates="assigned_action_items", foreign_keys=[assignee_id]
    )
    duplicate_of: Mapped[Optional["ActionItem"]] = relationship(
        remote_side=[id], foreign_keys=[duplicate_of_id]
    )
