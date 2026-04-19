---
title: Hosted Frontend Plugin SDK
slug: hosted-frontend-plugin-sdk
summary: Reference for the separate hosted frontend workspace, its first-party plugin surfaces, plugin manifest contract, and the repo tooling that installs and tests it.
tags:
  - article-type/reference
  - area/frontend-platform
  - workflow/plugin-sdk
  - audience/developer
  - verification-date/2026-04-19
created_by_agent: fact-doc-writer
updated_by_agent: fact-doc-writer
created_at: 2026-04-19T00:00:00Z
updated_at: 2026-04-19T00:00:00Z
---

# Hosted Frontend Plugin SDK

This reference documents the separate hosted frontend workspace in `frontend/`, the plugin SDK surfaces it exposes, and the repository tooling that now installs and tests that workspace alongside `app/ui/`.

<details>
<summary>Article metadata</summary>

- **title:** Hosted Frontend Plugin SDK
- **slug:** hosted-frontend-plugin-sdk
- **summary:** Reference for the separate hosted frontend workspace, its first-party plugin surfaces, plugin manifest contract, and the repo tooling that installs and tests it.
- **tags:** article-type/reference, area/frontend-platform, workflow/plugin-sdk, audience/developer
- **created_at:** 2026-04-19T00:00:00Z
- **updated_at:** 2026-04-19T00:00:00Z

</details>

## Scope

This article covers the first-party hosted frontend workspace in `frontend/`, the seven first-party plugins that ship real feature screens, the plugin manifest and host-runtime contract, and the repo scripts that bootstrap or validate that workspace.

Out of scope: deployment-specific static hosting setup.

## Prerequisites

- A local checkout of this repository with the `frontend/` workspace present.
- Node.js and npm available in `PATH`.
- Backend environment access when you want to exercise the hosted shell against real platform endpoints.

## Reference

### Platform endpoints consumed by the hosted shell

- Token-based frontend auth through `POST /api/v1/platform/auth/tokens`, `POST /api/v1/platform/auth/refresh`, and `POST /api/v1/platform/auth/revoke`.
- Platform bootstrap metadata through `GET /api/v1/platform/bootstrap`.
- First-party plugin catalog through `GET /api/v1/platform/plugins`.
- Iframe embed descriptors through `GET /api/v1/platform/embeds/{embed_id}`.

### First-party workspace layout

The separate frontend module lives in [`frontend/`](/Users/nikhilsathyanarayana/Documents/malcom/frontend/).

Primary areas:

- `frontend/apps/host/` — standalone host shell entry files.
- `frontend/packages/sdk/` — manifest validation helpers.
- `frontend/packages/host/` — route and capability registry helpers.
- `frontend/plugins/` — first-party plugin manifests and renderers.

The current root workspace metadata in `frontend/package.json` defines npm workspaces for `packages/*` and `plugins/*`, plus a root `npm test` command for the lightweight package-level checks.

### First-party plugins and hosted routes

Seven plugins ship real feature screens. The host runtime resolves each registered path to its owning plugin's renderer.

| Plugin | Capability key | Native routes | Iframe routes |
|---|---|---|---|
| Dashboard | `dashboard` | `/dashboard`, `/dashboard/activity` | — |
| APIs | `apis` | `/apis`, `/apis/inbound`, `/apis/outbound`, `/apis/webhooks` | — |
| Automations | `automations` | `/automations`, `/automations/runs`, `/automations/library` | `/automations/builder` (embed: `workflow-builder`) |
| Tools | `tools` | `/tools`, `/tools/runtimes` | — |
| Scripts | `scripts` | `/scripts`, `/scripts/executions` | — |
| Settings | `settings` | `/settings`, `/settings/connectors`, `/settings/storage` | — |
| Docs | `docs` | `/docs`, `/docs/articles` | — |

The automations plugin distinguishes the native automation overview from the workflow builder by exposing them as separate route entries with different `mountMode` values. The builder route uses `mountMode: "iframe"` with `embedId: "workflow-builder"`, while all other automations routes use `mountMode: "native"`.

### Repo tooling hooks during migration

The hosted frontend workspace is part of the repo bootstrap and test flow now:

- `app/scripts/dev.py` installs `frontend/` dependencies during `./malcom` startup.
- `app/scripts/dev.py` runs a hosted frontend root build only when `frontend/package.json` defines a root `build` script.
- `app/scripts/test-precommit.sh` runs `npm install` and `npm test` in `frontend/` after the real-system backend gate and the legacy `app/ui` checks.
- `app/scripts/test-full.sh` reruns those hosted frontend workspace checks before the full `app/ui` Playwright suite.

Current local commands:

```bash
npm --prefix frontend install
npm --prefix frontend test
```

### Plugin manifest contract

Plugins must define:

- `id`
- `displayName`
- `description`
- `capabilityKey`
- `nav`
- `routes`

Route entries support:

- `path`
- `mountMode`
  Supported values: `native`, `iframe`
- `embedId` when `mountMode` is `iframe`

### Host responsibilities

The host shell owns:

- authentication bootstrap
- plugin registration
- navigation rendering
- capability gating
- iframe embed launch for isolated modules

### Iframe embed contract

The iframe embed contract is reserved for isolated surfaces that are not yet native-hosted. The workflow builder is the current embed surface.

Embed descriptor responses include:

| Field | Description |
|---|---|
| `id` | Embed identifier (`workflow-builder`) |
| `title` | Human-readable surface name |
| `src` | URL of the legacy backend page loaded inside the iframe |
| `builder_route` | Legacy backend page loaded inside the iframe (`/automations/builder.html`) |
| `mount_mode` | Always `iframe` |
| `origin_policy` | `cross-origin-token` — token is passed through the postMessage handshake |
| `handshake_channel` | postMessage channel name used for host↔iframe handshake |
| `capabilities` | Capability keys granted to the embed |
| `lifecycle.session_binding` | `platform-session` — the embed shares the active hosted session |
| `lifecycle.refreshes_session` | `true` — embed activity can trigger token rotation |
| `lifecycle.lifecycle_events` | `mount`, `ready`, `resize`, `teardown` |
| `lifecycle.compatibility_mode` | `legacy-backend-ui` — signals the embed is backed by the legacy builder page |

**Handshake sequence:**

1. Host shell navigates the iframe to the `src` URL.
2. After mount, the host app posts `{ type: "malcom_embed_handshake", channel: "<handshake_channel>" }` to the iframe.
3. The legacy builder page (`app/ui/automations/builder.html`) signals readiness back via `postMessage`.

Current workflow-builder behavior:

- source: legacy backend UI
- contract owner: `/api/v1/platform/embeds/workflow-builder`
- intent: preserve existing builder behavior while the hosted frontend platform grows native surfaces

### Required backend environment

- `MALCOM_FRONTEND_BOOTSTRAP_TOKEN`
  Required to issue hosted frontend session tokens.
- `MALCOM_FRONTEND_ACCESS_TOKEN_TTL_MINUTES`
  Optional access token TTL in minutes (default: 30).
- `MALCOM_FRONTEND_REFRESH_TOKEN_TTL_DAYS`
  Optional refresh token TTL in days (default: 7).
- `MALCOM_FRONTEND_HOST_URL`
  Optional canonical frontend host URL returned in bootstrap metadata.
- `MALCOM_FRONTEND_ALLOWED_ORIGINS`
  Optional comma-separated CORS allowlist for hosted frontend origins.

### Hosted session lifecycle

Sessions are **refreshable** with a **rolling rotation** strategy. Every `POST /api/v1/platform/auth/tokens` response includes `auth.session_lifecycle`:

- `session_mode`: `"refreshable"`
- `rotation_strategy`: `"rolling"`
- `access_token_ttl_minutes`: active TTL (defaults to 15 minutes unless overridden)
- `refresh_token_ttl_days`: active TTL
- `bootstrap_token_required`: always `true`

Rotate access tokens without re-authentication via `POST /api/v1/platform/auth/refresh`. Revoke a session via `POST /api/v1/platform/auth/revoke`.

### Browser validation path

The following tests verify the hosted frontend and builder embed workflows in a real browser:

| Test file | Coverage |
|---|---|
| `app/ui/e2e/settings.spec.ts` | Hosted sign-in, hosted settings shell rendering |
| `app/ui/e2e/shell.spec.ts` | Hosted shell sign-in, workflow-builder iframe compatibility routing |
| `app/ui/e2e/coverage-route-map.json` | Hosted-frontend owned routes tracked separately from backend-served routes |
| `app/tests/test_platform_api.py` | Session lifecycle metadata, embed descriptor lifecycle/compatibility fields |
| `frontend/packages/host/src/plugin-runtime.test.mjs` | Iframe builder route metadata, session lifecycle transition fields |

Run critical browser checks: `cd app/ui && npm run test:e2e:critical`

## Expected result

Developers can identify which workspace files make up the hosted frontend platform, which platform endpoints the shell consumes, which first-party plugins own which hosted routes, the session lifecycle and token rotation contract, the full iframe builder embed descriptor and handshake sequence, and which repo scripts and browser tests install, test, and validate the `frontend/` workspace.

## Related tests

- `app/tests/test_dev_launcher.py`
- `app/tests/test_frontend_platform_structure.py`
- `frontend/packages/sdk/src/index.test.mjs`
- `frontend/packages/host/src/plugin-runtime.test.mjs`

## Sources

- Internal code evidence: `app/scripts/dev.py`.
- Internal code evidence: `app/scripts/test-precommit.sh`.
- Internal code evidence: `app/scripts/test-full.sh`.
- Internal code evidence: `app/backend/routes/platform.py`.
- Internal code evidence: `frontend/package.json`.
- Internal code evidence: `frontend/packages/sdk/src/index.mjs`.
- Internal code evidence: `frontend/packages/host/src/plugin-runtime.mjs`.
- Internal code evidence: `frontend/plugins/index.mjs`.
