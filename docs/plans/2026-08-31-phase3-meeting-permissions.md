# Phase 3 — Meeting-level permissions

Date: 2026-08-31
Status: Approved & implemented

## Scope

Role-based access control at the meeting level, with team-vs-meeting overrides
(#2).

## Model & roles

- `MeetingPermission` table (meeting_id, user_id, role), unique per pair.
- `Meeting.organizer_id` is the default owner.
- Effective role (`get_meeting_role`), highest precedence wins: SUPER_ADMIN →
  owner; organizer → owner; explicit permission → its role; team manager/LEAD →
  owner; CONTRIBUTOR → contributor; else viewer.

## Enforcement

- owner: edit minutes, reprocess/delete meeting, manage permissions, full
  action-item editing.
- contributor: comment, update own assigned items.
- viewer: read-only.

Applied to meeting PATCH/DELETE/process, action-item PATCH (role-aware), and
comment POST. New endpoints `GET/POST /meetings/{id}/permissions` and
`DELETE /meetings/{id}/permissions/{user_id}` (owner only).

## Frontend

- `MeetingDetailOut.my_role`.
- Meeting page hides Edit/Settings/Delete for non-owners; Settings modal gains a
  Permissions manager (owner only).
- `ActionItemModal` gains a `readOnly` flag (viewers).

## Verification

- Backend: 29 unit tests pass (added `TestMeetingPermissions`).
- Frontend: `tsc --noEmit` and `vite build` clean.
