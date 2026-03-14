# agents.md

## Purpose

Agents are automated workers that execute tasks within the middleware system.

They may run automations, call APIs, process responses, or coordinate with external tools.  
Agents operate independently from the UI and interact with the system primarily through the API layer.

The middleware acts as the **central coordinator**, while agents perform the actual execution work.

---

# Core Agent Principles

Agents must follow these principles when performing work:

### 1. Small, Testable Steps

Agents should **always execute work in small, testable steps**.

Avoid large, multi-stage operations that cannot be verified incrementally.

Instead:

- break complex tasks into smaller operations
- validate each step before continuing
- log intermediate results

Example pattern:

1. load configuration
2. validate inputs
3. perform action
4. verify response
5. proceed to next step

---

### 2. Provide Testing Instructions

Whenever an agent performs development work or introduces new functionality, it must include:

- clear **testing instructions**
- expected behavior
- verification steps

Testing instructions should allow a developer to confirm that the change works without needing deep system knowledge.

Example format:

### 3. Require Stable Element IDs and Semantic CSS Classes

For any UI-facing implementation or update, **all rendered elements must have explicit, stable `id` attributes** and use **semantic CSS class names**.

Use IDs that are deterministic and human-readable so they can be used for:

- automation hooks
- UI testing
- accessibility and tooling integrations

Use CSS classes that describe the purpose or structure (e.g., `.top-navigation`, `.sidebar-menu`) rather than presentation (e.g., avoid utility classes like `.bg-blue-500`).

Avoid missing, random, or transient IDs for interactive or structural UI elements. Avoid overly complex or misaligned styling by using a traditional class/ID system instead of utility-first frameworks.

---

