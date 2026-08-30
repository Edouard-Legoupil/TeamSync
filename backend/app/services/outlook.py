"""Outlook integration: .ics calendar export and Outlook Web deeplinks.

The ``.ics`` file opens directly in Outlook Calendar when downloaded, and the
Web deeplinks open Outlook on the web (OWA) pre-filled. Server-side Graph send
(Mail.Send / Calendars.ReadWrite) is the next integration step and is gated
behind ``MICROSOFT_GRAPH_ENABLED`` (see README).
"""

from __future__ import annotations

from datetime import timedelta
from urllib.parse import quote

from app.models import Meeting
from app.services.email_draft import markdown_to_text


def _format_ical_dt(dt) -> str:
    return dt.strftime("%Y%m%dT%H%M%SZ")


def _escape(text: str) -> str:
    return (
        (text or "")
        .replace("\\", "\\\\")
        .replace("\r\n", "\\n")
        .replace("\n", "\\n")
        .replace(",", "\\,")
        .replace(";", "\\;")
    )


def build_ics(meeting: Meeting, duration_minutes: int = 60) -> str:
    start = meeting.date
    end = start + timedelta(minutes=duration_minutes)
    body = markdown_to_text(meeting.minutes_markdown)

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//TeamSync//Meeting Minutes//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "BEGIN:VEVENT",
        f"UID:teamsync-{meeting.id}",
        f"DTSTAMP:{_format_ical_dt(meeting.date)}",
        f"DTSTART:{_format_ical_dt(start)}",
        f"DTEND:{_format_ical_dt(end)}",
        f"SUMMARY:{_escape(f'Meeting Minutes: {meeting.title}')}",
        f"DESCRIPTION:{_escape(body)}",
        "END:VEVENT",
        "END:VCALENDAR",
    ]
    return "\r\n".join(lines) + "\r\n"


def build_email_web_url(subject: str, body: str) -> str:
    return (
        "https://outlook.office.com/mail/deeplink/compose"
        f"?subject={quote(subject)}&body={quote(body)}"
    )


def build_calendar_web_url(meeting: Meeting, subject: str, body: str, duration_minutes: int = 60) -> str:
    start = meeting.date
    end = start + timedelta(minutes=duration_minutes)

    def iso(dt) -> str:
        return dt.strftime("%Y-%m-%dT%H:%M:%S")

    return (
        "https://outlook.office.com/calendar/deeplink/compose"
        f"?subject={quote(subject)}&body={quote(body)}"
        f"&startdt={quote(iso(start))}&enddt={quote(iso(end))}"
    )
