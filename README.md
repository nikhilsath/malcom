# README.md

## Project Overview

This project is a **self‑hosted local automation middleware** designed to run continuously on a low‑power MacBook (currently used as a Plex server).

The system acts as a **local orchestration layer** between:

* local programs
* locally run AI tools
* MCP tools
* external APIs

The goal is to allow the user to **build and manage automations without relying on third‑party cloud automation platforms** such as Zapier, Make, or similar services.

The system exposes a **local API and web interface** for managing and executing automations.

---

# Core Goals

1. Run reliably on low‑power hardware
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

APScheduler handles time‑based triggers.

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
6. Follow‑up action executed
7. Result logged

---

# Development Principles

Keep the system:

* simple
* modular
* reliable
* local‑first

Avoid over‑engineering early versions.

Do not introduce:

* distributed systems
* complex message brokers
* heavy container orchestration

until they are proven necessary.

---

# UI Principles

The UI should behave like a **clean operational admin tool**.

Avoid:

* flashy dashboards
* oversized cards
* heavy animations

Prefer:

* tables
* lists
* structured forms
* readable logs

The UI must work well on:

* desktop
* tablet
* mobile

---

# Future Expansion

Possible future additions:

* additional worker machines
* distributed execution
* advanced workflow editor
* mobile wrapper app
* additional connectors

---

# agents.md

## Purpose

Agents represent automated actors capable of executing workflows, running tasks, or interacting with external systems.

The middleware may eventually coordinate multiple agents across different machines.

---

## Agent Responsibilities

Agents may be responsible for:

* executing automation workflows
* running local scripts
* calling external APIs
* interacting with AI tools
* processing job queues

Agents should be **stateless workers** whenever possible.

Persistent state should be stored in the main system database.

---

## Agent Types

### Local Runtime Agent

Runs on the main MacBook server.

Responsibilities:

* execute workflows
* schedule jobs
* process API responses

---

### Worker Agents (Future)

Optional future agents that run on other machines.

These may handle:

* CPU‑heavy work
* AI processing
* batch tasks

---

## Agent Communication

Agents communicate through the middleware API.

Typical pattern:

1. agent requests job
2. middleware assigns task
3. agent executes task
4. agent returns result

---

## Reliability Rules

Agents must:

* report execution status
* retry transient failures
* avoid duplicate task execution

---

## Design Principle

Agents should remain:

* lightweight
* replaceable
* independent of UI

The middleware remains the central coordinator.
