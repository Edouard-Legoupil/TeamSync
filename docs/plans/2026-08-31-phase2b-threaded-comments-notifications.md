# Phase 2b — Threaded comments + in-app notifications

Date: 2026-08-31
Status: Approved & implemented

## Scope

Completes Phase 2: threaded discussion on action items and @mention
notifications.

## Decisions

- Comments thread via `parent_id` (self-referential).
- Mentions use `@Name` / `@email`, resolved against the action item's team
  members only; the actor never notifies themselves.
- Notifications are in-app only (bell); no email/push.
- Clicking a notification navigates to the containing meeting.

## Backend

- `ActionItemComment.parent_id` (nullable self-FK) + `parent`/`replies`.
- New `Notification` model (recipient, actor, kind, entity, meeting_id, text,
  read flag).
- `services/notifications.py`: `notify_mentions` parses `@token`s and resolves
  against the item's team members.
- `POST /api/action-items/{id}/comments` accepts `parent_id` and fires mention
  notifications.
- New router: `GET /api/notifications`, `GET .../unread-count`,
  `POST .../{id}/read`, `POST .../read-all`.
- Schemas: `NotificationOut`, `UnreadCountOut`, comment `parent_id`.

## Frontend

- `ActionItemComment.parent_id`, `Notification`, `UnreadCount` types.
- `ActionItemModal`: threaded **Discussion** (nested replies + Reply action)
  and a **History** section now limited to field changes.
- `TopBar`: notification bell with unread badge, dropdown, mark-all-read, and
  click-to-open-meeting.

## Verification

- Backend: 26 unit tests pass (added mention-resolution tests).
- Frontend: `tsc --noEmit` and `vite build` clean.
