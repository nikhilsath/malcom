# Malcom

Malcom is a FastAPI and PostgreSQL automation app with a Vite-built multi-page web UI. It runs on one machine by default and also supports remote workers for selected runtime jobs and worker-bound tools.

This README describes the program as it exists in this repository today. The sections below were checked against the current code in `backend/`, `ui/`, `scripts/`, and the automated tests under `tests/` and `ui/e2e/`.

## What Ships Today

- A FastAPI backend serving `/health`, `/api/v1/**`, built UI pages, and static assets.
- A PostgreSQL-backed data model for API resources, automations, runs, scripts, tools, settings, runtime telemetry, and managed log-table metadata.
- A registry-driven UI with a mixed frontend stack:
  - React/TypeScript pages for dashboard and automations
  - a TypeScript module page for the scripts library
  - vanilla JavaScript pages for APIs, tools, and settings
- An automation system with these trigger types:
  - `manual`
  - `schedule`
  - `inbound_api`
  - `smtp_email`
- An automation builder with these step types:
  - `log`
  - `outbound_request`
  - `connector_activity`
  - `script`
  - `tool`
  - `condition`
  - `llm_chat`
- API resource management for:
  - inbound APIs
  - outgoing scheduled APIs
  - outgoing continuous APIs
  - webhooks
- A script library for saved Python and JavaScript scripts, including validation on save.
- A managed tool catalog with four seeded tools:
  - `coqui-tts`
  - `llm-deepl`
  - `smtp`
  - `image-magic`
- Connector support with seeded provider presets for:
  - Google
  - GitHub
  - Notion
  - Trello
- A backend connector-activity catalog currently exists for:
  - Google Gmail, Drive, Calendar, and Sheets
  - GitHub repository and issue workflows
- A backend HTTP preset catalog currently exists for Google:
  - Gmail
  - Drive
  - Sheets
- Runtime and dashboard endpoints for:
  - scheduler status
  - queue state
  - registered workers
  - runtime trigger history
  - dashboard summary, logs, and resource history
  - live resource-profile metrics

## UI Surface

The current served UI surface comes from `ui/page-registry.json`.

### Canonical served pages

- Dashboard: `/dashboard/home.html`
- Automations: `/automations/overview.html`, `/automations/library.html`, `/automations/builder.html`, `/automations/data.html`
- APIs: `/apis/registry.html`, `/apis/incoming.html`, `/apis/outgoing.html`, `/apis/webhooks.html`
- Tools: `/tools/catalog.html`, `/tools/coqui-tts.html`, `/tools/llm-deepl.html`, `/tools/smtp.html`, `/tools/image-magic.html`
- Scripts: `/scripts/library.html`
- Settings: `/settings/workspace.html`, `/settings/logging.html`, `/settings/notifications.html`, `/settings/access.html`, `/settings/connectors.html`, `/settings/data.html`

### Redirect-only UI routes

- `/dashboard/devices.html` -> `/dashboard/home.html#/devices`
- `/dashboard/logs.html` -> `/dashboard/home.html#/logs`
- `/dashboard/queue.html` -> `/dashboard/home.html#/queue`
- `/apis/automation.html` -> `/automations/library.html`
- `/scripts.html` -> `/scripts/library.html`

Legacy aliases such as `/`, `/dashboard`, `/automations`, `/apis`, `/tools`, and `/scripts` are also defined in the page registry and redirect to their canonical pages.

## Architecture

### Backend

- App factory: `backend/main.py`
- API router aggregation: `backend/routes/api.py`
- UI route registration: `backend/routes/ui.py`
- UI route source of truth: `backend/page_registry.py` + `ui/page-registry.json`
- Database schema source of truth: `backend/database.py`
- Seed tool catalog and manifest generation: `backend/tool_registry.py`

The backend mounts these static paths:

- `/assets` from `ui/dist/assets`
- `/media` from `media`
- `/scripts` from `ui/scripts`
- `/styles` from `ui/styles`
- `/modals` from `ui/modals`

FastAPI docs are exposed at:

- `/api/docs`
- `/api/redoc`
- `/api/openapi.json`

### Frontend

- Vite input generation comes from `ui/page-registry.ts`
- Build config lives in `ui/vite.config.ts`
- Shared shell navigation lives in `ui/scripts/shell-config.js` and `ui/scripts/navigation.js`

Current frontend split:

- `ui/src/dashboard/**`: React dashboard app
- `ui/src/automation/**`: React automation pages
- `ui/src/scripts-library/**`: TypeScript scripts-library page
- `ui/scripts/apis/**`: vanilla APIs pages
- `ui/scripts/tools/**`: vanilla tool pages
- `ui/scripts/settings/**`: vanilla settings pages

### Runtime Model

Malcom uses both persisted state and in-memory runtime state.

Persisted state lives in PostgreSQL and includes automation definitions, run history, API resources, scripts, settings, tool metadata, and resource snapshots.

In-memory runtime state lives in `backend/runtime.py` and includes:

- the trigger job queue
- worker registration state
- queue pause state
- recent trigger history

Worker claims expire after a lease window and are re-queued automatically if they are not completed in time.

### Settings And Connectors

Settings are stored in the `settings` table as JSON sections.

Current default settings sections are:

- `general`
- `logging`
- `notifications`
- `data`
- `automation`
- `connectors`

Connector instance records are currently stored inside the `connectors` settings JSON section at `settings.value_json`, not in a standalone `connectors` table.

Seeded connector provider metadata is stored in the relational `integration_presets` table.

The workflow builder connector-option path in code is:

1. `settings.connectors.records`
2. `backend/services/workflow_builder.py`
3. `GET /api/v1/automations/workflow-connectors`
4. `ui/src/automation/app.tsx`

## Database Schema

`backend/database.py` is the schema source of truth.

### API registry tables

- `inbound_apis`
- `inbound_api_events`
- `outgoing_scheduled_apis`
- `outgoing_continuous_apis`
- `webhook_apis`
- `webhook_api_events`
- `outgoing_delivery_history`

### Runtime telemetry

- `runtime_resource_snapshots`

### Workspace state

- `tools`
- `settings`
- `integration_presets`

### Automation runtime

- `automations`
- `automation_steps`
- `automation_runs`
- `automation_run_steps`

### Script library

- `scripts`

### Managed log-table schema

- `log_db_tables`
- `log_db_columns`

### Dynamic tables

Managed log steps can create runtime `log_data_*` tables. Those tables are not part of the fixed checked-in schema; they are derived from `log_db_tables` and `log_db_columns`.

## Tool And Connector Capabilities

### Seeded tools

- `coqui-tts`: text-to-speech using a local Coqui TTS command
- `llm-deepl`: local LLM chat against configurable OpenAI-compatible endpoints, including streaming chat
- `smtp`: SMTP listener and relay/test-send support
- `image-magic`: ImageMagick-based file conversion, optionally delegated to a worker

### Connector flows

The backend currently supports:

- connector credential test
- connector revoke
- OAuth start/callback/refresh for Google
- settings-backed connector storage with masked/sanitized responses
- provider-aware connector activity catalog
- provider-aware HTTP preset catalog

Google OAuth can use connector-supplied credentials or these environment fallbacks:

- `MALCOM_GOOGLE_OAUTH_CLIENT_ID`
- `MALCOM_GOOGLE_OAUTH_CLIENT_SECRET`

Connector secrets are protected with a derived key that can be overridden with `MALCOM_CONNECTOR_SECRET`.

Remote worker RPC calls use `X-Malcom-Cluster-Secret`, backed by `MALCOM_CLUSTER_SECRET` when set.

## Quick Start

### Prerequisites

- Python 3
- Node.js and npm
- PostgreSQL reachable from the app

PostgreSQL is required. The backend rejects non-PostgreSQL database URLs.

### Set the database URL

```bash
export MALCOM_DATABASE_URL="postgresql://postgres:postgres@127.0.0.1:5432/malcom"
```

If unset, Malcom defaults to:

```bash
postgresql://postgres:postgres@127.0.0.1:5432/malcom
```

### Start the app

```bash
./malcom
```

`./malcom` is a thin launcher for `scripts/dev.py`. That launcher:

- creates `./.venv` if needed
- re-enters the script inside `./.venv`
- installs backend dependencies from `requirements.txt`
- installs UI dependencies with `npm ci`
- runs a Vite build when its tracked UI inputs change
- checks that PostgreSQL is responsive
- tries to start a Homebrew PostgreSQL service when PostgreSQL is down and `brew` is available
- aborts if port `8000` is already in use
- starts Uvicorn on `127.0.0.1:8000` with `--reload`

Open the app at:

- UI and API: `http://127.0.0.1:8000`
- FastAPI docs: `http://127.0.0.1:8000/api/docs`

### Startup caveat

Even if `MALCOM_DATABASE_URL` points somewhere else, the launcher still probes `127.0.0.1:5432` when deciding whether PostgreSQL is already running.

## Testing

The repo uses a two-tier test flow.

### Fast iteration

```bash
./scripts/test-precommit.sh
```

This runs:

- test-database preflight via `scripts/require_test_database.py`
- backend pytest excluding smoke tests
- UI page-entry wiring checks
- `npm test` in `ui/`
- `npm run build` in `ui/`

### Full gate

```bash
./scripts/test-full.sh
```

This runs:

- everything from `test-precommit.sh`
- smoke coverage in `tests/test_api_smoke_matrix.py`
- external probe checks in `scripts/test-external-probes.py`
- Playwright end-to-end tests with `npm run test:e2e`

### Playwright details

- Config: `ui/playwright.config.ts`
- Server launcher: `scripts/run_playwright_server.sh`
- Default server port: `4173`
- If `4173` is busy and `PLAYWRIGHT_PORT` is not preset, Playwright searches for the next free port.
- The Playwright server resets the test database before launching Uvicorn.

Test database resolution order:

1. `MALCOM_TEST_DATABASE_URL`
2. `MALCOM_DATABASE_URL`
3. `postgresql://postgres:postgres@127.0.0.1:5432/malcom_test`

Install browser binaries once with:

```bash
cd ui && npm run test:e2e:install
```

## Repository Map

### Backend

- `backend/main.py`: app factory and mounts
- `backend/routes/`: API route modules
- `backend/services/`: feature logic and runtime helpers
- `backend/runtime.py`: in-memory queue and worker registry
- `backend/database.py`: schema initialization and additive evolution
- `backend/tool_registry.py`: tool seed catalog and manifest support

### Frontend

- `ui/page-registry.json`: served and redirect UI route definitions
- `ui/page-registry.ts`: Vite input generation from the registry
- `ui/src/`: React and TypeScript UI features
- `ui/scripts/`: vanilla page controllers and shared shell logic
- `ui/styles/`: shared and page styles
- `ui/modals/`: modal partials used by vanilla pages

### Tooling And Tests

- `scripts/dev.py`: local launcher
- `scripts/test-precommit.sh`: fast test gate
- `scripts/test-full.sh`: full test gate
- `tests/`: backend and API tests
- `tests/api_smoke_registry/`: smoke scenarios for internal API coverage
- `ui/e2e/`: Playwright workflow coverage

## Troubleshooting

### Built UI is missing

The backend expects built assets in `ui/dist`. If `ui/dist/dashboard/home.html` or `ui/dist/assets` is missing, UI routes will fail until you build the frontend or start the app through `./malcom`.

### Port conflicts

Common ports used by the repo:

- `5432`: PostgreSQL
- `8000`: local app server
- `4173`: Playwright app server default
- `2525`: default SMTP tool port

### Logs

Application logs are written under `backend/data/logs/`. The dashboard logs endpoint reads and normalizes the runtime log file from there.

## Contributing

1. Read `AGENTS.md` before implementation work.
2. Keep source-of-truth files authoritative:
   - `backend/database.py` for schema
   - `ui/page-registry.json` for UI routes
   - `backend/tool_registry.py` for seeded tool metadata
3. Add or update automated tests when behavior changes.
4. Use `./scripts/test-precommit.sh` during iteration.
5. Use `./scripts/test-full.sh` when validating user-visible workflow changes or shared test/build infrastructure.
