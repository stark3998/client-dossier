# Communication Intelligence

---

## Overview

The communications feature continuously reads your Outlook mailbox and calendar, attributes emails and meetings to clients based on configurable rules, stores them in Cosmos DB, and optionally generates AI draft replies. All of this happens in the background without any manual action.

---

## How Email Scanning Works

### Reading from Outlook

The scanner uses the **Outlook win32com COM interface** — the same API used by Outlook macros and add-ins — to read the locally-synced Outlook data store. This requires Outlook to be installed and running on the same machine as the backend. No new OAuth scopes or admin consent are needed.

The `OutlookWin32Service` (`backend/app/services/outlook_win32.py`) wraps all COM calls in `asyncio.to_thread()` so they don't block the FastAPI event loop.

For headless or remote deployments, or when Outlook is not running, the `GraphAPIService` provides a fallback via the Microsoft Graph API (`Mail.Read` scope, delegated user consent).

The `CommunicationAccess` facade (`backend/app/services/communication_access.py`) tries win32com first and falls back to Graph automatically.

### Store Resolution

Exchange mailboxes have multiple MAPI stores. On Deloitte Exchange, the primary mailbox (`Madan, Jatin`) and the Online Archive (`jatmadan@deloitte.com`) are separate stores with different DisplayNames. The scanner resolves the correct store by:

1. Iterating `ns.Accounts` and matching on `account.DisplayName` (the email address configured in Outlook)
2. Returning `account.DeliveryStore` — the authoritative pointer to the primary mailbox, not a display name guess

This avoids the Online Archive matching instead of the primary Inbox.

### Attribution Logic

For each email, the scanner tests three rules in priority order:

| Priority | Rule | Example |
| --- | --- | --- |
| 1 | **Domain match** | Sender or any recipient contains `@navyfederal.org` |
| 2 | **Contact match** | Sender or recipient exactly matches `john.smith@navyfederal.org` |
| 3 | **Keyword match** | Subject or body contains `"Project Horizon"` |

The first rule that matches determines the attribution reason. All three are stored on the email record so you can audit which rule triggered the match.

---

## Configuration

Each client has its own scan configuration, editable in the **Config** tab of the Communications view.

```json
{
  "accounts": [
    { "display_name": "jatmadan@deloitte.com", "folders": ["Inbox", "Sent Items"] }
  ],
  "domains": ["navyfederal.org"],
  "contacts": ["jane.smith@navyfederal.org"],
  "keywords": ["Navy Federal", "Project Horizon"],
  "scan_sent": true,
  "auto_draft": true,
  "scan_interval_minutes": 15,
  "lookback_days": 0
}
```

| Field | Description |
| --- | --- |
| `accounts` | Which Outlook accounts and folders to scan. Use "Add Outlook account" in the UI to pick from detected accounts. |
| `domains` | Email domains that map to this client. Match is on sender and all recipients. |
| `contacts` | Specific email addresses that always attribute to this client. |
| `keywords` | Phrases to match in subject and body. Case-insensitive. |
| `scan_sent` | Whether to include the Sent Items folder in addition to explicitly listed folders. |
| `auto_draft` | Generate GPT-4o draft replies for inbound emails from client contacts. |
| `scan_interval_minutes` | How frequently the background scanner runs. Minimum 5. |
| `lookback_days` | How far back to scan. `0` = all email history. Any positive value limits to that many days. |

### TagInput flush behaviour

In the Config UI, text typed into a domain/keyword/contact field is not committed until you press Enter, click `+`, or move focus away from the field. The Save button flushes any uncommitted text into the payload before saving, so you don't lose a value just because you clicked Save without pressing Enter first.

---

## Background Scanner

`CommunicationScanner` (`backend/app/agent/communication_scanner.py`) runs as a FastAPI background task. It polls on a per-client schedule and:

1. Loads all clients that have a communication config
2. For each client, calls `scan_client()` which runs email and calendar scanning in sequence
3. Emits progress updates throughout via an injected `progress_cb` callback

The scanner respects `lookback_days`: if 0, it fetches from `2000-01-01`; otherwise it calculates a `since` cutoff as `now - lookback_days`.

### Live Progress

When you click **Scan now** in the UI, the backend:

1. Initialises an entry in `_scan_progress` (module-level dict keyed by `client_id`) with `running: True`
2. Injects a `_progress()` callback into `scan_client()`
3. Runs the scan as a `BackgroundTask`
4. Exposes the current progress at `GET /api/communication/{name}/scan/status`

The frontend polls that endpoint every 2 seconds and shows a progress panel at the bottom of the view:
- Current account and folder being processed
- Whether it's fetching, attributing, or saving
- Running totals: emails fetched / matched / saved as new
- Green "done" state with final counts on completion

---

## Draft Reply Generation

When `auto_draft: true`, the scanner generates a GPT-4o draft reply for every new inbound email attributed to a client. The draft:

- Draws context from the client's memory (stakeholders, recent engagements, open action items)
- Is stored with `pending_review` status — it is **never sent automatically**
- Can be edited in the Drafts tab
- Can be approved to push directly into your Outlook Drafts folder
- Accepts feedback ("too formal", "missed the urgency") that is stored in client memory to inform future drafts

### Approving and pushing to Outlook

`POST /api/communication/{name}/drafts/{id}/approve` creates a new item in your Outlook Drafts folder via win32com. The draft appears in Outlook ready for final review and sending. The platform records the push timestamp and sets status to `pushed_to_outlook`.

---

## Calendar and Teams Intelligence

### Calendar scanning

The scanner reads Outlook calendar appointments and applies the same domain/contact/keyword logic to attendee email addresses and the meeting subject. Matched meetings are stored with full attendee lists, start/end times, location, Teams join URL (if present), and your RSVP status.

### Teams transcript summarisation

For Teams meetings that have ended, the scanner:

1. Fetches the transcript via `GET /communications/callRecords/{id}/sessions/...` (Graph API)
2. Summarises to ≤300 words using GPT-4o
3. Extracts action items as a structured JSON array
4. Stores the summary and action items on the meeting record

Transcript fetch requires the `OnlineMeetings.Read` Graph scope (user-consented).

### RSVP via win32com

`POST /api/communication/{name}/meetings/{id}/respond` accepts or declines a meeting directly from the platform by calling `appointment.Respond()` via win32com.

---

## Email Threads

The Threads view groups emails into conversations by subject (after stripping Re:/Fwd: prefixes). `GET /api/communication/{name}/threads` returns thread summaries; `GET /api/communication/{name}/threads/{thread_key}` returns all emails in the thread chronologically.

A WebSocket endpoint (`/ws/communication/{name}/threads/{key}/insight`) streams a GPT-4o analysis of the full thread — summarising the conversation, identifying outstanding questions, and surfacing risks or commitments.

---

## Teams Channel Messages

For clients with a known Teams team, the platform can read channel messages via the Graph API:

- `GET /api/communication/{name}/teams` — lists joined teams
- `GET /api/communication/{name}/teams/{team_id}/channels` — lists channels
- `GET /api/communication/{name}/teams/{team_id}/channels/{ch_id}/messages` — fetches messages

Requires `ChannelMessage.Read.All` (admin-consented) or `ChannelMessage.Read.Group` depending on the Graph permission model used.
