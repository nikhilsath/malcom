# AGENTS.md

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
