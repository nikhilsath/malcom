# Task Executor Instructions

Purpose:
Execute work from one existing task file.
Do not create new task files unless the user explicitly asks.
Your job is to take one task file, perform its current step, update the task file in place, and stop cleanly when blocked or when the current run has completed its allowed scope.

## Core Rules

- Work from one task file at a time.
- Do not switch to another task unless the user explicitly tells you to.
- Do not create a new task file if an existing task file already covers the request.
- Treat the task file as the only execution memory for the task.
- Update the task file as work progresses.
- Do not rely on hidden memory from previous runs.
- Do not expand scope beyond the task file.
- If the task file conflicts with repo-wide hard safety rules in `AGENTS.md`, follow `AGENTS.md`.
- If the task file is missing required structure, stop and report that issue instead of guessing.

## Task Selection Rules

If the user gives a specific task file or task ID, use that task.

If the user refers to an existing task without naming it clearly, identify the likely matching task and ask whether to continue that task or start a new one.

If multiple open tasks exist, do not choose a different one mid-run. Remain on the task you were assigned.

## Required Inputs

Before starting execution, confirm that you have:
- one task file
- the current `AGENTS.md`
- any routed instruction files explicitly required by the current step and current repo structure

Do not read all instruction files up front.
Read only what is needed for the current step.

## Execution Model

Work section by section in the task file.

Expected section order:
1. Confirm and update task instructions
2. Test impact review
3. Execution steps
4. Testing steps
5. Documentation updates
6. GitHub update

Section order is binding.

Do not skip ahead unless:
- the task file explicitly allows it
- or the current step is marked `Execution: parallel_ok`

Default assumption:
- steps are sequential

If a step is marked `Execution: parallel_ok`, it may be done independently of other `parallel_ok` steps in the same section. It does not permit reordering unrelated sequential steps or jumping to another section.

Execution scope per run:
- default to one active step at a time
- finish the active step completely before stopping, unless blocked
- do not continue to the next step automatically unless the current response explicitly includes that continuation
- do not attempt to complete the whole task in one run just because enough context is available
- do not ask the user for confirmation between sub-actions that are clearly required to satisfy the active step’s completion check
- only ask the user for input when:
  - the current step is blocked
  - the task file is ambiguous
  - the next action would expand or change scope
  - or the current step is complete and the task file does not authorize automatic continuation

Before starting the Execution steps section, check whether the task includes a Test impact review section.

If it does:
- complete that section first
- do not proceed into implementation while known-stale tests remain unreviewed

If the task changes a user-visible workflow and no early test-impact step exists:
- stop and report that the task file is missing required pre-execution test-impact handling
- do not continue into implementation

## GitHub Hard Rules

Git operations are forbidden unless the current step route is `github` and the active section is `GitHub update`.

This includes:
- `git add`
- `git commit`
- `git push`
- drafting commit commands
- staging files in preparation for a later commit
- proposing commit or push commands early

Treat any GitHub workflow instructions found in `AGENTS.md` or elsewhere in the repo as inactive unless the active step route is `github` and the active section is `GitHub update`.

If you are about to stage, commit, or push before reaching the GitHub update section, stop immediately and report that you are out of section order.

## Step Handling Rules

Every step should already have:
- a routing label
- a clear action
- a completion check

For each step:
1. read only the relevant routed instructions from `AGENTS.md`
2. update the task file to mark the step `[-]` before running commands or edits
3. perform the action
4. verify the completion check
5. update the task file again before doing anything else

If the completion check is satisfied:
- mark the step `[x]`

If the step is blocked:
- mark it `[!]`
- record the exact blocker directly under that step
- stop unless another step is explicitly safe to continue independently

Do not mark a step completed just because code was changed.
Only mark it completed when the completion check is satisfied.

Do not expand or rewrite future steps just because you now understand them better.

You may update downstream steps only when:
- the Confirm and update task instructions section changed the verified implementation path
- a current step cannot be executed safely without correcting stale downstream instructions
- the task file explicitly tells you to revise a later step now

Otherwise:
- execute the current step only
- leave later steps unchanged until their section is reached

If completing a verification-first step changes the task assumptions:
- pause execution
- review all affected downstream steps
- update stale downstream wording in place
- only resume once later sections match verified reality

Do not continue into stale downstream execution, testing, documentation, or GitHub steps.

## Task File Update Rules

The task file is the authoritative execution record.

Do not rely on temporary agent todos, chat summaries, or internal plans as state.

When working a task, update it in place.

Use these step state markers:
- `[ ]` not started
- `[-]` in progress
- `[x]` completed
- `[!]` blocked

When you begin a step:
- change it to `[-]` before running any command

When you complete a step:
- change it to `[x]`

When marking a step completed:
- update the existing checklist line in place
- do not append a duplicate checklist line
- do not create a new row for the same step
- if the task file contains a metadata row or state table, update the existing entry in place

When you hit a blocker:
- change the step to `[!]`
- add a short blocker note directly under that step

When a blocked step becomes unblocked later:
- change `[!]` back to `[-]` when resuming
- then to `[x]` only after the completion check passes

When the verification section changes verified reality:
- update downstream step text before continuing
- keep the original user goal
- remove stale assumptions from later sections
- do not leave later sections written against a disproved path

Do not report progress or propose a next step until the task file has been updated in place.

## Confirm and Update Task Instructions Section

This section comes first for a reason.

In this section:
- verify that the task still matches the current repo state
- verify assumptions before implementation
- correct the task file if its assumptions are outdated
- do not start implementation before this section is handled

If repo reality differs from the task:
- update the task file first
- keep the scope aligned with the original user goal
- do not silently continue with stale assumptions

If this section changes or narrows the verified implementation path:
- review all later sections before executing them
- update stale steps that still reflect the old assumption
- do not continue into later sections until downstream steps match verified reality

If the user proposed a source of truth, architecture pattern, storage location, ownership model, or routing model:
- treat that proposal as something to verify first
- do not treat it as settled fact unless repo reality confirms it

Testing is not allowed in this section unless the active step explicitly calls for a narrow test-inspection command.

## Test Impact Review Rules

This section exists to identify test impact before implementation, not to run the main test suite.

When you reach Test impact review:
- identify affected backend tests
- identify affected frontend or unit tests
- identify affected Playwright tests in `ui/e2e/`
- decide for each affected test whether it should be kept, rewritten, replaced, or removed
- update the task file if later sections still assume stale test coverage

If stale Playwright tests are known and have not yet been updated:
- do not proceed into implementation that will be blocked by those tests
- first perform the required pre-execution Playwright rewrite or retirement step if the task provides one
- if the task file does not provide one, stop and report that the task file is incomplete

Unless the active Test impact review step explicitly requires it, do not run backend, frontend, or Playwright suites in this section.

## Routing Rules

Use the routing label on the current step to decide what to read.

Examples:
- `backend` → backend-relevant routed instructions
- `ui` → UI-relevant routed instructions
- `db` → database-relevant routed instructions
- `test` → testing instructions
- `docs` → documentation instructions
- `github` → GitHub update instructions

Do not read unrelated routed sections.
Do not load all AGENTS files or all instruction files by default.

## Execution Steps Rules

While in the Execution steps section:
- perform only implementation work described by the active execution step
- satisfy the active execution step’s completion check before stopping, unless blocked
- do not stop after partial progress if the remaining work is clearly part of the same active step and does not require user input
- do not run tests here unless the active execution step explicitly requires prerequisite test scaffolding
- do not add new testing detail here just because likely tests are now known
- do not rewrite the Testing steps section unless stale assumptions from verification require it

If the current task changes UI workflows, selectors, routes, API response shapes, or source-of-truth behavior:
- use the Test impact review output to identify stale tests before continuing
- do not wait until the Testing steps section to discover known-stale coverage

## Testing Rules

Testing is limited to the Testing steps section unless:
- the active Test impact review step explicitly requires a narrow test-inspection command
- or the active Execution step explicitly requires prerequisite test scaffolding

Outside those exceptions, do not run tests during:
- Confirm and update task instructions
- Test impact review
- Execution steps
- Documentation updates
- GitHub update

Running backend, frontend, Playwright, or full-suite test commands is forbidden outside the Testing steps section unless the active step explicitly names a narrow inspection command or prerequisite scaffolding command.
If the active step does not explicitly call for a test command, do not run one.

When you reach the Testing steps section:
- follow the routed testing instructions in `AGENTS.md`
- edit existing tests where needed
- add new tests where needed
- delete superfluous tests only when the task explicitly supports that
- run only the test commands required by the active Testing step
- record the exact command run and whether it passed or failed in the task file

Do not default to the full test suite unless the active Testing step explicitly says to do so.

If the verification section changed the verified implementation path:
- ensure testing steps were updated to match the verified path before running them
- do not run tests that still encode the disproved assumption

For tasks affecting user-visible workflows, Playwright handling begins with Test impact review and continues in the Testing steps section.

Before running affected Playwright tests:
- identify existing Playwright tests affected by the task
- determine whether each should be kept, rewritten, replaced, or removed
- apply required Playwright updates before running the affected suite

If stale Playwright tests are known and have not yet been updated:
- do not treat their failure as a normal blocker
- update the task file and correct the stale tests first

Do not rewrite or subdivide the Testing steps section early just because likely tests are now known.
Only modify the Testing steps section when:
- the verification section changed the verified implementation path
- the existing testing steps are stale because of that change
- or the current step explicitly requires test-preparation edits now

If tests fail:
- do not claim the task is complete
- update the task file with the exact failing area
- continue only if the next step explicitly makes sense without passing tests

## Documentation Rules

When you reach the Documentation updates section:
- follow the routed documentation instructions in `AGENTS.md`
- update only the documentation relevant to the completed changes
- do not invent documentation work outside the task scope

If the verification section changed the verified implementation path:
- ensure documentation steps were updated to match the verified path before editing docs
- do not document the original assumption if the verification section disproved it

Record in the task file what docs were updated.

Do not move documentation work into earlier sections unless the current step explicitly requires it.

## GitHub Update Rules

When you reach the GitHub update section:
- follow the GitHub update instructions in `AGENTS.md`
- stage only task-relevant files
- use a task-specific commit message
- do not include unrelated changes

If the verification section changed the verified implementation path:
- ensure GitHub update notes and commit message reflect the verified change, not the disproved assumption

Record in the task file:
- whether changes were staged
- the commit message used
- whether push succeeded

## Completion Rules

A task is complete only when:
- all required sections have been handled
- all required steps are `[x]`
- no required step remains `[ ]`, `[-]`, or `[!]`
- required tests and documentation steps were handled according to the task file
- GitHub update steps were handled if required by the task

When the task is complete:
- mark the task as complete inside the task file
- move it from `.agents/tasks/open/` to `.agents/tasks/done/` if the workflow for this repo supports that move
- if you are not the agent responsible for moving files, state clearly that the task content is complete and ready to be moved

Explicit final step requirement for task files:

- Every task file must include, as the final explicit step under "Notes and hand-off" or in the GitHub update section, a short instruction indicating that the executor should move the completed task file to `.agents/tasks/done/` and record the commit that included the move. Example text to include at the end of the task file:

  "Finalize: Once all checklist items are [x], move this file to `.agents/tasks/done/` and commit the move with a focused message (e.g., 'Move TASK-xxx to done after completion'). If you cannot move the file, mark the task run notes and notify the owner."

- Rationale: making the move an explicit, written final step in the task file prevents accidental omission and provides an audit trail linking the task to the commit that closed it.

File lifecycle on completion:
- if the repo uses `.agents/tasks/done/`, move the completed task file there and preserve the filename
- if the repo expects deletion instead, delete the file from `.agents/tasks/open/` only after recording completion metadata
- never create a new task file to represent the same completed work

## Stop Conditions

Stop and report immediately if:
- the task file is missing
- the task file is too ambiguous to execute safely
- the routing label does not map to usable repo instructions
- the step completion check cannot be evaluated
- the task conflicts with repo-wide hard safety rules
- the next task number, file path, or task identity is unclear and that ambiguity affects execution
- the work would require expanding scope beyond the task file
- the verification section changed the verified path and downstream sections cannot be safely rewritten without expanding scope
- you are about to continue into later sections without being asked
- you are about to rewrite future sections without a verified-path change
- you are about to expand the task beyond the current step or required correction
- the task affects user-visible workflow behavior, existing Playwright coverage is likely stale, and the task file does not include an early step to review and update affected tests
- you are about to run tests outside the Testing steps section without an explicit exception in the active step
- you are about to report progress or a next step without first updating the task file in place

## Output Rules

When reporting progress, be exact.

Include:
- task file being executed
- step updated in the task file
- steps completed
- steps blocked
- tests run
- docs updated
- GitHub update status
- next step

Do not give a vague success message.
Do not say the task is done unless the completion rules are satisfied.