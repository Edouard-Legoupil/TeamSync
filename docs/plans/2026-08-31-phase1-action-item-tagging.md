# Phase 1 — Multi-dimensional Action-Item Tagging

Date: 2026-08-31
Status: Approved & implemented

## Scope

First phase of the 13-capability roadmap. Meeting-series formalization (#13) is
already implemented; this phase adds the tagging system (#8).

## Decisions

- Tags are **global** (shared across teams).
- Tag `type` ∈ thematic | organizational | geographic | process | behavior.
- AI returns tag **name + type** per action item; on ingest, tags are upserted
  by name (case-insensitive) with **first-write-wins** on `type`.
- Deferred: notifications, meeting-level permissions, speaker/evidence,
  follow-up intelligence, exec dashboard/heatmaps, workspaces (Option B).

## Backend

- `Tag` model + `action_item_tags` association table (M2M).
- `TagType` enum; `TagOut` / `TagUpsert` / `TagCreate` schemas.
- `ActionItemOut.tags`; `ActionItemUpdate.tags` (list of name+type upserts).
- `services/tagging.py`: `upsert_tag`, `parse_action_item_tags`,
  `normalize_tag_key`.
- AI prompt + `process_transcript` return `action_item_tags`.
- `process_meeting` attaches tags to built action items by normalized task text.
- `GET/POST /api/tags`; `PATCH /api/action-items/{id}` accepts `tags`.
- Eager-load tags (`selectinload`) across all action-item queries.

## Frontend

- `Tag` type + `ActionItem.tags`.
- `ActionItemsList` renders tags as type-colored pills.
- `ActionItemModal` gains a tag editor (add by name + type, remove), saved via
  the update endpoint.

## Verification

- Backend: 19 unit tests pass (added `TestTagging`).
- Frontend: `tsc --noEmit` and `vite build` clean.
