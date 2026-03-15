# README.md

## Project Overview

This project is a **self-hosted local automation middleware** designed to run continuously on a low‑power MacBook (currently used as a Plex server).

The system acts as a **local orchestration layer** between:

* local programs
* locally run AI tools
* MCP tools
* external APIs

The goal is to allow the user to **build and manage automations without relying on third‑party cloud automation platforms** such as Zapier, Make, or similar services.

The system exposes a **local API and web interface** for managing and executing automations.

---

# Core Goals

1. Run reliably on low-power hardware
2. Avoid external cloud dependencies
3. Provide a local automation engine
4. Support scheduled and triggered workflows
5. Be easily expandable with new connectors
6. Provide a clean management UI
7. Be compatible with a future mobile WebView app

---

# Architecture Overview

The system follows a simplified version of the architecture used by enterprise integration platforms.

## Layers

### 1. UI Layer

React application used for:

* managing automations
* viewing run history
* editing workflows
* viewing logs

The UI runs in a browser and is designed to later run inside a **mobile WebView wrapper**.

### Developer Mode Toggle

The UI includes a **Developer Mode toggle** intended for local development and QA workflows.

When enabled, it uses browser storage options to seed/populate interface state so developers can quickly load realistic UI scenarios for testing without requiring live backend data.

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

### 2. API Layer

FastAPI service responsible for:

* exposing REST endpoints
* receiving automation triggers
* managing configuration
* interacting with the execution engine

### 3. Automation Engine (Runtime)

The runtime is responsible for:

* executing automation workflows
* calling APIs
* processing responses
* running logic rules
* triggering next steps
* managing retries

Current implementation includes:

* persisted automation definitions in SQLite
* manual, scheduled, and inbound API-triggered execution
* structured run history with step-level request and response summaries
* runtime and scheduler status APIs for the management UI

### 4. Scheduler

APScheduler handles time-based triggers.

Examples:

* hourly API polling
* daily automation runs
* periodic health checks

Current implementation note:

* the project currently uses an in-process scheduler loop tied to FastAPI lifespan
* scheduled automations and scheduled outgoing APIs share the same scheduler status surface

### 5. Connectors

Modular connectors handle interaction with external systems.

Examples:

* HTTP APIs
* local scripts
* AI tools
* MCP tools

### 6. Storage

SQLite database used for:

* automation definitions
* job schedules
* execution history
* logs
* configuration
* editable tool metadata overrides

### Inbound API Secret Policy

Inbound API bearer secrets are treated as opaque credentials for server-to-server authentication.

Rules:

* generate secrets with a cryptographically secure random source
* use 256 bits of entropy for production-generated inbound bearer secrets
* encode the random payload with URL-safe Base64 and prefix it with a stable Malcom identifier
* store only the SHA-256 hash of the secret in SQLite
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
* APScheduler
* SQLite

## Frontend

* React
* TypeScript (preferred for all new UI code)
* CSS with semantic classes and stable IDs
* Radix / primitive UI components


For frontend development, prefer **TypeScript over JavaScript** for components, context providers, tests, and app entry points to improve safety and maintainability.

## Runtime Management

* macOS launchd

---

# Example Automation

Example workflow:

1. Scheduler triggers job
2. Automation engine loads workflow
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

All UI elements must include explicit, stable `id` attributes so they can be reliably targeted for automation, testing, and accessibility workflows.

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
* **Developer Mode toggle**

Developer Mode enables a **session-only development environment** that:

* uses fake/mock data
* allows safe experimentation
* does not modify real automations or stored data

Developer Mode resets when the session ends.

---

# Contributions

## Verification

Backend tests:

```bash
.venv/bin/python -m unittest discover -s tests -q
```

Frontend tests:

```bash
cd ui && npm test
```

Frontend build:

```bash
cd ui && npm run build
```

## Adding A New Tool

Tools are discovered from the top-level `tools/` directory and surfaced in the UI through a generated manifest.

Each tool must live in its own folder:

* `tools/<tool-id>/tool.json`

Rules:

* the folder name is the tool slug
* the `id` field in `tool.json` must exactly match the folder name
* every tool must define `id`, `name`, and `description`
* keep descriptions concise and UI-ready

Example:

```json
{
  "id": "rss-poller",
  "name": "RSS Poller",
  "description": "Fetch RSS feeds on a schedule and emit normalized entries for downstream automations."
}
```

After adding or updating a tool, regenerate the UI manifest:

```bash
node scripts/generate-tools-manifest.mjs
```

Expected behavior:

* the command writes `ui/scripts/tools-manifest.js`
* `ui/tools.html` renders the new tool automatically
* no manual HTML edits are required to add the card
* tool folders are still discovered from `tools/<tool-id>/tool.json`
* saved name and description edits are stored in SQLite as overrides

Local UI note:

* opening `ui/tools.html` directly from disk is supported
* when opened via `file://`, the UI sends API requests to `http://localhost:8000`

Verification steps:

1. Create `tools/<tool-id>/tool.json`.
2. Run `node scripts/generate-tools-manifest.mjs`.
3. Open `ui/tools.html`.
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

* React
* CSS with semantic classes and stable IDs
* Radix primitives / shadcn-style components

This combination provides:

* accessibility
* cross-device compatibility
* flexible styling
* long-term maintainability

---

## UI Build Steps (Incremental)

Based on the latest design advice, the frontend should use:

- React
- CSS with semantic classes and stable IDs
- Radix UI
- shadcn-style component patterns

Avoid introducing Material UI, Bootstrap, or bulky UI frameworks.

### Step 1: Developer Mode Toggle

Scope:
- Add a top bar with a session-scoped **Developer Mode** toggle.
- Persist toggle state to `sessionStorage` (resets when browser session ends).
- Include stable IDs for automation/testing hooks.

Expected behavior:
1. Toggle defaults to off in a fresh session.
2. Toggling on stores `developerMode=true` in `sessionStorage`.
3. Toggling off stores `developerMode=false`.
4. Toggle and related top bar elements are addressable by explicit IDs.

Verification steps:
1. Start the UI (`npm run dev` from `ui/`).
2. Confirm the top bar renders with the Developer Mode toggle.
3. Toggle it on and inspect `sessionStorage.developerMode` in DevTools.
4. Refresh tab: value remains within the current session.
5. Close session and open a new one: value resets to default off.

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
