# Malcom: Local Automation Middleware

⚠️ **For development work, see [AGENTS.md](AGENTS.md) first** — it contains all operational rules for modifying this repo.

## Project Overview

This project is a **self-hosted local automation middleware** designed to run continuously on a low‑power MacBook (currently used as a Plex server).

The system acts as a **local orchestration layer** between:

* local programs and managed runtimes
* machine-executed capabilities such as local AI/model services
* external APIs and SaaS providers reached through connector-backed HTTP requests

The goal is to allow the user to **build and manage automations without relying on third‑party cloud automation platforms** such as Zapier, Make, or similar services.

The system exposes a **local API and web interface** for managing and executing automations.

---

# Core Goals

1. Run reliably on low-power hardware
2. Avoid external cloud dependencies
3. Provide a local automation engine
4. Support scheduled and triggered automations
5. Be easily expandable with new connectors
6. Provide a clean management UI
7. Be compatible with a future mobile WebView app

---

# Architecture Overview

The system follows a simplified version of the architecture used by enterprise integration platforms.

## Layers

### 1. UI Layer

Vite-built HTML entry pages using a mix of React pages and vanilla JavaScript pages for:

* managing automations
* viewing run history
* editing automations
* viewing logs

The UI runs in a browser and is designed to later run inside a **mobile WebView wrapper**.

### Shared Navigation Shell

The UI shell now uses a **shared navigation contract** so the logo, top navigation, side navigation, and section metadata stay aligned across static HTML pages and the React dashboard.

Source of truth:

* `ui/scripts/shell-config.js` for brand and navigation definitions
* `ui/scripts/navigation.js` for static shell rendering
* `ui/src/dashboard/app.tsx` consuming the same shell config for the React dashboard

For static pages, the expected pattern is:

* declare `data-section`
* declare `data-sidenav-item`
* declare `data-shell-path-prefix`
* render `<div id="topnav"></div>`
* render `<aside id="sidenav"></aside>`

Do not manually duplicate top navigation or side navigation markup on new pages.

### Tool Registration And Configuration Pages

The Tools section is registration-driven.

Tools are for **machine-executed capabilities** that Malcom runs locally or through a managed runtime or worker. Remote API integrations such as Gmail belong in the connector and outgoing-request flows unless they require a local executable/runtime layer.

Source of truth:

* `backend/tool_registry.py` for the default tool catalog seed data
* the `tools` table in PostgreSQL for persisted enabled state and metadata overrides
* `scripts/generate-tools-manifest.mjs` to regenerate `ui/scripts/tools-manifest.js`
* `ui/scripts/shell-config.js` consuming the generated manifest to build the tools sidenav
* `ui/tools/catalog.html` as the directory page for metadata edits and enable/disable state
* `ui/tools/<tool-id>.html` as the per-tool configuration page in the sidenav

Expected sequence for adding a new tool:

1. Add the tool entry to the catalog in `backend/tool_registry.py` with `id`, `name`, and `description`.
2. Add `ui/tools/<tool-id>.html` and use the shared shell placeholders: `id="topnav"` and `id="sidenav"`.
3. Set `data-section="tools"`, `data-sidenav-item="sidenav-tools-<tool-id>"`, `data-shell-path-prefix="../"`, and `data-tool-id="<tool-id>"` on the page body.
4. Add the page to `ui/page-registry.json` and `ui/vite.config.ts`; `backend/routes/ui.py` serves it through the registry.
5. Run `node scripts/generate-tools-manifest.mjs`.
6. Build the UI and confirm the tool appears in both the catalog page and the sidenav without manual nav edits.

The catalog page edits metadata and enabled state through `/api/v1/tools` and `/api/v1/tools/{tool_id}/directory`.
Tool-specific runtime configuration, when needed, should live on the per-tool page rather than being embedded in the catalog.
Do not create new `tools/<tool-id>/tool.json` files for tool registration. That legacy filesystem flow has been replaced by database-backed tool records plus the generated manifest.

### Connector-Backed Remote APIs And HTTP Requests

Use these three concepts separately:

* **Connectors** store reusable provider auth, scopes, and base URLs for remote APIs.
* **Outgoing APIs** and automation **HTTP request steps** define the actual request URL, method, payload, and cadence.
* **Tools** are reserved for locally executed or runtime-managed capabilities, not remote API calls by themselves.

Example:

* a Gmail unread-count integration should use a Google/Gmail connector plus an outgoing API or automation HTTP step
* it should not be added as a Tool unless Malcom must run a local program or managed runtime to perform that work

### 2. API Layer

FastAPI service responsible for:

* exposing REST endpoints
* receiving automation triggers
* managing configuration
* interacting with the execution engine

### 3. Automation Engine (Runtime)

The runtime is responsible for:

* executing automations
* calling APIs
* processing responses
* running logic rules
* triggering next steps
* managing retries

Current implementation includes:

* persisted automation definitions in PostgreSQL
* manual, scheduled, and inbound API-triggered execution
* structured run history with step-level request and response summaries
* runtime and scheduler status APIs for the management UI

### 4. Scheduler

An in-process custom scheduler/runtime loop handles time-based triggers.

Examples:

* hourly API polling
* daily automation runs
* periodic health checks

Current implementation note:

* the scheduler runs as an in-process runtime loop tied to FastAPI lifespan
* scheduled automations and scheduled outgoing APIs share the same scheduler status surface

### 5. Connectors

Connectors store reusable auth and provider metadata for remote services and HTTP APIs.

Examples:

* Gmail and other Google APIs
* Google Calendar
* Google Sheets
* GitHub

Connectors are reused by outgoing APIs and automation HTTP request steps. They are not the same thing as Tools.

Google connector onboarding rule:

* start Google connector setup from the **Connect provider** action on the Connectors page
* complete credential entry inside the connector details modal (Client ID, Client secret, Redirect URI)
* do not collect OAuth credentials with browser popup prompts
* follow Google OAuth best practices: configure OAuth consent screen, use OAuth 2.0 Web application credentials, and register the exact redirect URI shown by Malcom
* reference docs: https://developers.google.com/identity/protocols/oauth2/web-server
* automation builder connector activities: provider-aware connector activities should appear as explicit selectable actions with action-specific inputs/outputs in the automation builder UI; do not hide them behind generic connector config.

### 6. Storage

PostgreSQL database used for:

* automation definitions
* job schedules
* execution history
* logs
* configuration
* editable tool metadata overrides
* persisted tool catalog records and enablement state

### Inbound API Secret Policy

Inbound API bearer secrets are treated as opaque credentials for server-to-server authentication.

Rules:

* generate secrets with a cryptographically secure random source
* use 256 bits of entropy for production-generated inbound bearer secrets
* encode the random payload with URL-safe Base64 and prefix it with a stable Malcom identifier
* store only the SHA-256 hash of the secret in PostgreSQL
* return the plaintext secret only once when an inbound API is created or rotated
* require operators to store the returned secret externally because list and detail endpoints do not expose it later
* rotate secrets when a credential is shared, leaked, or reaches the team rotation window

Developer mode exception:

* seeded developer fixtures may use a fixed token for deterministic local UI testing
* fixed developer tokens must not be reused for production-generated inbound APIs

---

# Technology Stack

## Backend

* Python
* FastAPI
* PostgreSQL

### Database Configuration

Set `MALCOM_DATABASE_URL` to a PostgreSQL connection string before starting the app.

Example:

```bash
export MALCOM_DATABASE_URL="postgresql://postgres:postgres@127.0.0.1:5432/malcom"
```

If `MALCOM_DATABASE_URL` is not set, the app defaults to `postgresql://postgres:postgres@127.0.0.1:5432/malcom`.

## Port Reference

All ports used by the app and its tools are listed here. If a service fails to start with `Address already in use`, check this table first.

| Port | Service | Host | Configurable? |
|------|---------|------|---------------|
| **5432** | PostgreSQL | `127.0.0.1` | Yes — via `MALCOM_DATABASE_URL` env var |
| **8000** | FastAPI / Uvicorn (HTTP API + served UI) | `127.0.0.1` | No — hardcoded in `scripts/dev.py` |
| **2525** | SMTP tool local listener | `127.0.0.1` | Yes — per-tool config in Settings → SMTP |
| **4173** | Playwright e2e test server | `127.0.0.1` | No — hardcoded in `ui/playwright.config.ts` |
| **1234** | LM Studio API (LLM tool preset) | `127.0.0.1` | Yes — preset only; editable in Settings → LLM |

Notes:

* **8000** is the most likely conflict on a developer machine. Stop any existing `./malcom` process before relaunching.
* **5432** and **8000** are the only ports required to run the app without optional tools.
* The SMTP tool relay port (used in automation steps) is not listed here because it is user-supplied per-step, not a server port owned by this app.

## Frontend

* Vite-built HTML entry pages
* React for some pages and vanilla JavaScript for others
* TypeScript (preferred for new React/TS UI code where applicable)
* CSS with semantic classes and stable IDs
* Radix / primitive UI components


For frontend development, prefer **TypeScript over JavaScript** for components, context providers, tests, and app entry points to improve safety and maintainability.

## Runtime Management

* macOS launchd

## Testing Workflow

Default local validation before commits:

```bash
./scripts/test-precommit.sh
```

This runs:

* backend `pytest` coverage-oriented validation against the configured PostgreSQL database
* frontend `npm run test`
* frontend `npm run build`

Expanded validation:

```bash
./scripts/test-full.sh
```

This adds:

* route-level API smoke coverage via `pytest tests/test_api_smoke_matrix.py -m smoke`
* smoke case definitions sourced from the `tests/api_smoke_registry/` package and exercised through `tests/test_api_smoke_matrix.py`
* browser smoke coverage through Playwright in `ui/e2e/`
* connector onboarding smoke coverage that opens Settings -> Connectors, selects Connect provider, and verifies Google draft setup does not fail with a `PATCH /api/v1/settings` `422`
* connector onboarding smoke coverage that verifies the Google redirect URI field is editable and defaults to `/api/v1/connectors/google/oauth/callback` so OAuth callback values can be aligned with Google Cloud credentials
* OAuth callback browser coverage that verifies a successful authorization on `/api/v1/connectors/google/oauth/callback` redirects back to `/settings/connectors.html` with status query params
* the informational external probe report from `scripts/test-external-probes.py`

Prerequisites:

* set `MALCOM_DATABASE_URL` to a reachable local PostgreSQL instance
* prefer `MALCOM_TEST_DATABASE_URL` for the isolated test database used by `pytest` and Playwright
* install backend dependencies from `requirements.txt`
* install frontend dependencies in `ui/`
* for browser smoke tests, run `cd ui && npm run test:e2e:install` at least once to install Chromium

---

# Tool Development

Use these steps whenever a new tool is introduced or an existing tool page is expanded.

Use a tool only when the feature is a machine-executed or runtime-managed capability. For remote API work such as Gmail, prefer connectors plus outgoing APIs or automation HTTP steps.

1. Register the tool in `backend/tool_registry.py`.
2. Build or update the tool page in `ui/tools/<tool-id>.html`.
3. Prefer shared scripts for common tool-page behavior and add tool-specific scripts only when runtime behavior differs, such as `ui/scripts/smtp.js`.
4. Run `node scripts/generate-tools-manifest.mjs` so the overview and sidenav use the latest metadata.
5. Run `npm run build` in `ui/`.
6. Verify the built page is emitted in `ui/dist/tools/`.
7. Open `tools/catalog.html`, edit the tool metadata, toggle enabled/disabled, and confirm the matching sidenav entry opens the correct configuration page.

Legacy note:

* `tools/<tool-id>/tool.json` is no longer used for new tool registration.
* new tools must be added to the backend catalog seed and then propagated through the generated manifest.

---

# Example Automation

Example automation:

1. Scheduler triggers job
2. Automation engine loads automation
3. HTTP request sent to API
4. Response parsed
5. Logic rule evaluated
6. Follow-up action executed
7. Result logged

Automation API surface:

* `GET /api/v1/automations`
* `POST /api/v1/automations`
* `GET /api/v1/automations/{automation_id}`
* `PATCH /api/v1/automations/{automation_id}`
* `DELETE /api/v1/automations/{automation_id}`
* `POST /api/v1/automations/{automation_id}/validate`
* `GET /api/v1/automations/{automation_id}/runs`
* `POST /api/v1/automations/{automation_id}/execute`
* `GET /api/v1/runtime/status`
* `GET /api/v1/scheduler/jobs`

---

# Development Principles

Keep the system:

* simple
* modular
* reliable
* local-first

Avoid over-engineering early versions.

Do not introduce:

* distributed systems
* complex message brokers
* heavy container orchestration

until they are proven necessary.

---

# UI Principles

The UI should behave like a **clean operational admin tool** rather than a flashy SaaS product.

All UI elements must include explicit, stable `id` attributes so they can be reliably targeted for automation, testing, and accessibility tasks.

Avoid:

* flashy dashboards
* oversized cards
* heavy animations
* marketing-style spacing
* overly rounded "no-code" UI patterns

Prefer:

* tables
* structured lists
* clear forms
* readable logs
* operational status indicators

The UI must work well on:

* desktop
* tablet
* mobile

Navigation should also remain structurally consistent across every section:

* top navigation is rendered from the shared shell config
* the Malcom brand appears in the side navigation header
* per-page shell differences should come from metadata, not copied markup

---

# Design Template (Project UI Standard)

This section defines the **visual and structural design system** used across the project. The goal is consistency, simplicity, and long-term maintainability.

## Design Tone

The UI should feel **accessible, calm, and easy to use**, similar to well-designed SaaS tools such as Akeneo or Pendo.

Characteristics:

* easy to understand at a glance
* minimal visual noise
* structured layouts
* approachable but professional

Avoid experimental or overly playful design patterns.

---

## Color Philosophy

The interface should remain **largely neutral**.

Color should be used primarily for **categorization and meaning**, for example:

* automation categories
* connector types
* success / warning / error states
* system health indicators

Color should communicate meaning rather than decoration.

---

## Theme

The initial version of the UI supports **light mode only**.

Dark mode may be added later once the design system stabilizes.

---

## Layout Structure

Use a simple **application shell layout**.

### Top Bar

Contains:

* project title
* quick actions
* system status indicator

---

# Contributions

## Verification

Default validation:

```bash
./scripts/test-precommit.sh
```

Expanded validation:

```bash
./scripts/test-full.sh
```

Notes:

* backend tests run with `pytest`, not `unittest`
* `scripts/test-precommit.sh` runs backend `pytest`, frontend `npm test`, and frontend `npm run build`
* `scripts/test-full.sh` runs the precommit checks, then executes `tests/test_api_smoke_matrix.py` as the smoke test entrypoint, using the `tests/api_smoke_registry/` package for smoke case definitions, before the external probe report and Playwright smoke coverage

## Adding A New Tool

Tools are defined in the backend catalog and surfaced in the UI through a generated manifest.

This path is for runtime-managed capabilities. If the feature is a remote API integration that can be expressed as an HTTP request with saved credentials, use connectors plus outgoing APIs or automation HTTP steps instead of the tool catalog.

Primary registration sources:

* `backend/tool_registry.py`
* the PostgreSQL `tools` table
* `ui/scripts/tools-manifest.js`

Rules:

* the tool `id` is the stable slug used by routes, DB rows, and sidenav items
* every tool must define `id`, `name`, and `description`
* keep descriptions concise and UI-ready
* do not add new `tools/<tool-id>/tool.json` files

Example:

```python
{
  "id": "rss-poller",
  "name": "RSS Poller",
  "description": "Fetch RSS feeds on a schedule and emit normalized entries for downstream automations.",
}
```

After adding or updating a tool, regenerate the UI manifest:

```bash
node scripts/generate-tools-manifest.mjs
```

Expected behavior:

* the command writes `ui/scripts/tools-manifest.js`
* `ui/tools/catalog.html` renders the new tool automatically
* no manual HTML edits are required to add the card
* the manifest is generated from the backend tool catalog and stored DB records
* saved name and description edits are stored in PostgreSQL as overrides

Local UI note:

* opening `ui/tools/catalog.html` directly from disk is supported
* when opened via `file://`, the UI sends API requests to `http://localhost:8000`

Verification steps:

1. Add the tool entry in `backend/tool_registry.py`.
2. Run `node scripts/generate-tools-manifest.mjs`.
3. Open `ui/tools/catalog.html`.
4. Confirm the new tool card appears with the correct name and description.

### Sidebar Navigation

Primary navigation is **sidebar-first**.

Desktop behavior:

* sidebar visible by default
* collapsible
* icon-only collapsed state available

Navigation sections:

* Automations
* Runs
* Connectors
* Settings

### Mobile Navigation

On smaller screens:

* sidebar becomes a drawer
* navigation remains accessible via icon

### Collapsible Sections

For collapsible settings/content panels in the app UI:

* use a compact full-width collapse bar (not a CTA button)
* place the collapse bar directly under the section title and above the collapsible content
* show `-` when expanded and `+` when collapsed
* wire `aria-expanded` + `aria-controls` on the toggle
* use `hidden` on the controlled content container
* keep stable IDs for the toggle, symbol, and content panel

---

## Page Template

Each major screen follows the same structure.

### Page Header

* page title
* short description
* primary action button

### Main Content

Primary surface for:

* tables
* structured lists

### Detail Panels

Used for:

* editing forms
* configuration settings
* automation steps

### Supporting UI

Includes:

* logs
* status badges
* alerts

---

## Automation Editing Model

Automation editing uses a **hybrid approach**.

Initial version:

* structured step list editor

Future versions may introduce:

* visual node graph editor

The system architecture should allow both models.

---

## Logs and Execution Views

Execution history should display **structured step logs**.

Each automation run should show:

* step-by-step execution
* request summaries
* response summaries
* status
* execution time

Steps should be expandable to reveal detailed information.

---

## Component Standards

Use simple reusable primitives.

Core components:

* Buttons
* Inputs
* Selects
* Textareas
* Switches
* Tables
* Tabs
* Drawers
* Dialogs
* Badges
* Alerts
* Accordions

Avoid highly specialized components unless functionality requires them.

---

## Typography

Typography should prioritize **clarity and readability**.

Guidelines:

* clean sans-serif
* clear hierarchy
* readable technical text

Logs and execution outputs must be easy to scan.

---

## Spacing and Density

Use **balanced information density**.

The UI should:

* avoid excessive padding
* avoid cramped layouts
* maintain predictable spacing

Operational tables should remain efficient but readable.

---

## Icons

Icons should be:

* minimal
* functional
* supportive of meaning

Icons must never be required to understand a feature.

---

## Animations

Animations should remain extremely limited.

Allowed uses:

* loading states
* success feedback
* error feedback

Avoid decorative motion.

---

## Responsive Strategy

The same UI must function across:

* desktop browser
* tablet browser
* mobile browser
* future mobile WebView wrapper

Guidelines:

* avoid fixed-width layouts
* avoid hover-only interactions
* maintain large touch targets
* prefer drawers over modals on small screens

---

## Technology Alignment

Frontend stack assumed by this design template:

* Vite-built HTML entry pages
* React for some pages and vanilla JavaScript for others
* CSS with semantic classes and stable IDs
* Radix primitives / shadcn-style components

This combination provides:

* accessibility
* cross-device compatibility
* flexible styling
* long-term maintainability

---

## UI Build Steps (Incremental)

Based on the current frontend architecture, the UI uses:

- Vite-built HTML entry pages
- React for some pages and vanilla JavaScript for others
- CSS with semantic classes and stable IDs
- Radix UI
- shadcn-style component patterns

Avoid introducing Material UI, Bootstrap, or bulky UI frameworks.

## Single Command Dev Launcher

Use the root launcher to prepare dependencies and start the app:

```bash
./malcom
```

Expected behavior:

1. verifies or creates the root `.venv`
2. installs backend dependencies from `requirements.txt` when needed
3. installs UI dependencies in `ui/` when needed
4. builds the UI into `ui/dist/`
5. starts the backend on `http://127.0.0.1:8000`

Notes:

* this is the local development launcher, not the final `launchd` packaging path
* stop the app with `Ctrl+C`
* the dashboard and static UI pages are served by FastAPI from the built UI output
