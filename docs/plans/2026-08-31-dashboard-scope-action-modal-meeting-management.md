# Dashboard scope, action-item modal, meeting management, and team hierarchy

Date: 2026-08-31
Status: Approved

## Goals

1. Global "All teams" scope in the top-bar switcher (one team or all my teams
   together) for the Dashboard, Meetings page, and action-items tracker.
2. Dashboard "Recent Meetings" shows team + series badges instead of status.
3. Clicking an action item opens an edit modal; field changes are recorded and
   shown as light history, and users can add comments.
4. Meeting page: delete a meeting, or change its team / series / date.
5. Upload detects the meeting date (AI) and records it; editable afterwards.
6. Remove the "Markdown" button from the meeting page.
7. Meeting page gains a "Transcript" tab with the transcript text and a
   downloadable `.txt` (named like the original file).
8. Admin can create a team as a child of another team.

## Decisions

- Meeting deletion is a hard delete (cascades action items), with a confirm.
- "All teams" = every team the user can access (their `/teams/mine` list).
- Transcript: text-based (option C) — store the original filename, keep
  `raw_transcript`, serve a `.txt` download. No binary storage.
- Comments live in a dedicated table; field changes are recorded in the audit
  log with structured old→new detail.

## Backend

- `Meeting`: add `source_filename` (nullable); set on upload, null on paste.
- New `ActionItemComment` model (action_item_id, author_id, body, timestamps).
- Schemas:
  - `MeetingSummary` / `MeetingListRow`: add `team_id`, `team_name`,
    `series_id`, `series_name`.
  - `MeetingDetailOut`: add `raw_transcript`, `source_filename`.
  - `MeetingUpdate`: add `team_id`, `series_id`, `date`.
  - `ActionItemUpdate`: add `description`, `priority`.
  - New `ActionItemCommentCreate`, `ActionItemCommentOut`,
    `ActionItemHistoryEntry`, `AllDashboardOut`.
- `ai_service`: prompt + parse a `meeting_date` field; `process_meeting` sets
  `meeting.date` from it (fallback to upload time).
- `helpers`: `meeting_detail_out` includes transcript/source; add
  `meeting_summary_out` and `meeting_list_row_out` to populate team/series.
- Routes:
  - `GET /api/teams/dashboard` → `AllDashboardOut` (all accessible teams).
  - `GET /api/meetings` → `list[MeetingListRow]` across accessible teams.
  - `PATCH /api/meetings/{id}` accepts team/series/date (validates access and
    that the series belongs to the team).
  - `DELETE /api/meetings/{id}`.
  - `GET /api/meetings/{id}/transcript` → `.txt` download.
  - `POST`/`GET /api/action-items/{id}/comments`.
  - `GET /api/action-items/{id}/history` → merged changes + comments.
- `database._ensure_dev_columns`: add `meetings.source_filename`.

## Frontend

- `AuthContext`: `currentTeamId` supports `'__all__'`; top-bar switcher adds
  "All teams".
- `TopBar`: "All teams" option.
- `Dashboard`: fetch team or all-teams dashboard; recent meetings show team +
  series badges.
- `AllMeetings`: fetch team or all-teams meeting list; show team + series.
- `TeamActionItems`: team or all-teams source (`/action-items/mine` for all).
- New `ActionItemModal`: edit description/assignee/due/priority/status, show
  history, add comments; opened by clicking an item in every list.
- `MeetingDetail`: add Transcript tab + download; remove Markdown button; add
  meeting-settings modal (team/series/date) and Delete button.
- `AdminPage`: parent-team selector when creating a team.

## Testing

- Backend unit tests: date parsing fallback, action-item history/comments
  serialization, meeting summary team/series population.
- Frontend: `tsc --noEmit` and `vite build`.
