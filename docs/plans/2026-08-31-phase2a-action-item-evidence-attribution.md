# Phase 2a — Action-item evidence, speaker attribution, completion narrative

Date: 2026-08-31
Status: Approved & implemented

## Scope

Second phase slice of the roadmap: transcript evidence + traceability (#4),
speaker-to-action attribution (#7), and completion notes (#5).

## Decisions

- Speaker attribution per the approved rule: deterministically parse the
  transcript for speaker/timestamp cues; fall back to AI inference; record the
  method and a single confidence (reliability) score.
- Evidence/requester/participants are display-only in this slice.
- Threaded comment replies + notifications deferred to Phase 2b.

## Backend

- `ActionItem` gains: `source_excerpt`, `source_speaker`, `source_timestamp`,
  `confidence`, `attribution_method`, `requester`, `related_participants`,
  `completion_notes`, `completion_links`, `completion_follow_up`.
- New `services/transcript_parser.py`: `parse_segments` (WebVTT/SRT, bracketed
  and bare speaker cues) + `find_evidence` (verbatim/fuzzy excerpt match).
- AI prompt + `process_transcript` return `action_item_details` (excerpt,
  speaker, timestamp, requester, related_participants, confidence).
- `process_meeting` reconciles transcript vs AI evidence and populates fields.
- `ActionItemOut` exposes the new fields; `ActionItemUpdate` accepts the three
  completion fields (recorded in history as "updated").
- SQLite dev migration for the new columns.

## Frontend

- `ActionItem` type extended with the new fields.
- `ActionItemModal`: read-only **Source** block (excerpt, speaker, timestamp,
  method, confidence %, requester, interested parties) and editable
  **Completion notes** (shown when status is Done).

## Verification

- Backend: 24 unit tests pass (added transcript-parser and evidence tests).
- Frontend: `tsc --noEmit` and `vite build` clean.
