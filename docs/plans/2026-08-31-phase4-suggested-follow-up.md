# Phase 4 — Suggested Follow-Up replaces Next Agenda

Date: 2026-08-31
Status: Approved & implemented

## Scope

Replace the meeting-centric "Next Agenda" with structured, AI-suggested
follow-ups (type, participants, rationale) (#3, #6).

## Model & AI

- New `MeetingFollowUp` model (follow_up_type ∈ meeting | email |
  document_sharing | one_on_one | ad_hoc; title, issue, participants JSON,
  rationale, status).
- AI returns `follow_ups` (structured) in place of `next_agenda_markdown`.
- `process_meeting` rebuilds follow-ups and renders them into
  `next_agenda_markdown` (kept for export/back-compat + carried-forward
  roll-forward).

## API

- `MeetingDetailOut.follow_ups`.
- `DashboardOut` / `AllDashboardOut`: `next_agenda_preview` replaced by
  `follow_ups` (latest meeting's).

## UI

- Meeting page: "Next Agenda" tab → "Suggested Follow-Up" (structured cards);
  agenda-markdown editing removed (minutes editing retained).
- Dashboard: "Next Agenda" section → "Suggested Follow-Up" list.

## Deferred

- Live AI re-generation on action-item changes; follow-up status editing.

## Verification

- Backend: 30 unit tests pass (added `TestFollowUps`).
- Frontend: `tsc --noEmit` and `vite build` clean.
