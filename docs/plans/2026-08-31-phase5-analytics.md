# Phase 5 — Executive analytics dashboard + theme heatmap

Date: 2026-08-31
Status: Approved & implemented

## Scope

Cross-team executive visibility (#9) and a tag-based theme heatmap (#10).

## Backend

- New `GET /api/analytics` (across the caller's accessible teams) with optional
  filters `team_id`, `status`, `assignee_id`, `tag`.
- Returns: `open_count`, `overdue_count`, `by_team`, `by_theme` (thematic tags),
  `by_region` (geographic tags), `by_assignee`, `top_themes` (top 10), and
  `follow_up_types`.
- Reuses the Phase 1 tagging model (theme = thematic tag, region = geographic
  tag).

## Frontend

- New **Analytics** page (`/analytics`) with summary cards, filter row
  (team/status/tag), and count-bar sections (By Theme, By Region, By
  Responsible, Top Themes, Follow-ups by type).
- Nav link gated to SUPER_ADMIN / SUPERVISOR / team managers.

## Deferred

- Time-series "trend evolution" and NLP "most discussed issues" (#10).

## Verification

- Backend: 31 unit tests pass (added `TestAnalyticsHelpers`).
- Frontend: `tsc --noEmit` and `vite build` clean.
