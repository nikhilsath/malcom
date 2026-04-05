---
title: Settings Reference
slug: settings-reference
summary: Section-by-section settings reference aligned to the workspace settings screens and API payload fields.
tags:
  - article-type/reference
  - area/workspace-settings
  - workflow/settings-management
  - audience/admin
  - verification-date/2026-04-04
created_by_agent: fact-doc-writer
updated_by_agent: fact-doc-writer
created_at: 2026-04-04T20:19:33Z
updated_at: 2026-04-05T12:30:00Z
---

# Settings Reference

This reference maps workspace settings behavior to the backend routes, schema validation, and UI settings workflows implemented in this repository.

<details>
<summary>Article metadata</summary>

- **title:** Settings Reference
- **slug:** settings-reference
- **summary:** Section-by-section settings reference aligned to the workspace settings screens and API payload fields.
- **tags:** article-type/reference, area/workspace-settings, workflow/settings-management, audience/admin
- **created_at:** 2026-04-04T20:19:33Z
- **updated_at:** 2026-04-05T12:30:00Z

</details>

## Table of Contents

- [Scope](#scope)
- [Prerequisites](#prerequisites)
- [Reference](#reference)
- [Expected result](#expected-result)
- [Sources](#sources)
## Scope

This article covers:

- Settings APIs served by `/api/v1/settings` and `/api/v1/settings/data/backups*`.
- Section keys validated by settings response/update schemas.
- Connector policy and connector record surfaces returned through settings and connector APIs.
- UI actions in the settings page that call these APIs.

Out of scope: connector provider onboarding instructions and tool-specific runtime configuration procedures.

## Prerequisites

- Admin access to workspace settings pages or API endpoints.
- API access to the same workspace database state used by the UI.

## Reference

### Core settings API

- `GET /api/v1/settings` returns the normalized settings payload.
- `PATCH /api/v1/settings` writes changed section keys into the `settings` table and returns the refreshed payload.

### Validated settings sections and defaults

The settings response is normalized against these sections:

- `general`: `environment` (`live`) and `timezone` (`utc|local|ops`, default `local`).
- `logging`: `max_stored_entries` (50-5000, default 250), `max_visible_entries` (10-500, default 50), `max_detail_characters` (500-20000, default 4000), `max_file_size_mb` (1-100, default 5).
- `notifications`: `channel` (`email|pager`, default `email`) and `digest` (`realtime|hourly|daily`, default `hourly`).
- `data`: `payload_redaction` (default `true`), `export_window_utc` (`00:00|02:00|04:00`, default `02:00`), `workflow_storage_path` (default `backend/data/workflows`).
- `automation`: `default_tool_retries` (0-10, default 2).
- `security`: `session_timeout_minutes` (`30|60|120|480`, default `60`), `dual_approval_required` (default `false`), `token_rotation_days` (`30|60|90`, default `90`).

### Connectors section in settings payload

- `connectors.catalog`: provider catalog entries.
- `connectors.records[]`: saved connector instances with metadata including status and sanitized auth fields.
- `connectors.auth_policy`: `rotation_interval_days`, `reconnect_requires_approval`, and `credential_visibility`.

Connector policy updates are served through `PATCH /api/v1/connectors/auth-policy`.

### Proxy settings workflow

- The settings UI includes proxy controls for domain, HTTP/HTTPS ports, and enabled state.
- Settings PATCH handling includes a proxy sync branch that calls runtime sync for caddy proxy state when a `proxy` section is changed.
- Runtime proxy state is written to `backend/data/caddy/public_proxy_runtime.json`.

### Backup and restore endpoints

- `POST /api/v1/settings/data/backups` creates a backup and returns backup metadata.
- `GET /api/v1/settings/data/backups` lists available backups.
- `POST /api/v1/settings/data/backups/restore` starts a restore workflow for the selected backup payload.

### Settings page UI actions

- Save settings: submits current section values through `PATCH /api/v1/settings`.
- Reset defaults: submits default app settings through the same PATCH flow.
- Clear stored logs: clears browser log storage only; it does not call a backend settings route.

## Expected result

Operators can map each settings control or API field to a validated section key, an update route, and the persisted settings behavior used by the workspace runtime.

<!-- Troubleshooting removed per fact-doc-writer guidance; include operator workflows in Procedure sections where actionable steps are required. -->

## Sources

- Internal code evidence: `backend/schemas/settings.py`.
- Internal code evidence: `backend/routes/settings.py`.
- Internal code evidence: `backend/routes/connectors.py`.
- Internal code evidence: `backend/services/helpers.py`.
- Internal code evidence: `backend/services/domain_proxy.py`.
- Internal code evidence: `ui/scripts/settings.js`.
- Internal code evidence: `ui/scripts/log-store.js`.
