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

Return ONLY a JSON object with exactly these four fields:

{
  "minutes_markdown": "...",
  "action_items_markdown": "...",
  "next_agenda_markdown": "...",
  "confidence": 0.85
}

Rules:
- "minutes_markdown": structured minutes with "## Summary", "## Discussion Points",
  "## Decisions Made". Use "### " for subsections.
- "action_items_markdown": a single Markdown table with exactly these columns:
  | Task | Assignee | Due Date | Priority | Status |
  Priority is one of HIGH, MEDIUM, LOW. Status is one of OPEN, IN_PROGRESS, DONE.
- "next_agenda_markdown": a numbered Markdown list of topics for the next meeting.
- Each Markdown field must be RAW Markdown text, not a JSON string wrapping more JSON.
- "confidence" is a number from 0.0 to 1.0 reflecting how well the transcript
  supports the extracted content (lower when the transcript is noisy or sparse).
- Do not invent facts. Only use information present in the transcript.
- Use the name of the person explicitly mentioned as the assignee; otherwise
  use "Unassigned".
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
            "minutes_markdown": content,
            "action_items_markdown": "",
            "next_agenda_markdown": "",
            "confidence": 0.0,
        }

    return {
        "minutes_markdown": str(data.get("minutes_markdown", "") or ""),
        "action_items_markdown": str(data.get("action_items_markdown", "") or ""),
        "next_agenda_markdown": str(data.get("next_agenda_markdown", "") or ""),
        "confidence": _parse_confidence(data.get("confidence")),
        "model": getattr(completion, "model", settings.OPENAI_MODEL),
    }


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
