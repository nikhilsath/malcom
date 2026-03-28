# Malcom

Malcom is a self-hosted, local-first automation orchestration platform for running workflows, APIs, connectors, and runtime-managed tools on your own machine or network.

It combines a FastAPI backend, PostgreSQL persistence, and a Vite-built, registry-driven multi-page web UI with both React/TypeScript and vanilla JavaScript pages.

## Table of Contents

- [What Malcom Does](#what-malcom-does)
- [UI Surface](#ui-surface)
- [Current Architecture](#current-architecture)
- [Database Schema](#database-schema)
- [Repository Map](#repository-map)
- [Quick Start](#quick-start)
- [Testing Workflow](#testing-workflow)
- [UI and Route Wiring](#ui-and-route-wiring)
- [Connectors vs Tools](#connectors-vs-tools)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

## What Malcom Does

Malcom provides the API, UI, and runtime needed to build and operate local-first automation workflows.

It includes:

- a FastAPI API for automations, runs, inbound and outgoing APIs, webhooks, connectors, tools, scripts, settings, log tables, workers, and runtime status
- a browser UI for dashboard monitoring, automation authoring, API management, tools, scripts, connectors, and workspace settings
- an in-process scheduler, trigger queue, and worker coordination runtime for executing and tracking automation runs, including inbound API and webhook-triggered flows
- connector-backed outbound requests, reusable HTTP presets, and provider-specific connector activities
- a PostgreSQL-backed tool and settings store that also feeds generated frontend manifest data
- persisted run history and per-step execution details in PostgreSQL

Primary goals:

1. Run reliably on low-power local hardware, letting "tools" be run on any other connected machine for more intense tasks.
2. Keep workflows local-first.
3. Stay extensible for connectors and runtime-managed tools.

## UI Surface

The current product UI is organized into these areas:

- Dashboard: a shared dashboard app with home, devices, logs, and queue views
- Automations: overview, library, builder, and log data
- APIs: registry, incoming, outgoing, webhooks, and connector setup
- Tools: catalog plus configuration pages for the current runtime-managed tools
- Scripts: reusable script library
- Settings: workspace, logging, notifications, access, and data

## Current Architecture

### Backend

- FastAPI app serving feature routers under `/api/v1/**`, `/health`, and the built UI/static surface
- Runtime scheduler, trigger queue, worker registration/claim flow, and automation execution services
- Feature APIs for automations, runs, inbound and outgoing APIs, webhooks, connectors, tools, scripts, log tables, settings, workers, dashboard status, runtime status, scheduler jobs, and trigger history
- Registry-driven served and redirect UI route registration via `backend/page_registry.py` and `ui/page-registry.json`

### Frontend

- Vite-built HTML entry pages and route metadata driven by `ui/page-registry.json`
- Mixed stack: React/TypeScript pages for dashboard and automations
- TypeScript/DOM page logic for the scripts library
- Vanilla JavaScript pages for APIs, settings, and tool configuration
- Shared shell/navigation contract for topnav/sidenav
- Redirect and legacy alias support for canonical UI routes

### Data

- PostgreSQL is the runtime database
- Schema source of truth: `backend/database.py`
- Tool metadata, connector settings, automation state, scripts, log tables, API definitions, event histories, delivery history, and integration presets are persisted in PostgreSQL

## Database Schema

`backend/database.py` is the only schema source of truth. The app initializes PostgreSQL tables there and applies additive column evolution from the same module.

Current table groups:

- API registry: `inbound_apis`, `inbound_api_events`, `outgoing_scheduled_apis`, `outgoing_continuous_apis`, `webhook_apis`, `webhook_api_events`, `outgoing_delivery_history`
- Workspace state: `tools`, `settings`, `integration_presets`
- Automation runtime: `automations`, `automation_steps`, `automation_runs`, `automation_run_steps`
- Script library: `scripts`
- Log schema: `log_db_tables`, `log_db_columns`

Schema conventions in `backend/database.py`:

- additive table creation uses `CREATE TABLE IF NOT EXISTS`
- additive column changes use `_ensure_column(...)`
- boolean-like flags are stored as integer-compatible `0` and `1` values
- structured payloads are typically persisted in `*_json` text columns

## Repository Map

### Core backend

- `backend/main.py` - app factory and mounting
- `backend/routes/` - feature API routers plus UI-serving glue
- `backend/page_registry.py` - UI page registry loader and validator
- `backend/runtime.py` - runtime event bus, queue, and worker state
- `backend/services/` - runtime and feature logic
- `backend/schemas/` - request/response contracts
- `backend/database.py` - schema initialization and additive evolution
- `backend/tool_registry.py` - seed tool catalog plus DB sync and manifest support

### Core frontend

- `ui/<section>/<page>.html` - page entry HTML
- `ui/page-registry.json` - canonical served and redirect UI page registry
- `ui/page-registry.ts` - Vite input generation from the page registry
- `ui/src/` - React/TS features for dashboard and automations, plus TypeScript modules such as the scripts library and shared frontend helpers
- `ui/scripts/` - vanilla page controllers plus shared shell logic for APIs, settings, and tools
- `ui/modals/` - shared modal HTML fragments loaded by vanilla UI pages
- `ui/styles/` - shared and page styles
- `ui/vite.config.ts` - Vite config using registry-derived inputs

### Tooling and tests

- `scripts/` - developer scripts and test runners
- `tests/` - backend tests, API coverage, and smoke registry/matrix support
- `ui/src/**/__tests__/` - frontend unit tests for React/TypeScript features
- `ui/e2e/` - Playwright workflow coverage

## Quick Start

### Prerequisites

- macOS or Linux shell
- Python 3.x
- Node.js + npm
- PostgreSQL reachable on `127.0.0.1:5432`

Notes:

- On macOS/Homebrew, `./malcom` can auto-start a Homebrew PostgreSQL service if PostgreSQL is not already responsive.
- On Linux or non-Homebrew setups, start PostgreSQL yourself before running `./malcom`.

### 1) Set database URL

```bash
export MALCOM_DATABASE_URL="postgresql://postgres:postgres@127.0.0.1:5432/malcom"
```

If omitted, the app falls back to `postgresql://postgres:postgres@127.0.0.1:5432/malcom`.

Note:

- The FastAPI app reads `MALCOM_DATABASE_URL`.
- The `./malcom` launcher still checks for a PostgreSQL listener on `127.0.0.1:5432` before startup, regardless of that env var.

### 2) Start the app

```bash
./malcom
```

What this launcher does:

- creates and uses `./.venv` if needed
- re-execs into `./.venv`
- installs backend dependencies from `requirements.txt`
- installs UI dependencies with `npm ci` in `ui/`
- builds UI when inputs changed
- checks PostgreSQL responsiveness on `127.0.0.1:5432`
- attempts Homebrew PostgreSQL startup when needed on supported macOS setups
- starts Uvicorn with `--reload` on `127.0.0.1:8000`
- aborts if port `8000` is already occupied

### 3) Open the app

- UI and API host: `http://127.0.0.1:8000`

## Testing Workflow

Malcom uses a two-tier test workflow.

Before running the test scripts:

- Run `./malcom` once first, or otherwise create `./.venv`, install `requirements.txt`, and install `ui/` dependencies.
- Set `MALCOM_TEST_DATABASE_URL` to a dedicated PostgreSQL database.
- If `MALCOM_TEST_DATABASE_URL` is unset, tests fall back to `MALCOM_DATABASE_URL`, then `postgresql://postgres:postgres@127.0.0.1:5432/malcom_test`.

Important:

- Playwright and test reset helpers truncate core tables and drop dynamic log data tables in the resolved test database.
- Do not point `MALCOM_TEST_DATABASE_URL` or fallback values at a database you want to keep.

### Fast local iteration

```bash
./scripts/test-precommit.sh
```

Runs:

- PostgreSQL test DB preflight and schema initialization
- backend pytest suite excluding smoke marker (`-m "not smoke"`)
- UI entry wiring check (`node scripts/check-ui-page-entry-modules.mjs`)
- frontend unit tests (`npm test` in `ui/`)
- frontend build (`npm run build` in `ui/`)

### Full completion gate

```bash
./scripts/test-full.sh
```

Runs:

- everything from `test-precommit.sh`
- smoke matrix (`pytest tests/test_api_smoke_matrix.py -m smoke`)
- external probe report (`python scripts/test-external-probes.py`)
- Playwright workflows (`npm run test:e2e` in `ui/`)

Playwright details:

- Launches its own app server through `scripts/run_playwright_server.sh`
- Resets the test database before startup
- Uses `MALCOM_TEST_DATABASE_URL` when set, otherwise falls back to `MALCOM_DATABASE_URL`, then `malcom_test`

Targeted browser iteration:

```bash
cd ui && npx playwright test <spec>
```

Before using the targeted Playwright command:

- install browser binaries once with `cd ui && npm run test:e2e:install`
- make sure built UI assets already exist, for example by running `./malcom` once or `cd ui && npm run build`

### Test policy

- Behavior-changing implementation work must add or update relevant automated tests in the same change.
- User-visible workflow changes require Playwright coverage updates unless strictly non-behavioral.
- API route additions/removals must stay aligned with `tests/test_api_smoke_matrix.py` and `tests/api_smoke_registry/`.

## UI and Route Wiring

For a new served UI page to work end-to-end:

1. Add `ui/<section>/<page>.html`.
2. Wire the page entry in the HTML itself:
   - React pages load `ui/src/<feature>/main.tsx` or `main.ts`.
   - Vanilla pages load `ui/scripts/<section>/<page>.js`.
3. Add the route record to `ui/page-registry.json`, including `serveMode`, legacy aliases, and redirect target when needed.
4. Build UI with `cd ui && npm run build`.

Notes:

- Do not hand-edit `ui/dist/**`.
- Vite inputs and backend-served UI routes derive from the page registry.
- The registry supports canonical served pages, redirect-only routes, and legacy aliases.
- Page entry modules are checked by `scripts/check-ui-page-entry-modules.mjs`; new page wiring should stay within the page's section instead of adding arbitrary new root-level entry files.
- Shared shell pages should use `id="topnav"`, `id="sidenav"`, `data-section`, and usually `data-sidenav-item` plus `data-shell-path-prefix`.
- Dashboard subpages are routed as redirects into the main dashboard entry with hash-based subroutes.
- The Tools section combines static catalog navigation with manifest-driven tool entries; enabled state filters the shell nav, while tool page routes still come from the page registry.

## Connectors vs Tools

Use the right integration model:

- **Connectors**: saved provider auth, base URL, scopes, and reusable remote API settings (Google, GitHub, etc.).
- **Outgoing APIs / HTTP steps**: request definitions for raw or custom remote API calls, including connector-scoped preset-driven requests in automation steps.
- **Connector activities**: provider-aware automation actions with explicit inputs, outputs, and required scopes.
- **Tools**: local or worker-bound machine capabilities exposed through the managed tool catalog (for example SMTP, local LLM, Coqui TTS, and Image Magic).

Rule of thumb:

- Remote SaaS/API access belongs in connectors plus outgoing APIs, automation HTTP steps, or provider-aware connector activities.
- Use connector activities for common provider actions in the automation builder; keep generic HTTP steps for raw or custom calls.
- Do not model remote API calls as tools unless local runtime execution or worker-bound machine behavior is required.

Google-specific onboarding:

- Start from the Connect provider control on the Connectors page.
- Do not collect OAuth credentials via browser `prompt()` dialogs.

## Troubleshooting

### Port conflicts

Common ports:

- `5432` PostgreSQL
- `8000` FastAPI/Uvicorn
- `4173` Playwright server default (auto-falls forward when busy)
- `2525` SMTP tool listener (tool config dependent)

- `./malcom` requires `8000` to be free and aborts if it is occupied.
- When available, `./malcom` prints existing listeners with `lsof` before exiting.
- Playwright starts at `4173` and automatically selects the next free port if needed.
- When startup or Playwright launch fails, check active listeners first and inspect `backend/data/logs/` for companion startup/runtime errors.

### Playwright/browser setup

Install browsers once:

```bash
cd ui && npm run test:e2e:install
```

Target a specific port when needed:

```bash
cd ui && PLAYWRIGHT_PORT=4190 npx playwright test <spec>
```

## Contributing

1. Read `AGENTS.md` before implementation work.
2. Keep changes small and aligned with existing source-of-truth files.
3. Add or update relevant tests in the same change when behavior changes.
4. Use `./scripts/test-precommit.sh` for normal iteration.
5. Use `./scripts/test-full.sh` for user-visible workflow changes, shared frontend or test-infra changes, and browser workflow validation.
6. Update `ui/e2e/` when user-visible workflows change.
7. Keep `/health` and `/api/v1/**` smoke coverage aligned with `tests/test_api_smoke_matrix.py` and `tests/api_smoke_registry/`.
8. Manually verify the served route when HTML/script wiring changes, in addition to build and test coverage.
9. Do not hand-edit generated outputs such as `ui/dist/**`; regenerate artifacts like the tools manifest from source.
