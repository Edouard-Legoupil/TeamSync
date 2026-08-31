"""AI processing pipeline: transcript -> three Markdown strings.

The model is asked to return a single JSON object with three fields, each
containing *raw* Markdown. We parse defensively (code fences, leading prose,
etc.) so minor prompt-drift still produces usable output.
"""

from __future__ import annotations

import json
import re
from typing import Any

from openai import AzureOpenAI, OpenAI

from app.config import settings

SYSTEM_PROMPT = """You are an expert meeting assistant for a humanitarian organization.
You convert raw meeting transcripts into precise, professional Markdown.

Return ONLY a JSON object with exactly these seven fields:

{
  "meeting_date": "YYYY-MM-DD",
  "minutes_markdown": "...",
  "action_items_markdown": "...",
  "action_item_tags": [...],
  "action_item_details": [...],
  "follow_ups": [...],
  "confidence": 0.85
}

Rules:
- "meeting_date": the date the meeting took place, as ISO "YYYY-MM-DD".
  Infer it from the transcript (stated date, agenda header, timestamps, etc.).
  If no date can be determined, use null.
- "minutes_markdown": structured minutes with "## Summary", "## Discussion Points",
  "## Decisions Made". Use "### " for subsections.
- "action_items_markdown": a single Markdown table with exactly these columns:
  | Task | Assignee | Due Date | Priority | Status |
  Priority is one of HIGH, MEDIUM, LOW. Status is one of OPEN, IN_PROGRESS, DONE.
- "action_item_tags": an array with one entry per action item in the table, as
  {"task": "<exact action item description>", "tags": [{"name": "...", "type": "..."}]}.
  "type" is one of: thematic, organizational, geographic, process, behavior.
  Infer tags only from what the transcript supports. Examples: thematic (RAF,
  Fundraising, Protection, Route-Based Approach), organizational (GPS, DIPS,
  DERS, MENA), geographic (Libya, Sudan, MENA), process (Reporting, Capacity
  Building, Donor Relations). If no tag applies, use an empty list.
- "action_item_details": an array with one entry per action item in the table, as
  {"task": "<exact action item description>", "excerpt": "<verbatim quote>",
  "speaker": "<name or null>", "timestamp": "<MM:SS or null>",
  "requester": "<who raised it or null>", "related_participants": ["..."],
  "confidence": 0.8}. The excerpt must be a verbatim phrase from the transcript
  that supports the action item. Infer speaker, timestamp, requester, and
  related participants from context; use null when not determinable. The
  per-item confidence reflects how well the transcript supports the item.
- "follow_ups": an array of suggested follow-ups derived from the open items and
  discussion. Each entry is {"follow_up_type": "...", "title": "...",
  "issue": "<what prompted it or null>", "participants": ["..."],
  "rationale": "<why or null>"}. "follow_up_type" is one of: meeting, email,
  document_sharing, one_on_one, ad_hoc. Infer the lightest-weight type that
  fits (not every action needs a meeting). Return an empty array if nothing is
  needed.
- Each Markdown field must be RAW Markdown text, not a JSON string wrapping more JSON.
- "confidence" is a number from 0.0 to 1.0 reflecting how well the transcript
  supports the extracted content (lower when the transcript is noisy or sparse).
- Do not invent facts. Only use information present in the transcript.
- Use the name of the person explicitly mentioned as the assignee; otherwise
  use "Unassigned".
"""

_FOLLOW_UP_PROMPT = """You are an expert meeting assistant for a humanitarian organization.
Given the meeting context below (minutes, action items, and completion notes),
suggest the next follow-ups.

Return ONLY a JSON object with exactly one field:

{"follow_ups": [{"follow_up_type": "...", "title": "...", "issue": "...", "participants": [...], "rationale": "..."}]}

Rules:
- "follow_up_type" is one of: meeting, email, document_sharing, one_on_one, ad_hoc.
- Infer the lightest-weight type that fits; not every action needs a meeting.
- Only use information present in the context; return an empty array if nothing is needed.
"""


def _client() -> tuple[Any, str]:
    if settings.AZURE_OPENAI_ENDPOINT and settings.AZURE_OPENAI_DEPLOYMENT:
        return (
            AzureOpenAI(
                api_key=settings.OPENAI_API_KEY,
                api_version=settings.AZURE_OPENAI_API_VERSION,
                azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
                azure_deployment=settings.AZURE_OPENAI_DEPLOYMENT,
            ),
            "azure",
        )
    return OpenAI(api_key=settings.OPENAI_API_KEY), "openai"


def _extract_json(text: str) -> dict:
    """Recover a JSON object from model output that may include fences/prose."""
    text = (text or "").strip()

    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()

    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    if start != -1:
        depth = 0
        for i in range(start, len(text)):
            ch = text[i]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        parsed = json.loads(text[start : i + 1])
                        if isinstance(parsed, dict):
                            return parsed
                    except json.JSONDecodeError:
                        break

    raise ValueError("AI response did not contain a valid JSON object")


def process_transcript(transcript: str) -> dict[str, Any]:
    client, kind = _client()
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"Here is the meeting transcript:\n\n{transcript}",
        },
    ]

    kwargs: dict[str, Any] = {"temperature": 0.2}
    if kind == "azure":
        kwargs["model"] = settings.AZURE_OPENAI_DEPLOYMENT
        completion = client.chat.completions.create(messages=messages, **kwargs)
    else:
        kwargs["model"] = settings.OPENAI_MODEL
        completion = client.chat.completions.create(
            messages=messages, response_format={"type": "json_object"}, **kwargs
        )

    content = completion.choices[0].message.content or ""
    try:
        data = _extract_json(content)
    except ValueError:
        # Graceful fallback if the model drifted from JSON mode.
        data = {
            "meeting_date": None,
            "minutes_markdown": content,
            "action_items_markdown": "",
            "action_item_tags": [],
            "action_item_details": [],
            "follow_ups": [],
            "confidence": 0.0,
        }

    return {
        "meeting_date": data.get("meeting_date"),
        "minutes_markdown": str(data.get("minutes_markdown", "") or ""),
        "action_items_markdown": str(data.get("action_items_markdown", "") or ""),
        "action_item_tags": data.get("action_item_tags") or [],
        "action_item_details": data.get("action_item_details") or [],
        "follow_ups": data.get("follow_ups") or [],
        "confidence": _parse_confidence(data.get("confidence")),
        "model": getattr(completion, "model", settings.OPENAI_MODEL),
    }


def suggest_follow_ups(context: str) -> list[dict[str, Any]]:
    """Re-derive suggested follow-ups from the current meeting context."""
    client, kind = _client()
    messages = [
        {"role": "system", "content": _FOLLOW_UP_PROMPT},
        {"role": "user", "content": context},
    ]

    kwargs: dict[str, Any] = {"temperature": 0.2}
    if kind == "azure":
        kwargs["model"] = settings.AZURE_OPENAI_DEPLOYMENT
        completion = client.chat.completions.create(messages=messages, **kwargs)
    else:
        kwargs["model"] = settings.OPENAI_MODEL
        completion = client.chat.completions.create(
            messages=messages, response_format={"type": "json_object"}, **kwargs
        )

    content = completion.choices[0].message.content or ""
    try:
        data = _extract_json(content)
    except ValueError:
        data = {"follow_ups": []}
    return data.get("follow_ups") or []


# --- Action item table parsing ----------------------------------------------

_SEPARATOR_RE = re.compile(r":?-{3,}:?")

HEADER_ALIASES: dict[str, str] = {
    "task": "task",
    "action": "task",
    "action item": "task",
    "description": "task",
    "assignee": "assignee",
    "assigned to": "assignee",
    "owner": "assignee",
    "responsible": "assignee",
    "due date": "due_date",
    "due": "due_date",
    "deadline": "due_date",
    "priority": "priority",
    "status": "status",
}

VALID_PRIORITIES = {"HIGH", "MEDIUM", "LOW"}
VALID_STATUSES = {"OPEN", "IN_PROGRESS", "DONE"}


def _parse_confidence(value: object) -> float:
    try:
        conf = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0.5
    return max(0.0, min(1.0, conf))


def _canonical(header: str) -> str | None:
    h = header.lower().strip()
    for alias, canon in HEADER_ALIASES.items():
        if alias in h:
            return canon
    return None


def parse_action_items_table(markdown: str) -> list[dict[str, str]]:
    """Parse a Markdown table into a list of ``{header: value}`` rows."""
    rows: list[dict[str, str]] = []
    header: list[str] | None = None
    for raw in (markdown or "").splitlines():
        line = raw.strip()
        if not (line.startswith("|") and line.endswith("|")):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if all(_SEPARATOR_RE.fullmatch(c) for c in cells):
            continue
        if header is None:
            header = cells
            continue
        while len(cells) < len(header):
            cells.append("")
        rows.append(dict(zip(header, cells[: len(header)])))
    return rows


def parse_action_items(markdown: str) -> list[dict[str, Any]]:
    """Turn an action-items Markdown table into normalized field dicts."""
    parsed: list[dict[str, Any]] = []
    for row in parse_action_items_table(markdown):
        fields: dict[str, str] = {}
        for header, value in row.items():
            canon = _canonical(header)
            if canon and canon not in fields:
                fields[canon] = value.strip()

        description = fields.get("task", "").strip()
        if not description:
            continue

        priority = (fields.get("priority", "") or "MEDIUM").strip().upper()
        if priority not in VALID_PRIORITIES:
            priority = "MEDIUM"
        status = (fields.get("status", "") or "OPEN").strip().upper()
        if status not in VALID_STATUSES:
            status = "OPEN"

        parsed.append(
            {
                "description": description,
                "assignee": fields.get("assignee", "").strip(),
                "due_date": fields.get("due_date", "").strip(),
                "priority": priority,
                "status": status,
            }
        )
    return parsed
