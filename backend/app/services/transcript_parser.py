"""Deterministic transcript speaker/timestamp parsing.

Extracts speaker/timestamp segments from common transcript formats so action
items can be grounded in transcript evidence. When the transcript has no
recognizable cues, ``has_speakers``/``has_timestamps`` are False and the caller
falls back to AI inference.
"""

from __future__ import annotations

import re
from typing import Any

# WebVTT / SRT cue line: "00:14:23.000 --> 00:14:26.000"
_CUE_RE = re.compile(r"^\s*(\d{1,2}):(\d{2})(?::(\d{2}))?(?:[.,]\d+)?\s*-->")

# A line that starts with a timestamp: "[14:23]", "(14:23)", "14:23", optionally
# followed by a separator (":", "-", "—").
_TIMESTAMP_LEAD_RE = re.compile(
    r"^\s*[\[(]?\s*(\d{1,2}:\d{2}(?::\d{2})?)\s*[\])]?\s*[-—:]?\s*(.*)$"
)

# A speaker prefix: "Speaker Name: rest".
_SPEAKER_RE = re.compile(r"^\s*([^:]{1,60}?)\s*:\s*(.*)$")

_IGNORED_PREFIXES = ("webvtt", "note")


def _fmt(hour: str, minute: str, second: str | None) -> str:
    return f"{hour}:{minute}:{second}" if second else f"{hour}:{minute}"


def _parse_line(line: str) -> tuple[str | None, str | None, str]:
    """Return (timestamp, speaker, text) for a single content line."""
    timestamp: str | None = None
    match = _TIMESTAMP_LEAD_RE.match(line)
    if match:
        timestamp = match.group(1)
        line = match.group(2).strip()

    speaker: str | None = None
    sp = _SPEAKER_RE.match(line)
    if sp and not re.match(r"^\d", sp.group(1).strip()):
        speaker = sp.group(1).strip()
        text = sp.group(2).strip()
    else:
        text = line
    return timestamp, speaker, text


def parse_segments(raw: str) -> dict[str, Any]:
    """Split a transcript into ``{speaker, timestamp, text}`` segments.

    Returns ``{"segments": [...], "has_speakers": bool, "has_timestamps": bool}``.
    """
    segments: list[dict[str, str | None]] = []
    current_ts: str | None = None

    for raw_line in (raw or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.lower().startswith(_IGNORED_PREFIXES):
            continue

        cue = _CUE_RE.match(line)
        if cue:
            current_ts = _fmt(cue.group(1), cue.group(2), cue.group(3))
            continue

        timestamp, speaker, text = _parse_line(line)
        if timestamp:
            current_ts = timestamp
        if not text and speaker is None:
            continue

        segments.append(
            {
                "speaker": speaker,
                "timestamp": timestamp or current_ts,
                "text": text,
            }
        )

    return {
        "segments": segments,
        "has_speakers": any(s["speaker"] for s in segments),
        "has_timestamps": any(s["timestamp"] for s in segments),
    }


def find_evidence(segments: list[dict[str, str | None]], excerpt: str) -> dict[str, str | None]:
    """Find the segment that contains the given excerpt (verbatim or fuzzy).

    Returns ``{"speaker": ..., "timestamp": ...}`` or empty values when no
    segment matches.
    """
    needle = (excerpt or "").strip().lower()
    if not needle:
        return {"speaker": None, "timestamp": None}
    for seg in segments:
        text = (seg.get("text") or "").lower()
        if needle in text:
            return {"speaker": seg.get("speaker"), "timestamp": seg.get("timestamp")}
    # Fuzzy: first few significant words overlap.
    words = [w for w in re.split(r"\W+", needle) if len(w) > 3][:4]
    if words:
        for seg in segments:
            text = (seg.get("text") or "").lower()
            if all(w in text for w in words):
                return {"speaker": seg.get("speaker"), "timestamp": seg.get("timestamp")}
    return {"speaker": None, "timestamp": None}
