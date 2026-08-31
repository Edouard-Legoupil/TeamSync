from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Column, ForeignKey, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import new_id

if TYPE_CHECKING:
    from app.models.action_item import ActionItem

# Many-to-many between ActionItem and Tag (no extra columns).
action_item_tags = Table(
    "action_item_tags",
    Base.metadata,
    Column(
        "action_item_id",
        String(36),
        ForeignKey("action_items.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "tag_id",
        String(36),
        ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Tag(Base):
    """A multi-dimensional label (thematic, organizational, geographic, process,
    behavior) attached to action items. Tags are global/shared across teams."""

    __tablename__ = "tags"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    type: Mapped[str] = mapped_column(String(32), nullable=False, default="thematic")

    action_items: Mapped[list["ActionItem"]] = relationship(
        secondary=action_item_tags, back_populates="tags"
    )
