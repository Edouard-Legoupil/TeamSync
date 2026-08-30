# TeamSync — Meeting Intelligence Hub

TeamSync turns meeting transcripts into structured, portable data and keeps
track of the commitments people make in meetings.

The core idea is simple: **Markdown is the source of truth.** Every meeting
produces three Markdown documents — structured minutes, an action-item table,
and a next-meeting agenda — which are then tracked, searched, and exported to
Word, Markdown, an Outlook calendar event, or an email draft.

## Capabilities

**Capture**
- Upload a transcript as `.txt`, `.vtt`, or `.docx`, or paste text directly.
- AI (OpenAI or Azure OpenAI) structures it into `minutes`, `action items`,
  and `next agenda`, plus a **confidence score** per meeting.
- Processing runs in the background; each meeting reports `Processing`,
  `Processed`, or `Failed` (with a retry button).

**Tracking & accountability**
- Action items with status (`OPEN` / `IN_PROGRESS` / `DONE`), assignee,
  due date, and priority.
- **Due-soon / overdue** flags across the dashboard, personal list, and tracker.
- **Cross-meeting deduplication** — a repeated action point is linked to the
  existing item instead of being double-tracked.
- A personal **My Action Items** view and an email-ready **My Digest**.

**Continuity**
- **Full-text search** across minutes, action items, and agendas.
- **Recurring meeting series** that automatically roll open action items
  forward into the next meeting's agenda.
- Editable minutes and agenda, with an **immutable audit trail** of every
  edit, upload, export, and status change.

**Organisation**
- **Organigramme**: team hierarchy via `parent_team_id`, with a child-team
  roll-up (open items, recent meetings) for supervisors.
- **Admin console**: manage users (role, active), create/rename/delete teams,
  and manage team membership and access.

**Portability & Outlook**
- Export minutes to **Word** (`.docx`), **Markdown** (`.md`), and an
  **iCalendar** (`.ics`) event that opens in Outlook Calendar.
- Generate an **email draft** (copy / mailto / `.txt`), and **Outlook Web
  deeplinks** to open a pre-filled calendar event or email in OWA.

**Access & security**
- Azure AD (Entra ID) SSO with role-based access control.
- First-login **team selection** onboarding.
- AI output is sanitized; the JWT is an httpOnly cookie; Markdown is rendered
  without raw HTML.

## User journey

### First visit — sign in

1. You open the app URL. If you are not authenticated, you are redirected to
   **Azure AD SSO** (locally, the `dev-login` endpoint stands in).
2. On the callback, TeamSync exchanges the token, **creates or updates your
   account**, issues an application JWT (httpOnly cookie), and redirects you.
3. **First time only:** you land on a **"Select your team"** screen, pick the
   team you belong to, and continue. Every later visit goes straight to your
   team dashboard.

### The happy path — process a meeting

1. You land on your **Team Dashboard**, scoped to your primary team (a
   **Team Switcher** in the top bar changes context).
2. The dominant action is **Upload Transcript**. You drop a `.docx`/`.txt`/`.vtt`
   file — or paste text — and optionally attach it to a **meeting series**.
3. A toast shows *"Processing transcript…"* and a **subtle progress bar** runs
   across the top of the screen (nothing else is blocked).
4. When complete, the page refreshes: the meeting appears in **Recent
   Meetings**, its action items appear in **Open Action Items**, and the
   **Next Agenda** preview updates.
5. You open the meeting to see **Minutes | Action Items | Next Agenda** tabs.
   Low-confidence output is flagged for review.
6. You mark action items done, reassign them, or change due dates **inline** —
   every change is written back to the source Markdown and audited.
7. You export the result: **Download Word**, **Download Markdown**,
   **Add to Calendar** (`.ics`), **Email Draft**, or **Open in Outlook**.

### Recurring meetings

Create a series (e.g. *"Weekly Coordination"*). Each new meeting in that series
automatically **carries forward** the still-open action items from the previous
meeting into its next agenda.

### Personal accountability

Open **My Items** to see every open action item across all your teams, with
overdue/due-soon flags. **My Digest** produces a copy-paste or mailto summary
you can send to your supervisor.

### Supervisors

The **Teams** page shows the **organigramme** (parent → child teams) and a
**roll-up** of open action items and recent meetings across child teams.

### Administrators

The **Admin** page (visible only to `SUPER_ADMIN`) lets you:

1. Review **all users** and change their role or active status.
2. **Create, rename, or delete teams** (name, description, manager, parent).
3. **Define team access** — add users and set `LEAD` / `CONTRIBUTOR` / `VIEWER`.

## Roles & permissions

| Role          | Scope                                                                                          |
| ------------- | ---------------------------------------------------------------------------------------------- |
| `SUPER_ADMIN` | Everything, including the Admin console and all teams.                                         |
| `SUPERVISOR`  | Teams they manage, teams they belong to, and **all descendant child teams**.                   |
| `MEMBER`      | Only teams where they have a `TeamMember` relation.                                            |

Within a team, membership roles are `LEAD`, `CONTRIBUTOR`, and `VIEWER`.
`require_team_access(user, team_id)` enforces this on every team-scoped route.


## Stack

| Layer      | Technology                                                        |
| ---------- | ----------------------------------------------------------------- |
| Backend    | Python, FastAPI, SQLAlchemy 2.0                                    |
| Database   | PostgreSQL (SQLite works out of the box for local dev)            |
| Auth       | Azure AD (Entra ID) SSO + application JWT (`python-jose`, `msal`) |
| AI         | OpenAI or Azure OpenAI                                             |
| Frontend   | React, Vite, TypeScript, Tailwind CSS                              |
| Deployment | Azure Functions v4 (`azure-functions` ASGI middleware)            |

## Repository layout

```
backend/
  main.py                  # FastAPI app; serves API + built SPA (SPA fallback)
  function_app.py          # Azure Functions v4 ASGI entrypoint
  requirements.txt
  .env.example
  app/
    config.py              # pydantic-settings (env-driven)
    database.py            # engine, session, Base (+ dev column migration)
    models/                # User, Team, TeamMember, Meeting, MeetingSeries,
                           #   ActionItem, AuditLog
    schemas.py             # Pydantic request/response models
    auth/                  # Azure AD, JWT, RBAC dependencies
    api/routes/            # auth, teams, meetings, action-items, admin,
                           #   series, search, reports, outlook, export
    services/              # ai_service, processing, word_export, email_draft,
                           #   outlook, file_parser, markdown_sync, audit, ...
  seed.py                  # local demo data
frontend/
  src/
    api/                   # axios client (JWT interceptor), types, download helper
    auth/                  # AuthContext
    components/            # UI kit + layout + modals
    pages/                 # Dashboard, MeetingDetail, AllMeetings, MyItems,
                           #   SearchResults, Teams, Admin, Onboarding
```

## Quick start (local)

The fastest path is the `start.sh` launcher, which sets up and starts both
servers:

```bash
./start.sh            # install deps if needed, then start both
./start.sh --seed     # also seed demo users/teams first
```

This runs the backend on `http://localhost:8000` and the frontend on
`http://localhost:5173` (Vite proxies `/api` to `:8000`). It enables
`ALLOW_DEV_LOGIN=true`, so you can sign in locally with:

```
http://localhost:5173/api/auth/dev-login?email=supervisor@example.org
```

### Manual setup

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # then edit DATABASE_URL etc.
uvicorn main:app --reload       # http://localhost:8000

# Frontend
cd frontend
npm install
npm run dev                     # http://localhost:5173 (proxies /api -> :8000)
```

### Serve the built SPA from the backend

```bash
cd frontend && npm run build     # outputs frontend/dist
cd ../backend
uvicorn main:app --reload        # http://localhost:8000 serves API + SPA
```

## Environment variables

| Variable                  | Required | Description                                                          |
| ------------------------- | -------- | -------------------------------------------------------------------- |
| `DATABASE_URL`            | yes      | `postgresql+psycopg2://…` (or `sqlite:///./teamsync.db` for dev)     |
| `AZURE_AD_TENANT_ID`      | yes*     | Entra ID tenant                                                      |
| `AZURE_AD_CLIENT_ID`      | yes*     | Entra ID app client id                                               |
| `AZURE_AD_CLIENT_SECRET`  | yes*     | Entra ID app client secret (confidential-client flow)                |
| `AZURE_AD_REDIRECT_URI`   | yes*     | Must match an app-registration redirect URI                          |
| `JWT_SECRET_KEY`          | yes      | Long random string (e.g. `openssl rand -hex 32`)                     |
| `OPENAI_API_KEY`          | yes*     | OpenAI key (or the key for Azure OpenAI)                             |
| `OPENAI_MODEL`            | no       | default `gpt-4o-mini`                                                |
| `AZURE_OPENAI_ENDPOINT`   | no       | Optional Azure OpenAI endpoint                                       |
| `AZURE_OPENAI_DEPLOYMENT` | no       | Optional Azure OpenAI deployment name                                |
| `FRONTEND_URL`            | no       | Origin serving the SPA (CORS + redirects)                            |
| `CORS_ORIGINS`            | no       | Comma-separated allowed origins                                      |
| `STATIC_DIR`              | no       | Path to built frontend (default `../frontend/dist`)                  |
| `ALLOW_DEV_LOGIN`         | no       | `true` enables `GET /api/auth/dev-login` — **never in production**   |
| `DEV_LOGIN_EMAIL`         | no       | Email used by the dev-login redirect (default `supervisor@example.org`) |
| `MICROSOFT_GRAPH_ENABLED` | no       | Gate for server-side Outlook/Graph send (future step)               |
| `APP_TIMEZONE`            | no       | IANA timezone for "overdue"/"due soon" (default `UTC`)              |
| `RATE_LIMIT_PER_MINUTE`   | no       | Per-IP request limit for auth/upload (default `60`; `0` disables)   |

\* Required for the corresponding feature (SSO / AI). The app still starts
without them so you can use `dev-login` for UI work.

## Azure AD SSO

1. Register an app in Azure AD with a **Web** platform.
2. Add redirect URIs:
   - Local: `http://localhost:8000/api/auth/callback`
   - Prod: `https://<function-app>.azurewebsites.net/api/auth/callback`
3. Grant the `User.Read` delegated permission.
4. Create a client secret and set `AZURE_AD_CLIENT_SECRET`.

Flow: `/api/auth/login` → Azure AD → `/api/auth/callback` → upsert user in DB →
issue app JWT as an **httpOnly cookie** → redirect to `/team` (or to the
first-login **team selection** screen when the user has no team yet).

## Background processing

`process_meeting(meeting_id)` is synchronous and idempotent. In development it
runs via FastAPI `BackgroundTasks`. For long AI runs, offload to an Azure
Storage Queue instead (see the commented queue-trigger pattern in
`function_app.py`). On failure the meeting is marked `FAILED` and the error is
recorded in `ai_metadata`, so the UI can offer a manual retry
(`POST /api/meetings/{id}/process`).

## Azure Functions deployment

```bash
cd frontend && npm install && npm run build
cd ../backend
# Ensure frontend/dist is deployed alongside the function code.
func azure functionapp publish <function-app-name>
```

The `function_app.py` entrypoint wraps the FastAPI app with
`func.AsgiFunctionApp`. `init_db()` runs at cold start (create tables, plus a
best-effort column migration for an existing SQLite dev DB) — use Alembic
migrations for real production schema management.

For the full production access model (managed identity roles, Entra SSO
permissions, Key Vault, networking, and a provisioning checklist), see
**[`deployment.md`](deployment.md)**.

## Security notes

- AI output is sanitized with `bleach` (all HTML tags stripped) before storage.
- The frontend renders Markdown with `react-markdown` + `remark-gfm`, which
  escapes raw HTML by default — no `dangerouslySetInnerHTML`.
- The JWT is delivered as an httpOnly, `SameSite=Lax` cookie (Secure when
  `FRONTEND_URL` is HTTPS).
- Uploads are limited to `.txt`/`.vtt`/`.docx` and 10 MB.
- Auth and upload endpoints are **rate-limited** per client IP.
- `dev-login` only responds on **localhost**, even if `ALLOW_DEV_LOGIN` is set.
- Every request gets an `X-Request-ID` and is logged with method/path/status/timing.
- "Overdue"/"due soon" are computed in the configured `APP_TIMEZONE`.
- Every edit, upload, export, and status change (including admin actions) is
  written to an audit log; the audit trail survives record deletion.

## Tests

A stdlib `unittest` suite covers the fragile logic — RBAC, action-item
deduplication, Markdown↔ActionItem sync, due/overdue flags, and Word/ICS/email
exports. Run it with the virtualenv (no external services needed):

```bash
cd backend
./venv/bin/python -m unittest discover -s tests -v
```

## API surface (summary)

- `GET  /api/auth/login`, `/callback`, `/me`, `/logout`, `/dev-login`
- `GET  /api/teams/mine`
- `GET  /api/teams/available` (first-login team picker)
- `POST /api/teams/{team_id}/join`
- `GET  /api/teams/{team_id}/dashboard`
- `GET  /api/teams/{team_id}/meetings`
- `GET  /api/teams/{team_id}/members`
- `GET  /api/teams/{team_id}/tree` (organigramme)
- `GET  /api/teams/{team_id}/rollup` (child-team aggregate)
- `GET  /api/teams/{team_id}/series`
- `POST /api/series`
- `POST /api/meetings/upload` (multipart: `team_id`, `file`, optional `title`, `series_id`)
- `POST /api/meetings/import` (pasted text / JSON)
- `POST /api/meetings/{id}/process`
- `GET  /api/meetings/{id}`
- `PATCH /api/meetings/{id}` (edit title/minutes/agenda — audited)
- `GET  /api/meetings/{id}/action-items`
- `GET  /api/meetings/{id}/audit`
- `GET  /api/search?q=…` (full-text across minutes/actions/agenda)
- `PATCH /api/action-items/{id}` (status / assignee / due date — syncs Markdown)
- `GET  /api/action-items/team/{team_id}`
- `GET  /api/action-items/mine` (across all your teams)
- `GET  /api/reports/my-digest` (personal open-item digest + mailto)
- `GET  /api/meetings/{id}/export/word`
- `GET  /api/meetings/{id}/export/markdown`
- `GET  /api/meetings/{id}/export/ics` (Outlook calendar event)
- `GET  /api/meetings/{id}/outlook` (Outlook Web deeplinks)
- `POST /api/meetings/{id}/email-draft`

### Admin (SUPER_ADMIN only)

- `GET/PATCH /api/admin/users/{id}`
- `GET/POST /api/admin/teams`, `PATCH/DELETE /api/admin/teams/{id}`
- `GET/POST /api/admin/teams/{id}/members`, `PATCH/DELETE /api/admin/teams/{id}/members/{user_id}`

## Outlook integration

- **`.ics` export** — downloads an iCalendar event that opens in Outlook
  Calendar.
- **Outlook Web deeplinks** — open a pre-filled calendar event or email in
  Outlook on the web (OWA).

Server-side sending/creating via Microsoft Graph (send email, create calendar
event on the user's behalf) requires an app registration with `Mail.Send` and
`Calendars.ReadWrite` plus admin consent. It is gated behind
`MICROSOFT_GRAPH_ENABLED` and documented here as the next integration step.
