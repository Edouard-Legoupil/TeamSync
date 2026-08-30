"""Build a shareable email draft from a meeting's Markdown content."""

from __future__ import annotations

import re
from urllib.parse import quote

from app.models import Meeting


def markdown_to_text(markdown_text: str | None) -> str:
    """Best-effort Markdown -> plain text for email bodies."""
    out: list[str] = []
    for raw in (markdown_text or "").splitlines():
        line = raw.strip()
        if not line:
            out.append("")
            continue
        if line.startswith("|") and line.endswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if all(re.fullmatch(r":?-{3,}:?", c) for c in cells):
                continue
            out.append("  |  ".join(cells))
            continue
        line = re.sub(r"^#{1,6}\s*", "", line)
        line = re.sub(r"^\s*[-*+]\s+", "- ", line)
        line = re.sub(r"^\d+[.)]\s+", "", line)
        line = re.sub(r"\*\*(.+?)\*\*", r"\1", line)
        line = re.sub(r"__(.+?)__", r"\1", line)
        line = re.sub(r"\*(.+?)\*", r"\1", line)
        line = re.sub(r"`(.+?)`", r"\1", line)
        out.append(line)
    return "\n".join(out)


def build_email_draft(meeting: Meeting) -> dict[str, str]:
    subject = f"Meeting Minutes: {meeting.title} - {meeting.date.strftime('%Y-%m-%d')}"

    sections: list[str] = []
    if meeting.minutes_markdown:
        sections.append(markdown_to_text(meeting.minutes_markdown))
    if meeting.action_items_markdown:
        sections.append(
            "Action Items\n" + markdown_to_text(meeting.action_items_markdown)
        )
    if meeting.next_agenda_markdown:
        sections.append(
            "Next Agenda\n" + markdown_to_text(meeting.next_agenda_markdown)
        )

    body = "\n\n".join(sections).strip()
    mailto = f"mailto:?subject={quote(subject)}&body={quote(body)}"

    return {"subject": subject, "body": body, "mailto": mailto}
