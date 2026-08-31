from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, new_id

if TYPE_CHECKING:
    from app.models.action_item import ActionItem
    from app.models.user import User


class ActionItemComment(TimestampMixin, Base):
    """A free-form note attached to an action item.

    Kept separate from the Markdown source of truth; comments are annotations
    that don't belong in the exported action-items table.
    """

    __tablename__ = "action_item_comments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    action_item_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("action_items.id", ondelete="CASCADE"), nullable=False, index=True
    )
    author_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    parent_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("action_item_comments.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)

    action_item: Mapped["ActionItem"] = relationship(back_populates="comments")
    author: Mapped[Optional["User"]] = relationship()
    parent: Mapped[Optional["ActionItemComment"]] = relationship(
        remote_side=[id], back_populates="replies"
    )
    replies: Mapped[list["ActionItemComment"]] = relationship(
        back_populates="parent"
    )
