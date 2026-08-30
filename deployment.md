# TeamSync — Production Deployment & Access Requirements

This document describes the exact cloud access and configuration needed to run
TeamSync in production on Azure. It distinguishes between the **principals**
involved and states the minimum access each one requires (least privilege).

> Read this together with `README.md`. Target deployment: a Python **Azure
> Function App v4** serving the FastAPI backend and the built React SPA, an
> **Azure Database for PostgreSQL Flexible Server**, **Azure AD (Entra ID)**
> for SSO, and **OpenAI or Azure OpenAI** for transcript processing.

---

## 1. Principals involved

There are three distinct identities. Keep them separate.

| Principal | What it is | Used for |
| --- | --- | --- |
| **Function App managed identity** | The *service principal* the app runs as (system-assigned). | Accessing Postgres, Azure OpenAI, Key Vault, Storage — without stored secrets. |
| **Entra ID app registration** | The OAuth 2.0 *client* for sign-in (a separate application object). | User SSO (`User.Read`) and, optionally, Graph for Outlook send. |
| **Deployer / CI-CD identity** | A human or service principal used to publish the app. | Deploying code and wiring secrets. |

The "principal service" is the **Function App system-assigned managed identity**;
its exact requirements are in §3.

---

## 2. Entra ID app registration (SSO client)

This is **not** the same as the Function App identity. Create it under
**Microsoft Entra ID → App registrations**.

### Platform & redirect URIs

- Platform: **Web**.
- Redirect URI (must match `AZURE_AD_REDIRECT_URI` **exactly**):
  - Production: `https://<function-app>.azurewebsites.net/api/auth/callback`
  - Local dev: `http://localhost:8000/api/auth/callback`
    (or `http://localhost:5173/api/auth/callback` when using the Vite dev server)

### API permissions

| Permission (Microsoft Graph) | Type | Admin consent | Purpose |
| --- | --- | --- | --- |
| `User.Read` | Delegated | Not required | Resolve the signed-in user's identity at login. |
| `Mail.Send` *(optional)* | Delegated | Not required | Send minutes from the user's own mailbox (server-side Graph send). |
| `Calendars.ReadWrite` *(optional)* | Delegated | Not required | Create calendar events on the user's behalf. |

> The optional Graph permissions are only needed if you enable server-side
> Outlook send (`MICROSOFT_GRAPH_ENABLED=true`). The `.ics` export and Outlook
> Web deeplinks work **without** them. If the organisation restricts user
> consent, grant **admin consent** for these scopes.

### Credentials

- Create a **client secret** (or a certificate). Store it in Key Vault and
  expose it to the app as `AZURE_AD_CLIENT_SECRET`.
- Note the **Application (client) ID** (`AZURE_AD_CLIENT_ID`) and
  **Directory (tenant) ID** (`AZURE_AD_TENANT_ID`).

---

## 3. Function App managed identity — exact access

Enable **Identity → System assigned** on the Function App. Then grant the
following. Scope every role to the smallest resource possible.

### 3.1 Azure Database for PostgreSQL Flexible Server

The app needs to read/write the TeamSync schema. Two options:

**Option A — Microsoft Entra auth (recommended, no DB password).**

1. On the Flexible Server, enable **Microsoft Entra authentication** and add an
   Entra admin.
2. Add the managed identity as a database principal (run as an Entra admin in
   the `postgres` database):

   ```sql
   SELECT * FROM pgaadauth_create_principal('<function-app-name>', false, false);
   ```

3. In the **application database**, grant least privilege. The current code runs
   `create_all()` at startup, so it needs `CREATE` on the schema; after moving
   to migrations you can revoke `CREATE`:

   ```sql
   GRANT CONNECT ON DATABASE teamsync TO "<function-app-name>";
   GRANT USAGE, CREATE ON SCHEMA public TO "<function-app-name>";
   GRANT SELECT, INSERT, UPDATE, DELETE, REFERENCES, TRIGGER
     ON ALL TABLES IN SCHEMA public TO "<function-app-name>";
   GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO "<function-app-name>";
   ```

   > After introducing Alembic migrations, drop `CREATE` so the runtime
   > principal cannot alter schema.

**Option B — SQL username/password (current code path).** Put the credentials
in `DATABASE_URL` (stored in Key Vault). No Postgres RBAC role is needed, but
the managed identity then needs **Key Vault Secrets User** (§3.3) if the
password lives in Key Vault.

> **Important:** the code currently authenticates to Postgres with a connection
> string (Option B). Using Entra auth (Option A) requires adding an
> `azure-identity` token provider to the DB connection — a small code change,
> tracked as a hardening item.

### 3.2 Azure OpenAI

- If using **API key** (current code): no role is required; provide
  `OPENAI_API_KEY` via Key Vault.
- If using **managed identity**: assign **`Cognitive Services OpenAI User`** on
  the Azure OpenAI resource and use an Entra token provider in code (currently
  not implemented — also a hardening item).

### 3.3 Azure Key Vault

Assign **`Key Vault Secrets User`** on the vault (or on individual secrets via
per-secret access policies / RBAC) so the app can read its secrets. Recommended
secrets to store here:

- `JWT_SECRET_KEY`
- `AZURE_AD_CLIENT_SECRET`
- `OPENAI_API_KEY` (or Azure OpenAI key)
- `DATABASE_URL` (if using SQL auth)

Use **Key Vault references** in the Function App settings, e.g.
`@Microsoft.KeyVault(SecretUri=https://<vault>.vault.azure.net/secrets/JWT-SECRET/)`.

### 3.4 Storage Account (background processing)

Only needed if you offload AI processing to an **Azure Queue** (recommended for
long transcripts). Assign **`Storage Queue Data Contributor`** on the
`meeting-processing` queue (or the whole account if you prefer one grant).

The Function App also needs `AzureWebJobsStorage` (the Functions runtime's own
storage) — normally configured automatically at provisioning.

### 3.5 Application Insights

No RBAC role is required for standard telemetry — provide the
`APPLICATIONINSIGHTS_CONNECTION_STRING` app setting. If you publish custom
metrics, add **`Monitoring Metrics Publisher`** on the Application Insights
resource.

---

## 4. Application settings (Function App configuration)

Set these in the Function App **Configuration → Application settings**. Secrets
should be Key Vault references, not plaintext.

| Setting | Production value | Notes |
| --- | --- | --- |
| `DATABASE_URL` | `postgresql+psycopg2://…` (or Entra via code change) | SQL auth today; see §3.1 |
| `AZURE_AD_TENANT_ID` | tenant GUID | |
| `AZURE_AD_CLIENT_ID` | SSO app client ID | |
| `AZURE_AD_CLIENT_SECRET` | Key Vault reference | SSO app secret |
| `AZURE_AD_REDIRECT_URI` | `https://<function-app>.azurewebsites.net/api/auth/callback` | Must match the app registration exactly |
| `JWT_SECRET_KEY` | Key Vault reference, ≥32 random bytes | Keep it **stable**; changing it invalidates all sessions |
| `OPENAI_API_KEY` | Key Vault reference | Or use Azure OpenAI below |
| `AZURE_OPENAI_ENDPOINT` | `https://<resource>.openai.azure.com/` | Optional |
| `AZURE_OPENAI_DEPLOYMENT` | deployment name | Optional |
| `OPENAI_MODEL` | `gpt-4o-mini` (default) | |
| `FRONTEND_URL` | `https://<function-app>.azurewebsites.net` | Must be HTTPS so the auth cookie is `Secure` |
| `CORS_ORIGINS` | the prod URL | Same-origin serving usually makes CORS unnecessary |
| `STATIC_DIR` | `../frontend/dist` | Keep default; deploy the built SPA alongside |
| `ALLOW_DEV_LOGIN` | `false` | **Must be false** in production |
| `MICROSOFT_GRAPH_ENABLED` | `false` (until Graph is configured) | |
| `APP_TIMEZONE` | IANA tz, e.g. `Europe/Geneva` | Used for due/overdue |
| `RATE_LIMIT_PER_MINUTE` | e.g. `60` | |
| `FUNCTIONS_WORKER_RUNTIME` | `python` | Azure Functions |
| `FUNCTIONS_EXTENSION_VERSION` | `~4` | |
| `AzureWebJobsStorage` | connection string | Functions runtime storage |

---

## 5. Networking & security

- **Function App**: HTTPS-only, TLS 1.2+. Publicly reachable (SSO callback and
  users must reach it). Add the prod URL as an allowed redirect URI.
- **PostgreSQL**: put it on a private endpoint / VNet; allow the Function App's
  outbound subnet. Do **not** expose it publicly. Enforce `SSL` in the
  connection string (`?sslmode=require`).
- **Storage account**: restrict network access to Azure services / the Function
  App's VNet; disable public anonymous access.
- **Key Vault**: disable public access or restrict to the Function App's VNet
  and your admin identities; enable soft-delete + purge protection.
- **App registration**: scope `User.Read` only; review consent grants.

---

## 6. Database schema & migrations

The app calls `Base.metadata.create_all()` at cold start. On PostgreSQL this
means the runtime identity must hold `CREATE` on the schema (see §3.1). For a
clean least-privilege posture:

1. Generate an initial Alembic migration and run it with a **separate**
   migration principal (or your deployer identity).
2. Revoke `CREATE` from the Function App identity, leaving only DML.
3. Remove `create_all` (or keep it idempotent but harmless) once migrations own
   the schema.

---

## 7. Deployment (CI/CD) identity

The identity that publishes the app needs, at minimum:

| Scope | Role | Purpose |
| --- | --- | --- |
| Function App | `Website Contributor` (or `Contributor`) | Deploy code, set app settings |
| Storage account (deployment container) | `Storage Blob Data Contributor` | Upload the deployment package (if not using run-from-package URL) |
| Key Vault | `Key Vault Secrets Officer` **or** per-secret `set` | Write the initial secrets (best done once, manually) |

If you use Key Vault references, CI/CD does **not** need to read secret values —
it only writes references, which is safer.

---

## 8. Least-privilege summary

| Principal | Resource (scope) | Minimum access |
| --- | --- | --- |
| Function App MI | PostgreSQL | `CONNECT` + DML on app tables; `USAGE, CREATE` on schema (drop `CREATE` after migrations) |
| Function App MI | Azure OpenAI | `Cognitive Services OpenAI User` (or API key only) |
| Function App MI | Key Vault | `Key Vault Secrets User` (get/list) |
| Function App MI | Storage queue | `Storage Queue Data Contributor` |
| Function App MI | Application Insights | none (connection string); `Monitoring Metrics Publisher` for custom metrics |
| SSO app registration | Microsoft Graph | `User.Read` (delegated); optional `Mail.Send`, `Calendars.ReadWrite` |
| Deployer/CI-CD | Function App, Storage, Key Vault | `Website Contributor`, `Storage Blob Data Contributor`, secret write |

---

## 9. Provisioning checklist

1. Create the PostgreSQL Flexible Server; enable Entra auth; create the app DB.
2. Create the Azure OpenAI resource and a deployment (or use plain OpenAI).
3. Create the Key Vault; store `JWT_SECRET_KEY`, `AZURE_AD_CLIENT_SECRET`,
   `OPENAI_API_KEY`, `DATABASE_URL`.
4. Register the Entra app (§2); add redirect URIs; grant `User.Read`; create a
   client secret into Key Vault.
5. Create the Function App (Python, v4); enable **system-assigned identity**.
6. Grant the managed identity the roles in §3.
7. Set the app settings in §4 (use Key Vault references for secrets).
8. Build the frontend (`npm run build`) and publish backend + `frontend/dist`
   (`func azure functionapp publish <name>`).
9. Create the storage queue (`meeting-processing`) if using queue processing.

## 10. Pre-flight verification

- `https://<function-app>.azurewebsites.net/api/health` → `{"status":"ok"}`.
- SSO: hitting `/` redirects to Entra, callback lands back on `/team`, and the
  `teamsync_access_token` cookie is `Secure` + `HttpOnly`.
- Upload a `.txt`/`.docx`; it reaches `PROCESSED` and appears in the dashboard.
- Word, Markdown, and `.ics` exports download correctly.
- Confirm `ALLOW_DEV_LOGIN` is `false` and `/api/auth/dev-login` returns 403.
