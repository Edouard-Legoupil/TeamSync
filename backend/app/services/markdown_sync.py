"""Keep ``ActionItem`` records and the source-of-truth Markdown table in sync."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import ActionItem, Meeting, User


def build_action_item_row(db: Session, item: ActionItem) -> str:
    assignee_name = "Unassigned"
    if item.assignee_id:
        assignee = db.get(User, item.assignee_id)
        if assignee:
            assignee_name = assignee.full_name or assignee.email
    due = item.due_date.strftime("%Y-%m-%d") if item.due_date else ""
    return (
        f"| {item.description} | {assignee_name} | {due} | "
        f"{item.priority} | {item.status} |"
    )


def sync_action_item_to_markdown(db: Session, meeting: Meeting, item: ActionItem) -> None:
    """Replace the item's Markdown table row with its current DB values.

    ``source_markdown`` holds the exact row captured when the item was created,
    so we can do a precise string replacement instead of rebuilding the table.
    """
    md = meeting.action_items_markdown or ""
    new_row = build_action_item_row(db, item)
    old_row = item.source_markdown
    if old_row and old_row in md:
        md = md.replace(old_row, new_row)
    item.source_markdown = new_row
    meeting.action_items_markdown = md
