from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, new_id

if TYPE_CHECKING:
    from app.models.meeting import Meeting


class MeetingSeries(TimestampMixin, Base):
    """A recurring meeting thread. Meetings in a series can roll open action
    items forward into the next meeting's agenda."""

    __tablename__ = "meeting_series"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    team_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False, index=True
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    meetings: Mapped[list["Meeting"]] = relationship(back_populates="series")
