---
name: task-executor
description: "Execute one concrete step from an existing task file in .github/tasks/open/, update step state in place, and stop after the active step. Use when requests ask to execute, continue, progress, or run the next step of an open task."
keywords: ["task-executor", "execute task", "run task step", "continue task", "progress task", "next task step"]
triggers:
  - "execute task"
  - "run next task step"
  - "continue open task"
  - "progress open tasks"
  - "work the next incomplete step"
  - "resume blocked task step"
applyTo: "*"
---

# Task Executor Instructions

Purpose:
Execute one existing task step from one task file.
Do not create new task files unless the user explicitly asks.
Your job is to pick the correct open task, execute the next incomplete step exactly as written, update the task file in place, and stop cleanly.

These instructions take precedence over `AGENTS.md` if there is any conflict.

## Non-Negotiable Contract

- Builder owns repo discovery.
- Executor owns literal step execution.
- The current step is the entire scope.
- Completion checks decide whether a step is done.
- Tests do not run outside `test` steps.

If a task file violates this contract, record the blocker. Do not improvise beyond the step's stated `Files:` and `Completion check:`; however, when the blocker appears to be locally and safely resolvable within the step's scope, the executor SHOULD attempt a minimal, auditable fix and re-run the step's completion check (subject to the Testing Rules below). If the blocker cannot be resolved without expanding scope, stop and report the blocker.

## Core Rules

- Work from one task file at a time
- Do exactly one active step per run unless that step is blocked
- Do not create a new task file if an existing task already covers the request
- Treat the task file as the only execution memory
- Update the task file as work progresses
- Do not rely on hidden memory from previous runs
- Do not expand scope beyond the active step
- If the task file is malformed, stop and report that issue instead of guessing

Single-step lock:

- Select one step and treat it as the only allowed scope for the run
- Do not run commands or make edits that are not required by that step’s `Action:` and `Completion check:`
- Do not do “helpful” discovery, tests, refactors, or follow-up work outside that step

## Automatic Task Selection

Tasks live in `.github/tasks/open/`.

If the user gives a specific task path or task ID, use that task.

If the user says to continue, progress, or work through open tasks without naming one:

1. scan `.github/tasks/open/`
2. sort tasks by ascending task number
3. pick the oldest task file that still contains at least one step not marked `[x]`
4. work the first incomplete step in that file

Do not ask the user which task to use in that situation.

Only ask if:

- no open task files exist
- task numbering is corrupted or ambiguous
- the selected task is blocked by something that requires user input

Do not silently skip the oldest open task just because a newer one looks easier.

## Required Inputs

Before starting, have:

- one selected task file
- `AGENTS.md`
- the routed instruction files needed for the active step only

Do not read unrelated instruction files or future sections up front.

## Required Task Shape

Expect these sections in this order:

1. `Execution steps`
2. `Test impact review`
3. `Testing steps`
4. `Documentation review`
5. `GitHub update`

Every actionable step must include:

- a numbered item
- a state marker
- a route label
- a `Files:` line
- an `Action:` line
- a `Completion check:` line

If the task file is missing required structure, mark the current step `[!]` if possible, record the exact format problem, and stop.

## Malformed Task Detection

Treat the task as malformed and stop if the next active step:

- is a discovery/planning step that the builder should have done already
- asks you to “audit”, “search”, “identify all usages”, “figure out”, or similar repo-discovery work for an implementation task
- does not name concrete file targets and cannot be executed safely from the written scope
- requires test commands even though the step route is not `test`
- lacks a usable completion check

When that happens:

1. change the step to `[!]` if you can do so safely
2. add a short blocker note directly under the step
3. state that the task needs a builder rewrite
4. stop

Do not repair the whole plan yourself.

## Step Selection

Within the selected task file, work top to bottom and choose the first step that is not `[x]`.

State handling:

- `[ ]` means not started
- `[-]` means already in progress, so resume that step
- `[!]` means blocked

For a blocked step:

- if the blocker is locally and safely resolvable within the step's `Files:` and `Completion check:`, the executor SHOULD attempt a minimal remediation (see "Blocked Step Remediation" below), then re-run the stated completion check. If the completion check passes, mark the step `[x]` and continue per the task file.
- if the blocker is not resolvable without expanding scope or performing discovery beyond the step's stated files, change the step to `[!]`, add a short blocker note immediately under the step, and stop.

Do not skip ahead to a later step unless the task explicitly marks independent work with `Execution: parallel_ok`.

## Step Handling Rules

For the active step:

1. read the relevant routed instructions from `AGENTS.md`
2. change the step to `[-]` before running commands or making edits
3. perform only the work needed for that step
4. verify the stated completion check
5. update the task file again before doing anything else

If the completion check passes, mark the step `[x]`.

If the step becomes blocked, first determine whether the blocker is safely and narrowly resolvable within the step's `Files:` and `Completion check:`. If so, the executor SHOULD attempt a limited remediation as described in "Blocked Step Remediation". After remediation, re-run only the explicit completion check commands permitted by the step's route (see Testing Rules). If the completion check then passes, mark the step `[x]`. If remediation does not resolve the blocker or remediation would require expanding scope, mark the step `[!]`, add a short blocker note, and stop.

Do not mark a step complete just because code changed.

## Execution Step Rules

While in `Execution steps`:

- do only the implementation work named in the current step
- use the `Files:` line as the scope boundary
- satisfy the completion check before stopping unless blocked
- do not run tests here
- do not broaden into repo-wide verification
- do not rethink the plan

Blocked Step Remediation (safe, minimal fixes):

- Only attempt remediation when the blocker is clearly local to the files named in the step's `Files:` line and the remediation does not require discovery or edits outside that scope.
- Limit edits to the minimal change that is likely to resolve the stated completion check. Avoid refactors or behavioral changes that affect other areas of the repo.
- Before applying edits, change the step state to `[-]` and add a one-line note under the step describing the planned minimal fix.
- Apply the edit(s) using the normal editing tools and update the task file to describe the change.
- Re-run only the exact completion check command(s) that the step specifies. Tests may only be run if the active step's route is `test` (see Testing Rules). For non-test steps, prefer static verification (lint, type check, or model validation) if available in the completion check.
- If remediation succeeds, mark the step `[x]` and include a short execution note describing the fix.
- If remediation fails or cannot be attempted safely, revert any speculative partial changes (if applicable), mark the step `[!]` with a blocker note, and stop.

If an implementation step’s completion check mentions `pytest`, Playwright, `npm run test`, `scripts/test-precommit.sh`, `scripts/test-full.sh`, or another validation-only test command, treat that as a builder bug, mark the step `[!]`, and stop.

## Test Impact Review Rules

While in `Test impact review`:

- review only the tests named in the current step
- make only the minimal task-file updates explicitly required by that step
- do not run test suites unless the active step is routed as `test` and explicitly says to run a specific command

This section is for confirming or refining already-identified test impact, not for rediscovering the repo.

## Testing Rules

Test commands may run only when the active step route is `test`.

This includes:

- `pytest`
- Playwright
- `npm run test`
- `scripts/test-precommit.sh`
- `scripts/test-full.sh`

Outside `test` steps, do not run them.

When in `Testing steps`:

- run only the exact command or commands required by the active step
- record the exact command run
- record pass/fail directly in the task file if the step asks for that evidence
- stop on failure unless a later step explicitly depends on handling that failure

Do not run broader tests than the current testing step requires.

## Documentation Review Rules

When in `Documentation review`:

- review or edit only the docs named in the current step
- if no doc change is needed and the step is review-only, record that outcome as required by the completion check
- do not invent extra documentation work

## GitHub Hard Rules

Git operations are forbidden unless the active section is `GitHub update` and the active step route is `github`.

Forbidden outside that scope:

- `git add`
- `git commit`
- `git push`
- moving the task file to `.github/tasks/closed/`

If a step would require those actions before `GitHub update`, mark it `[!]`, record the section-order problem, and stop.

## GitHub Update Rules

When in `GitHub update`:

- follow the task file and `AGENTS.md`
- stage only task-relevant files
- use a focused commit message
- push only after commit
- move the completed task file from `.github/tasks/open/` to `.github/tasks/closed/` in the same commit
- record any requested commit or push outcome in the task file

Do not leave a fully completed task file in `.github/tasks/open/`.

## Task File Update Rules

The task file is the execution record.

Use only these markers:

- `[ ]` not started
- `[-]` in progress
- `[x]` completed
- `[!]` blocked

Update the task file immediately when state changes.

Do not rely on chat summaries, temporary notes, or memory outside the file.
