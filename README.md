# Malcom

Malcom is a local-first automation workspace that combines a FastAPI backend, PostgreSQL persistence, a Vite-built multi-page UI, and an in-process runtime for automations, APIs, connectors, tools, storage, and documentation.

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
- Workspace state: `tools`, `settings`, `integration_presets`, `connectors`, `log_db_tables`, `log_db_columns`, `connector_endpoint_definitions`
- Automation runtime: `automations`, `automation_steps`, `automation_runs`, `automation_run_steps`, `runtime_resource_snapshots`
- Script library: `scripts`
- Documentation: `docs_articles`, `docs_tags`, `docs_article_tags`
- Storage: `storage_locations`, `repo_checkouts`

Important runtime ownership:

- saved connectors are canonical in `connectors`
- connector activity and HTTP preset rows are canonical in `connector_endpoint_definitions` when present
- storage destinations are canonical in `storage_locations`
- repo clones tracked by the app are canonical in `repo_checkouts`
- docs article metadata lives in the docs tables, while article bodies are written to `data/docs/*.md`

## Repository Map

- [`app/backend/`](/Users/nikhilsathyanarayana/Documents/malcom/app/backend): FastAPI app, routes, schemas, services, migrations, runtime helpers
- [`app/ui/`](/Users/nikhilsathyanarayana/Documents/malcom/app/ui): HTML entries, React apps, vanilla page controllers, styles, Playwright tests
- [`app/tests/`](/Users/nikhilsathyanarayana/Documents/malcom/app/tests): backend and integration tests plus API smoke registry
- [`app/scripts/`](/Users/nikhilsathyanarayana/Documents/malcom/app/scripts): developer utilities, policy checks, startup helpers, test runners
- [`data/`](/Users/nikhilsathyanarayana/Documents/malcom/data): backups, config, docs, logs, media, workflow output
- [`.github/tasks/`](/Users/nikhilsathyanarayana/Documents/malcom/.github/tasks): task history and active task records

## Quick Start

The reliable manual startup path today is:

1. Create the virtual environment and install backend dependencies.
2. Install frontend dependencies.
3. Make sure PostgreSQL is running and reachable.
4. Build the UI.
5. Start the backend from `app/`.

Example:

```bash
python3 -m venv .venv
./.venv/bin/pip install -r app/requirements.txt
npm --prefix app/ui ci
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
- the checked-in `./malcom` launcher currently points at `app/scripts/dev.py`, but that script still references an undefined `ROOT_DIR`, so it should not be treated as the stable startup path yet

## Testing Workflow

### Environment-first design

The test system builds the environment it needs rather than depending on a standing manual setup. This makes the workflow repeatable for new-environment preparation and CI alike.

Primary environment-building real-system command (bootstrap prerequisites → DB setup → startup lifecycle → backend suite → critical browser subset, stops on first failure):

```bash
bash app/scripts/test-system.sh
```

On failure, `app/scripts/test-system.sh` writes the machine-readable result artifact to `app/tests/test-artifacts/system-result.json`.

`test-precommit.sh` calls `test-real-failfast.sh`, which delegates to `test-system.sh` — so the environment-first approach is used automatically at every gate level.

### Local gates

Fast local verification (runs `test-real-failfast.sh` → `test-system.sh` internally):

```bash
./app/scripts/test-precommit.sh
```

Full completion gate:

```bash
./app/scripts/test-full.sh
```

Supported secondary browser check:

```bash
npm --prefix app/ui run test:e2e
```

Useful focused commands:

```bash
npm --prefix app/ui run build
npm --prefix app/ui test
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

## Unfinished Features

These gaps are visible in the current codebase and should be treated as active follow-up work:


- GitHub trigger setup is exposed in the automation builder, but the dedicated webhook dispatch helper in [`app/backend/services/github_webhook.py`](/Users/nikhilsathyanarayana/Documents/malcom/app/backend/services/github_webhook.py) still stops at logging instead of enqueueing runtime work.
- The browser test for GitHub trigger creation is still a smoke placeholder in [`app/ui/e2e/github-trigger.spec.ts`](/Users/nikhilsathyanarayana/Documents/malcom/app/ui/e2e/github-trigger.spec.ts).
- The standalone storage automation step executor is still unimplemented in [`app/backend/services/automation_step_executors/storage.py`](/Users/nikhilsathyanarayana/Documents/malcom/app/backend/services/automation_step_executors/storage.py), so storage behavior currently rides through Log-step storage options instead.
- Notion and Trello connectors can be stored and used generically, but they still do not ship provider-specific connector activities or HTTP presets in the builder.
- Trello OAuth support is still limited by a demo-style callback contract and does not support refresh tokens.
- Settings Data still labels payload redaction as coming soon in [`app/ui/settings/data.html`](/Users/nikhilsathyanarayana/Documents/malcom/app/ui/settings/data.html).
