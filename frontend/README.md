# Malcom Hosted Frontend Platform

This module is the separately hosted frontend runtime for Malcom.

It contains:

- `apps/host/`: a browser-hosted shell that authenticates against the backend platform contract
- `packages/sdk/`: shared plugin manifest validation and utility helpers
- `packages/host/`: host-shell route and capability registry helpers
- `plugins/`: first-party plugin manifests and renderers

The host app is intentionally dependency-light so it can be served from any static host during the transition away from backend-served HTML.

## First-party plugins

Seven first-party plugins ship in `frontend/plugins/`, each owning a set of native hosted routes. The automations plugin additionally exposes the workflow builder as an explicit iframe-backed route via the `workflow-builder` embed descriptor.

| Plugin | Capability key | Routes |
|---|---|---|
| Dashboard | `dashboard` | `/dashboard`, `/dashboard/activity` |
| APIs | `apis` | `/apis`, `/apis/inbound`, `/apis/outbound`, `/apis/webhooks` |
| Automations | `automations` | `/automations`, `/automations/runs`, `/automations/library` (native), `/automations/builder` (iframe) |
| Tools | `tools` | `/tools`, `/tools/runtimes` |
| Scripts | `scripts` | `/scripts`, `/scripts/executions` |
| Settings | `settings` | `/settings`, `/settings/connectors`, `/settings/storage` |
| Docs | `docs` | `/docs`, `/docs/articles` |

The host runtime resolves every registered path to its owning plugin's renderer. The workflow builder iframe route is distinct from native automations routes so each can be navigated and gated independently.

## Local use

1. Install workspace dependencies from the repo root:

   ```bash
   npm --prefix frontend install
   ```

2. Run the hosted frontend workspace tests:

   ```bash
   npm --prefix frontend test
   ```

3. Start the backend API.

   Preferred path:

   ```bash
   ./malcom
   ```

   Manual backend path:

   ```bash
   python3 -m venv .venv
   ./.venv/bin/pip install -r app/requirements.txt
   npm --prefix app/ui ci
   npm --prefix app/ui run build
   cd app
   ../.venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
   ```

4. Set `MALCOM_FRONTEND_BOOTSTRAP_TOKEN` on the backend.
5. Serve `frontend/apps/host/` from any static file server.
6. Open `index.html`, enter the backend URL and bootstrap token, and sign in.

## Tooling notes

- The repo test scripts (`app/scripts/test-precommit.sh` and `app/scripts/test-full.sh`) install and test this workspace automatically.
- The workspace root currently exposes `npm test`. Repo tooling runs `npm run build` only if a root `build` script is added later.

The workflow builder currently runs through the new platform as an iframe-backed compatibility surface against the legacy builder page.

## Session lifecycle

Hosted frontend sessions are **refreshable** with a **rolling rotation** strategy:

- Issue a session via `POST /api/v1/platform/auth/tokens` using the `MALCOM_FRONTEND_BOOTSTRAP_TOKEN`.
- Access tokens expire per `MALCOM_FRONTEND_ACCESS_TOKEN_TTL_MINUTES` (default 15 minutes). Refresh tokens expire per `MALCOM_FRONTEND_REFRESH_TOKEN_TTL_DAYS` (default 7 days).
- Rotate access tokens via `POST /api/v1/platform/auth/refresh` without re-authentication.
- Revoke sessions via `POST /api/v1/platform/auth/revoke`.
- Session metadata always includes `session_lifecycle.session_mode = "refreshable"` and `session_lifecycle.rotation_strategy = "rolling"`.

## Builder embed contract

The workflow builder is an iframe-backed compatibility surface. The hosted route remains `/automations/builder`, while the host shell retrieves an embed descriptor from `GET /api/v1/platform/embeds/workflow-builder` that points the iframe at the legacy backend page:

- `src`: `/automations/builder.html`
- `builder_route`: `/automations/builder.html`
- `mount_mode`: `iframe`
- `origin_policy`: `cross-origin-token`
- `handshake_channel`: postMessage channel name the host and iframe use for handshake
- `lifecycle.session_binding`: `platform-session`
- `lifecycle.refreshes_session`: `true`
- `lifecycle.lifecycle_events`: `mount`, `ready`, `resize`, `teardown`
- `lifecycle.compatibility_mode`: `legacy-backend-ui`

After the iframe loads, the host app (`apps/host/main.js`) posts a `malcom_embed_handshake` message. The legacy builder page (`app/ui/automations/builder.html`) signals readiness back via `postMessage`.

## Browser validation

Browser coverage for the hosted frontend path:

- `app/ui/e2e/settings.spec.ts` — hosted sign-in and settings shell
- `app/ui/e2e/shell.spec.ts` — hosted shell sign-in and builder iframe compatibility routing
- `app/ui/e2e/coverage-route-map.json` — hosted-frontend owned routes tracked separately from backend-served routes

Run: `cd app/ui && npm run test:e2e:critical`
