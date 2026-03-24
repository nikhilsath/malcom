# Malcom

Local-first automation middleware built with FastAPI, PostgreSQL, and a Vite-based web UI.

For development policy and architecture rules, read `AGENTS.md` first.

## Table of Contents

- [What Malcom Does](#what-malcom-does)
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

- an API surface for managing automations, APIs, connectors, tools, scripts, settings, and runtime status
- a browser UI for operations and configuration
- an in-process runtime for scheduled and triggered automation execution
- persisted execution history and step-level run details in PostgreSQL

Primary goals:

1. Run reliably on low-power local hardware.
2. Keep workflows local-first.
3. Stay extensible for connectors and runtime-managed tools.

## Current Architecture

### Backend

- FastAPI app and route composition
- Runtime scheduler and automation execution services
- API endpoints under `/api/v1/**`
- HTML page serving through UI route registration

### Frontend

- Vite-built HTML entry pages
- Mixed stack: React/TypeScript pages and vanilla JavaScript pages
- Shared shell/navigation contract for topnav/sidenav

### Data

- PostgreSQL is the runtime database
- Schema source of truth: `backend/database.py`

## Repository Map

### Core backend

- `backend/main.py` - app factory and mounting
- `backend/routes/` - API and HTML routes
- `backend/services/` - runtime and feature logic
- `backend/schemas/` - request/response contracts
- `backend/database.py` - schema initialization and additive evolution

### Core frontend

- `ui/<section>/<page>.html` - page entry HTML
- `ui/src/` - React/TS features
- `ui/scripts/` - vanilla page controllers and shared shell logic
- `ui/styles/` - shared and page styles
- `ui/vite.config.ts` - Vite entry registration

### Tooling and tests

- `scripts/` - developer scripts and test runners
- `tests/` - backend/API tests and smoke matrix
- `ui/e2e/` - Playwright workflow coverage

## Quick Start

### Prerequisites

- macOS or Linux shell
- Python 3.x
- Node.js + npm
- PostgreSQL reachable locally

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
- installs backend dependencies from `requirements.txt`
- installs UI dependencies with `npm ci` in `ui/`
- builds UI when inputs changed
- checks PostgreSQL responsiveness
- starts Uvicorn on `127.0.0.1:8000`

### 3) Open the app

- UI and API host: `http://127.0.0.1:8000`

## Testing Workflow

Malcom uses a two-tier test workflow.

### Fast local iteration

```bash
./scripts/test-precommit.sh
```

Runs:

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

### Test policy

- Behavior-changing implementation work must add or update relevant automated tests in the same change.
- User-visible workflow changes require Playwright coverage updates unless strictly non-behavioral.
- API route additions/removals must stay aligned with `tests/test_api_smoke_matrix.py` and `tests/api_smoke_registry/`.

## UI and Route Wiring

For a new served UI page to work end-to-end:

1. Add `ui/<section>/<page>.html`.
2. Register the page in `ui/vite.config.ts` input entries.
3. Add or update the served route in `backend/routes/ui.py`.
4. Build UI with `cd ui && npm run build`.

Notes:

- Do not hand-edit `ui/dist/**`.
- Shared shell pages should use `id="topnav"`, `id="sidenav"`, plus page metadata attributes.

## Connectors vs Tools

Use the right integration model:

- **Connectors**: saved provider auth/base URL/scopes for remote APIs (Google, GitHub, etc.).
- **Outgoing APIs / HTTP steps**: request definitions (URL, method, payload, cadence).
- **Tools**: runtime-managed or machine-executed local capabilities (for example local SMTP, local LLM, TTS).

Rule of thumb:

- Remote SaaS/API access belongs in connectors + HTTP request flows.
- Do not model remote API calls as tools unless local runtime execution is required.

Google-specific onboarding:

- Start from the Connect provider control on the Connectors page.
- Do not collect OAuth credentials via browser `prompt()` dialogs.

## Troubleshooting

### Port conflicts

Common ports:

- `5432` PostgreSQL
- `8000` FastAPI/Uvicorn
- `4173` Playwright server default (can vary)
- `2525` SMTP tool listener (tool config dependent)

If startup fails because a port is busy, inspect active listeners and stop the conflicting process before retrying.

### Playwright/browser setup

Install browsers once:

```bash
cd ui && npm run test:e2e:install
```

## Contributing

1. Read `AGENTS.md` before implementation work.
2. Keep changes small and aligned with existing source-of-truth files.
3. Add or update relevant tests in the same change when behavior changes.
4. Run the appropriate validation tier before marking work complete.
