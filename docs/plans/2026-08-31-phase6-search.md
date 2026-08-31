# Phase 6 — Canonical transcript search

Date: 2026-08-31
Status: Approved & implemented

## Scope

Extend search across the canonical repository: meetings/transcripts, action
items, and follow-ups, filterable by team, tag, speaker, and date (#11).

## Backend

- Rewrote `GET /api/search`: `q` is optional; new filters `team_id`, `tag`,
  `speaker`, `date_from`, `date_to`, `kind`.
- Searches meetings (title, minutes, transcript, follow-up markdown), action
  items (description, source_speaker, requester, completion notes), and
  follow-ups (title, issue, rationale).
- Unified `SearchResult` gains `kind`, `speaker`, `action_item_id`.

## Frontend

- `SearchResults` renders all three kinds (kind badge, team/date, highlighted
  snippet, "Mentioned by" line) and adds a filter bar (team/type/tag/speaker).

## Verification

- Backend: 31 unit tests pass.
- Frontend: `tsc --noEmit` and `vite build` clean.
