# Action Items: Team & Series Identification, Assigned/Unassigned Split, Tracker

Date: 2026-08-31
Status: Approved

## Problem

- Users belong to one or more teams and can already switch teams, but action
  items do not carry enough context: they show neither the owning team nor the
  meeting series, so a supervisor (or a member of several teams) cannot tell at
  a glance where an item comes from.
- The team "Open Action Items" list mixes assigned and unassigned items in a
  single flat list.
- There is no dedicated per-team action-items tracker; items only surface on
  the Dashboard and "My Items".

## Goals

1. Every action item is identified by its **team** and **meeting series**
   (with a clear fallback when the meeting has no series).
2. Action-item lists clearly separate **Assigned** from **Unassigned** items in
   distinct boxes.
3. Provide a **dedicated per-team tracker** that rolls up the current team and
   its child teams.
4. Apply the same split + labels consistently on Dashboard, My Items, and the
   new tracker.

## Approach

Enrich the backend action-item payload with identification context and keep the
API returning a flat list. The frontend performs the assigned/unassigned split
and team→series grouping in a single shared component.

Rejected alternatives:
- Server-side nested/grouped responses (grouping is a view concern; more API
  surface).
- Denormalizing `team_name`/`series_name` onto `action_items` (duplication,
  stale on rename).

## Backend

- `ActionItemOut` gains `team_id`, `team_name`, `series_id`, `series_name`,
  `meeting_title` (defaults `""`/`None`).
- `action_item_out()` populates those from `item.meeting → team/series`.
- Every route returning action items eager-loads
  `ActionItem.meeting → Meeting.team` and `Meeting.series` (shared loader).
- New endpoint `GET /api/teams/{team_id}/action-items` → `list[ActionItemOut]`
  scoped to `team_id` + descendants (`get_team_descendant_ids`), open,
  non-duplicate items, ordered by due date then priority.

## Frontend

- Types: extend `ActionItem` with the identification fields; add `series_name`
  to `ActionItemWithContext`.
- New shared component `ActionItemsList` (props: `items`, `onToggleDone`,
  `onOpen?`, `groupByTeam?`):
  - renders an **Assigned** box and an **Unassigned** box, each with a count;
  - groups within each box by meeting series (and by team first when
    `groupByTeam`), with a "No series" bucket;
  - item row shows checkbox, description, assignee, due date, overdue/due-soon
    badges, priority, and a `team · series · meeting` metadata line.
- New page `TeamActionItems` at `/items` (nav label "Action Items") using the
  new rollup endpoint, `groupByTeam=true`.
- Dashboard "Open Action Items" card uses the shared component,
  `groupByTeam=false`.
- My Items uses the shared component, `groupByTeam=true`.
- TopBar: add the "Action Items" nav link; add the subtitle
  "Verba volant, scripta manent" under the app name.

## Out of scope

- Multi-team switching already works; joining a second team remains
  admin-only (`/teams/{id}/join` unchanged).

## Testing

- Backend unit tests: assert `action_item_out` populates team/series/meeting
  identification (assigned and unassigned).
- Frontend: `tsc --noEmit` and `vite build`.
