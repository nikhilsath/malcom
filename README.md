# Malcom

Malcom is a local-first automation workspace that combines a FastAPI backend, PostgreSQL persistence, a Vite-built multi-page UI, a separate hosted-frontend platform module, and an in-process runtime for automations, APIs, connectors, tools, storage, and documentation.

The current product is not just an automation builder. It is a small operator console for:

- building and running automations
- hosting inbound APIs and webhooks
- scheduling outbound API calls
- saving reusable connector credentials and provider presets
- configuring runtime-managed tools
- storing scripts, log tables, storage locations, repo checkouts, and docs articles

## What Malcom Does

Malcom currently supports these user-facing areas:

- Dashboard: runtime summary, connected devices, queue state, logs, and persisted resource telemetry
- Automations: overview, library, builder, execution history, and log-table data browsing
- APIs: inbound endpoints, scheduled outbound APIs, continuous outbound APIs, and webhook receivers
- Tools: managed configuration for SMTP, Local LLM, Coqui TTS, and Image Magic
- Scripts: reusable script library with validation metadata
- Settings: workspace, logging, notifications, access, connectors, and data/storage controls
- Docs: documentation homepage plus an editable article library backed by `data/docs`

## UI Surface

The current served routes come from [`app/ui/page-registry.json`](/Users/nikhilsathyanarayana/Documents/malcom/app/ui/page-registry.json) and [`app/backend/routes/ui.py`](/Users/nikhilsathyanarayana/Documents/malcom/app/backend/routes/ui.py).

Main page groups:

- `dashboard/*`: one React app with `home`, `devices`, `logs`, and `queue` views
- `automations/*`: React overview, library, builder, and log-data pages
- `apis/*`: vanilla pages for registry, incoming, outgoing, and webhooks
- `tools/*`: catalog plus one configuration page per managed tool
- `settings/*`: workspace, logging, notifications, access, connectors, and data
- `scripts/library.html`
- `docs/index.html` and `docs/library.html`

## Current Architecture

### Backend

- FastAPI app factory in [`app/backend/main.py`](/Users/nikhilsathyanarayana/Documents/malcom/app/backend/main.py)
- API routers aggregated in [`app/backend/routes/api.py`](/Users/nikhilsathyanarayana/Documents/malcom/app/backend/routes/api.py)
- HTML routing driven by the page registry rather than hardcoded per-page mounts
- Feature routers for runtime, automations, APIs, connectors, settings, storage, tools, scripts, docs, log tables, and workers

### Runtime

- lifespan boot handled in [`app/backend/services/automation_execution.py`](/Users/nikhilsathyanarayana/Documents/malcom/app/backend/services/automation_execution.py)
- in-process scheduler plus runtime event bus
- worker registration and trigger claiming endpoints for local or remote execution
- persisted automation runs and per-step run history
- dashboard telemetry persisted into `runtime_resource_snapshots`

### Frontend

- Vite multi-page build in `app/ui/`
- React/TypeScript used for dashboard, automations, and docs
- vanilla JavaScript used for APIs, settings, tools, and shell wiring
- shared navigation sourced from [`app/ui/scripts/shell-config.js`](/Users/nikhilsathyanarayana/Documents/malcom/app/ui/scripts/shell-config.js)
- hosted frontend platform module in [`frontend/`](/Users/nikhilsathyanarayana/Documents/malcom/frontend/) for the separate host shell, plugin SDK, host runtime helpers, and first-party plugin manifests

## Automation Model

Current trigger types exposed by the builder:

- manual
- schedule
- inbound API
- GitHub
- SMTP email

Current step types exposed by the builder:

- log
- connector activity
- outbound request
- script
- tool
- condition
- LLM chat

What is fully wired today:

- manual execution
- scheduled execution
- inbound API-triggered execution
- SMTP email-triggered execution
- connector-backed actions for Google and GitHub
- generic outbound HTTP requests
- script execution
- tool execution
- log-table writes plus file/Drive-backed write options on Log steps

## Connectors vs Tools

Malcom uses two different integration models.

Connectors are for remote services and reusable credentials. Current saved-connector providers are:

- Google
- GitHub
- Notion
- Trello
- cPanel PostgreSQL

Tools are for machine-executed capabilities. Current managed tools are defined in [`app/backend/tool_registry.py`](/Users/nikhilsathyanarayana/Documents/malcom/app/backend/tool_registry.py):

- `smtp`
- `llm-deepl` (Local LLM)
- `coqui-tts`
- `image-magic`

Current Coqui TTS product notes:

- install and removal from within the app are not implemented yet
- `coqui-tts` workflow steps can override `output_directory`; the Coqui tool page does not own that setting

Builder activity and preset coverage is narrower than connector storage coverage:

- Google and GitHub ship provider-specific connector activities
- Google and GitHub ship seeded HTTP presets
- Notion and Trello can be saved as connectors but currently rely on generic API usage instead of provider-specific builder catalogs

## Database Schema

Schema source of truth: [`app/backend/database.py`](/Users/nikhilsathyanarayana/Documents/malcom/app/backend/database.py)

Current table groups:

- API registry: `inbound_apis`, `inbound_api_events`, `outgoing_scheduled_apis`, `outgoing_continuous_apis`, `webhook_apis`, `webhook_api_events`, `outgoing_delivery_history`
- Workspace state: `tools`, `settings`, `integration_presets`, `connectors`, `connector_auth_policies`, `frontend_sessions`, `log_db_tables`, `log_db_columns`, `connector_endpoint_definitions`
- Automation runtime: `automations`, `automation_steps`, `automation_runs`, `automation_run_steps`, `runtime_resource_snapshots`
- Script library: `scripts`
- Documentation: `docs_articles`, `docs_tags`, `docs_article_tags`
- Storage: `storage_locations`, `repo_checkouts`

Important runtime ownership:

- saved connectors are canonical in `connectors`
- workspace connector credential policy is canonical in `connector_auth_policies`
- hosted frontend session tokens are canonical in `frontend_sessions`
- connector activity and HTTP preset rows are canonical in `connector_endpoint_definitions` when present
- storage destinations are canonical in `storage_locations`
- repo clones tracked by the app are canonical in `repo_checkouts`
- docs article metadata lives in the docs tables, while article bodies are written to `data/docs/*.md`

## Repository Map

- [`app/backend/`](/Users/nikhilsathyanarayana/Documents/malcom/app/backend): FastAPI app, routes, schemas, services, migrations, runtime helpers
- [`app/ui/`](/Users/nikhilsathyanarayana/Documents/malcom/app/ui): HTML entries, React apps, vanilla page controllers, styles, Playwright tests
- [`frontend/`](/Users/nikhilsathyanarayana/Documents/malcom/frontend): hosted frontend shell, plugin SDK, host runtime helpers, and first-party plugin manifests
- [`app/tests/`](/Users/nikhilsathyanarayana/Documents/malcom/app/tests): backend and integration tests plus API smoke registry
- [`app/scripts/`](/Users/nikhilsathyanarayana/Documents/malcom/app/scripts): developer utilities, policy checks, startup helpers, test runners
- [`data/`](/Users/nikhilsathyanarayana/Documents/malcom/data): backups, config, docs, logs, media, workflow output
- [`.github/tasks/`](/Users/nikhilsathyanarayana/Documents/malcom/.github/tasks): task history and active task records

## Quick Start

The preferred local startup path today is:

```bash
./malcom
```

The launcher in [`app/scripts/dev.py`](/Users/nikhilsathyanarayana/Documents/malcom/app/scripts/dev.py) currently does all of the following from the repo root:

1. Creates or reuses `.venv/`.
2. Installs backend dependencies from `app/requirements.txt`.
3. Installs legacy multi-page UI dependencies in `app/ui/`.
4. Installs hosted frontend workspace dependencies in `frontend/`.
5. Builds `app/ui/`.
6. Runs a hosted frontend root build only when `frontend/package.json` defines a `build` script.
7. Verifies PostgreSQL is reachable on `127.0.0.1:5432`.
8. Starts the FastAPI backend on `127.0.0.1:8000`.

The manual equivalent, including both frontend workspaces, is:

```bash
python3 -m venv .venv
./.venv/bin/pip install -r app/requirements.txt
npm --prefix app/ui ci
npm --prefix frontend install
npm --prefix app/ui run build
cd app
../.venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

Default database URL:

```bash
postgresql://postgres:postgres@127.0.0.1:5432/malcom
```

Notes:

- the backend import path resolves from `app/`, not the repo root
- the hosted frontend workspace currently defines `npm test` at the root; repo tooling only runs `npm run build` there when a root `build` script exists
- the hosted frontend platform uses `MALCOM_FRONTEND_BOOTSTRAP_TOKEN` to issue separate frontend session tokens

## Hosted Frontend Platform

Malcom ships a hosted frontend platform in `frontend/` that runs alongside the existing backend-served UI.

Backend platform endpoints:

- `POST /api/v1/platform/auth/tokens`
- `POST /api/v1/platform/auth/refresh`
- `POST /api/v1/platform/auth/revoke`
- `GET /api/v1/platform/bootstrap`
- `GET /api/v1/platform/plugins`
- `GET /api/v1/platform/embeds/{embed_id}`

First-party plugins and their hosted routes:

| Plugin | Capability key | Native routes | Iframe routes |
|---|---|---|---|
| Dashboard | `dashboard` | `/dashboard`, `/dashboard/activity` | — |
| APIs | `apis` | `/apis`, `/apis/inbound`, `/apis/outbound`, `/apis/webhooks` | — |
| Automations | `automations` | `/automations`, `/automations/runs`, `/automations/library` | `/automations/builder` (embed: `workflow-builder`) |
| Tools | `tools` | `/tools`, `/tools/runtimes` | — |
| Scripts | `scripts` | `/scripts`, `/scripts/executions` | — |
| Settings | `settings` | `/settings`, `/settings/connectors`, `/settings/storage` | — |
| Docs | `docs` | `/docs`, `/docs/articles` | — |

The automations plugin exposes the workflow builder as an explicit iframe-backed route distinct from native automations routes. All other first-party surfaces render as native plugin-owned screens.

Current hosted-frontend runtime behavior:

- the backend remains compatible with the existing multi-page UI during migration
- the hosted frontend shell authenticates with token-based API sessions
- `GET /api/v1/platform/bootstrap` returns product metadata, auth/session lifecycle metadata, plugin manifests, and capability flags for the host shell
- the host runtime resolves routes to plugin-owned renderers via the plugin registry
- capability gating controls route visibility per plugin `capabilityKey`
- repo tooling treats `frontend/` as a first-class workspace alongside `app/ui/` for dependency install and test hooks

### Hosted session lifecycle

Frontend sessions are **refreshable** with a **rolling rotation** strategy. The token contract:

- access token TTL: configurable via `MALCOM_FRONTEND_ACCESS_TOKEN_TTL_MINUTES` (default 15 minutes)
- refresh token TTL: configurable via `MALCOM_FRONTEND_REFRESH_TOKEN_TTL_DAYS` (default 7 days)
- bootstrap token required to issue sessions (`MALCOM_FRONTEND_BOOTSTRAP_TOKEN`)
- session metadata always includes `session_lifecycle.session_mode = "refreshable"` and `session_lifecycle.rotation_strategy = "rolling"`

The `POST /api/v1/platform/auth/refresh` endpoint rotates access tokens without requiring re-authentication.

### Builder embed flow

The workflow builder runs as an iframe-backed compatibility surface inside the hosted shell. The hosted route remains `/automations/builder`, while `GET /api/v1/platform/embeds/workflow-builder` returns the iframe descriptor that points the shell at the legacy backend page `/automations/builder.html`:

| Field | Value |
|---|---|
| `src` | backend-served legacy builder page (`/automations/builder.html`) |
| `builder_route` | `/automations/builder.html` |
| `mount_mode` | `iframe` |
| `origin_policy` | `cross-origin-token` |
| `handshake_channel` | postMessage channel name for host↔iframe handshake |
| `lifecycle.session_binding` | `platform-session` |
| `lifecycle.refreshes_session` | `true` |
| `lifecycle.lifecycle_events` | `mount`, `ready`, `resize`, `teardown` |
| `lifecycle.compatibility_mode` | `legacy-backend-ui` |

The host shell posts a `malcom_embed_handshake` message to the iframe after mount, and the legacy builder page (`app/ui/automations/builder.html`) signals readiness back via `postMessage`.

### Browser validation path

Browser coverage for the hosted frontend path lives in:

- `app/ui/e2e/settings.spec.ts` — hosted sign-in and settings shell rendering
- `app/ui/e2e/shell.spec.ts` — hosted shell sign-in and workflow-builder iframe compatibility routing
- `app/ui/e2e/coverage-route-map.json` — hosted-frontend route ownership tracked separately from backend-served routes

Run critical browser checks: `cd app/ui && npm run test:e2e:critical`

## Testing Workflow

### Environment-first design

The test system builds the environment it needs rather than depending on a standing manual setup. This makes the workflow repeatable for new-environment preparation and CI alike.

Primary environment-building real-system command (bootstrap prerequisites → DB setup → startup lifecycle → backend suite → critical browser subset, stops on first failure):

```bash
bash app/scripts/test-system.sh
```

On failure, `app/scripts/test-system.sh` writes the machine-readable result artifact to `app/tests/test-artifacts/system-result.json`.

`test-precommit.sh` calls `test-real-failfast.sh`, which delegates to `test-system.sh` — so the environment-first approach is used automatically at every gate level.
After that first-pass real-system run, `test-precommit.sh` also runs `app/ui` checks and hosted-frontend workspace checks in `frontend/`.

### Local gates

Fast local verification (runs `test-real-failfast.sh` → `test-system.sh` internally):

```bash
./app/scripts/test-precommit.sh
```

What it adds after the real-system backend gate:

- optional backend coverage if `pytest-cov` is installed
- `node app/scripts/check-ui-page-entry-modules.mjs`
- Playwright route coverage for `app/ui` unless `SKIP_PLAYWRIGHT_ROUTE_COVERAGE=1`
- `npm test` and `npm run build` in `app/ui`
- `npm install` and `npm test` in `frontend/`
- `npm run build` in `frontend/` only when the workspace root defines a `build` script

Full completion gate:

```bash
./app/scripts/test-full.sh
```

`test-full.sh` adds full route coverage and smoke validation, then reruns the hosted frontend workspace checks before the full `app/ui` Playwright browser suite.

Supported secondary browser check:

```bash
npm --prefix app/ui run test:e2e
```

Useful focused commands:

```bash
npm --prefix app/ui run build
npm --prefix app/ui test
npm --prefix frontend install
npm --prefix frontend test
./.venv/bin/pytest -c app/pytest.ini app/tests/
```

## Documentation Ownership

Canonical documentation locations are intentionally limited to:

1. `.github/tasks/open/` and `.github/tasks/closed/` for task tracking and historical execution records
2. `AGENTS.md` plus domain `AGENTS.md` files for repository policy and routing rules
3. `README.md` for repository and product orientation
4. `data/docs/**` for product and operator documentation content

Do not introduce a parallel documentation system outside those locations.

## Troubleshooting

- If `backend.main` fails to import, you are probably launching from the repo root instead of `app/`.
- If the app cannot start, verify PostgreSQL first.
- If a browser or Playwright flow fails to boot, check which process already owns the expected port before treating startup as unresolved.
- If the UI looks stale, rebuild with `npm --prefix app/ui run build`.
- If the hosted frontend host shell changes, reinstall workspace dependencies with `npm --prefix frontend install` and rerun `npm --prefix frontend test`.

## Unfinished Features

Current follow-up work is tracked in [`.github/tasks/open/`](/Users/nikhilsathyanarayana/Documents/malcom/.github/tasks/open/).
