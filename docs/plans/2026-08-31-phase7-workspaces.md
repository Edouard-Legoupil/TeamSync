# Phase 7 — Workspaces (Option B)

Date: 2026-08-31
Status: Approved & implemented

## Scope

Final roadmap phase: lightweight workspaces (#12/#13) as labels over the
existing `Team` entity, plus self-serve space creation.

## Decisions

- `Team.kind` ∈ team | personal | project | donor | operation (label only).
- Any authenticated user can create a space (becomes manager + sole member).
- Model unchanged: Team → Meeting Series → Meetings → Action Items.

## Backend

- `Team.kind` column.
- `TeamMineOut` / `AdminTeamOut` / `AdminTeamCreate` / `AdminTeamUpdate`
  expose/accept `kind`.
- New `POST /api/teams` (self-serve create, manager + LEAD member).
- SQLite dev migration for `teams.kind`.

## Frontend

- `Team` / `AdminTeam` types gain `kind`.
- Top-bar team switcher gains a "New space…" inline form (name + kind).

## Verification

- Backend: 31 unit tests pass; route + column confirmed.
- Frontend: `tsc --noEmit` and `vite build` clean.
