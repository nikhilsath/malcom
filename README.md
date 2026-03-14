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

### 4. Scheduler

APScheduler handles time-based triggers.

Examples:

* hourly API polling
* daily automation runs
* periodic health checks

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

---

# Technology Stack

## Backend

* Python
* FastAPI
* APScheduler
* SQLite

## Frontend

* React
* Tailwind CSS
* Radix / primitive UI components

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
* Tailwind CSS
* Radix primitives / shadcn-style components

This combination provides:

* accessibility
* cross-device compatibility
* flexible styling
* long-term maintainability

---
