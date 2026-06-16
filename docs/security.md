# Security

---

## Authentication Modes

The backend supports three authentication modes, controlled by environment variables. Only one should be active at a time.

| Mode | How to enable | Behaviour |
| --- | --- | --- |
| **Normal (production)** | Default | JWT from Entra ID (MSAL) validated on every protected request |
| **LOCAL_MODE** | `LOCAL_MODE=true` | Auth bypassed, in-memory service stubs replace all Azure services. Never use in staging or production. |
| **BYPASS_AUTH** | `BYPASS_AUTH=true` | JWT validation skipped but real Azure services still used. For integration testing only. |
| **MCP_API_KEY** | Set `MCP_API_KEY` | A static bearer token accepted on all `/mcp/*` routes, in addition to JWTs. Used by external MCP clients (Claude Desktop, Cursor). |

`LOCAL_MODE` and `BYPASS_AUTH` must never appear in staging or production configuration. They exist solely to simplify local development and CI testing.

---

## Entra ID JWT Validation

In normal mode, `AuthMiddleware` in `backend/app/api/auth.py`:

1. Reads the `Authorization: Bearer <token>` header
2. Validates the JWT signature against the Entra ID JWKS endpoint for the configured tenant
3. Checks `aud` (audience) matches `ENTRA_CLIENT_ID`
4. Extracts user claims (`sub`, `email`, `name`) and attaches them to the request

The frontend uses `@azure/msal-react` and `@azure/msal-browser` to acquire tokens via the MSAL Authorization Code + PKCE flow. Tokens are refreshed silently in the background; the `useApiFetch` hook injects the current token on every API call.

WebSocket connections pass the token as a query parameter (`?token=JWT`) since browsers do not support custom headers on WebSocket upgrades.

---

## Data Isolation

Each client has its own Cosmos DB database (`client_{id}`). A query against one client's database cannot return data from another client's database — this is enforced at the Cosmos DB resource level, not just in application logic.

The application never issues cross-database queries. All repository methods take a `client_name` parameter that resolves to the correct database before any read or write.

---

## Secrets Management

In staging and production, all secrets are stored in **Azure Key Vault** and injected into Container Apps as environment variable references at deploy time. The Container App uses a system-assigned managed identity with `Key Vault Secrets User` RBAC to read secrets at startup — no connection strings, no static credentials.

In local development, secrets are stored in `.env` (never committed). `.env.example` shows the required shape with placeholder values.

Secret categories:

| Secret | Where it lives |
| --- | --- |
| Azure OpenAI API key | Key Vault |
| Azure AI Search API key | Key Vault |
| Cosmos DB key | Key Vault |
| `GRAPH_CLIENT_SECRET` | Key Vault |
| `MCP_API_KEY` | Key Vault |
| Entra ID client ID / tenant ID | Environment variable (not secret) |

---

## Communication Scanning — Permission Model

Email scanning uses the **Outlook win32com interface**, which reads from the locally-synced Outlook data store on the user's machine. This requires:

- Microsoft Outlook installed and running on the same machine as the backend
- No new OAuth scopes
- No Microsoft 365 admin consent
- No new app registrations for baseline email scanning

The win32com path is treated as the primary scanner. The Microsoft Graph API is used as a fallback and is required for:

- Teams channel messages
- Post-meeting transcript fetch (`/communications/callRecords/...`)
- Headless or remote deployments where Outlook is not running

The Graph API path requires a delegated app registration with `Mail.Read` and `Calendars.Read` scopes (user-consented, not admin-wide).

---

## Service-to-Service Authentication

All Azure service calls from the backend use one of:

- **Managed identity** — when deployed in Container Apps, the system-assigned identity is granted RBAC roles on Cosmos DB, AI Search, and Key Vault. No connection strings.
- **API key** — used only in local development where managed identity is not available. Keys are read from `.env`, never hardcoded.

The backend never stores Azure credentials in application code or configuration files that are committed to source control.

---

## MCP Server Security

The built-in MCP server at `/mcp/sse` requires authentication on all endpoints. Clients authenticate with either:

- A valid Entra ID JWT (`Authorization: Bearer <token>`)
- The static `MCP_API_KEY` (`Authorization: Bearer <mcp-key>`)

The `MCP_API_KEY` is intended for external AI clients (Claude Desktop, Cursor) that cannot perform an interactive MSAL flow. It must be rotated manually and stored in Key Vault.

`GET /mcp/tools` and `GET /mcp/health` are public (no auth required) to support tool discovery without authentication.

---

## PII and Logging

Emails, meeting transcripts, and draft content are stored in Cosmos DB with no redaction. These containers are protected by Cosmos DB access controls and only accessible via the application's managed identity.

Application logs (Application Insights / Log Analytics) should not contain email bodies or personally identifiable information. The backend logs metadata (email IDs, folder names, attribution reasons) but does not log message content. If log verbosity is increased to `DEBUG`, content may appear in traces — use `INFO` in production.

---

## CORS

The backend allows CORS from `FRONTEND_URL` (default: `http://localhost:5173`). In production, set `FRONTEND_URL` to the Container Apps frontend FQDN. Do not use wildcard origins in production.

---

## Dependency Scanning

The CI pipeline includes a Docker image build step. Add Trivy to the CI job to scan for CVEs before push:

```yaml
- name: Scan image
  uses: aquasecurity/trivy-action@master
  with:
    image-ref: ${{ env.ACR_REGISTRY }}/backend:${{ github.sha }}
    severity: CRITICAL,HIGH
    exit-code: 1
```
