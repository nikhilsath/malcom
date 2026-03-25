# Malcom

Local-first automation middleware built with FastAPI, PostgreSQL, and a Vite-based web UI.

For development policy and architecture rules, read `AGENTS.md` first.
Then load only the relevant domain policy file for the task:

- `backend/AGENTS.md` for backend, schema, and tool/backend contract work
- `ui/AGENTS.md` for frontend structure, shell, styles, and route wiring work
- `tests/AGENTS.md` for verification workflow and test execution policy

## Table of Contents

- [What Malcom Does](#what-malcom-does)
- [UI Surface](#ui-surface)
- [Current Architecture](#current-architecture)
- [Repository Map](#repository-map)
- [Quick Start](#quick-start)
- [Testing Workflow](#testing-workflow)
- [UI and Route Wiring](#ui-and-route-wiring)
- [Connectors vs Tools](#connectors-vs-tools)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

## What Malcom Does

Malcom is a self-hosted orchestration layer for automation workflows.

It provides:

- an API surface for managing automations, runs, APIs, connectors, tools, scripts, settings, log tables, workers, and runtime status
- a browser UI for dashboard monitoring, automation authoring, API management, scripts, tools, and workspace settings
- an in-process runtime with scheduled execution, trigger queueing, worker registration and claiming, and automation run coordination
- connector-backed remote API integrations for outgoing APIs, automation HTTP steps, and provider-aware connector activities
- a DB-backed tool catalog reflected into the UI shell through generated manifest data
- persisted execution history and step-level run details in PostgreSQL

Primary goals:

1. Run reliably on low-power local hardware.
2. Keep workflows local-first.
3. Stay extensible for connectors and runtime-managed tools.

## UI Surface

The current product UI is organized into these areas:

- Dashboard: home, devices, logs, and queue
- Automations: overview, library, builder, and log data
- APIs: registry, incoming, outgoing, and webhooks
- Tools: catalog plus tool-specific configuration pages
- Scripts: reusable script library
- Settings: workspace, logging, notifications, access, connectors, and data

## Current Architecture

### Backend

- FastAPI app with feature routers under `/api/v1/**` plus `/health`
- Runtime scheduler, trigger queue, worker registration/claim flow, and automation execution services
- Feature APIs for automations, runs, connectors, outgoing APIs, webhooks, tools, scripts, log tables, settings, workers, dashboard status, and runtime status
- Registry-driven UI route registration via `backend/page_registry.py` and `ui/page-registry.json`

### Frontend

- Vite-built HTML entry pages driven by `ui/page-registry.json`
- Mixed stack: React/TypeScript pages for dashboard, automations, and scripts library
- Vanilla JavaScript pages for APIs, settings, and tool configuration
- Shared shell/navigation contract for topnav/sidenav
- Redirect and legacy alias support for canonical UI routes

### Data

- PostgreSQL is the runtime database
- Schema source of truth: `backend/database.py`
- Tool metadata, connector settings, automation state, scripts, and log tables are persisted in PostgreSQL

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
- `ui/src/` - React/TS features for dashboard, automations, and scripts library
- `ui/scripts/` - vanilla page controllers plus shared shell logic for APIs, settings, and tools
- `ui/styles/` - shared and page styles
- `ui/vite.config.ts` - Vite config using registry-derived inputs

### Tooling and tests

- `scripts/` - developer scripts and test runners
- `tests/` - backend/API tests and smoke matrix
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

### 3) Open the app

- UI and API host: `http://127.0.0.1:8000`

## Testing Workflow

Malcom uses a two-tier test workflow.

Before running the test scripts:

- Run `./malcom` once first, or otherwise create `./.venv`, install `requirements.txt`, and install `ui/` dependencies.
- Set `MALCOM_TEST_DATABASE_URL` to a dedicated PostgreSQL database when possible.
- If `MALCOM_TEST_DATABASE_URL` is unset, tests fall back to `MALCOM_DATABASE_URL`, then `postgresql://postgres:postgres@127.0.0.1:5432/malcom_test`.

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
- Shared shell pages should use `id="topnav"`, `id="sidenav"`, `data-section`, and usually `data-sidenav-item` plus `data-shell-path-prefix`.
- Dashboard subpages are routed as redirects into the main dashboard entry with hash-based subroutes.
- The Tools section combines static catalog navigation with manifest-driven tool pages filtered by enabled tool state.

## Connectors vs Tools

Use the right integration model:

- **Connectors**: saved provider auth, base URL, scopes, and reusable remote API settings (Google, GitHub, etc.).
- **Outgoing APIs / HTTP steps**: request definitions for raw or custom remote API calls.
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
8. Do not hand-edit generated outputs such as `ui/dist/**`; regenerate artifacts like the tools manifest from source.
