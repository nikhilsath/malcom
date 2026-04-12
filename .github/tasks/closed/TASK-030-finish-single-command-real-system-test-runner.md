# TASK-030 finish single-command real-system test runner

Assumption: `TASK-028-environment-first-real-system-test-workflow.md` and `TASK-029-replace-disallowed-stubbed-playwright-tests.md` have been completed. This follow-up closes the remaining gap to the original goal of real tests, one command, environment bootstrap, and minimal failure output.

## Execution steps

1. [x] [scripts]
Files: app/scripts/test-real-failfast.sh, app/scripts/test-system.sh, AGENTS.md, app/tests/AGENTS.md, app/ui/e2e/README.md, README.md
Action: Removed the legacy `failfast-result.json` mirror and made `app/tests/test-artifacts/system-result.json` the only supported artifact path. `test-real-failfast.sh` now preserves delegated failures without exiting early under `set -e`, and the policy/docs layer was updated to describe one canonical artifact contract.
Completion check: a forced failing invocation leaves `app/tests/test-artifacts/system-result.json` present with the expected `step`, `exit_code`, `command`, and `first_error_lines` contract.

2. [x] [scripts]
Files: app/scripts/test-system.sh, README.md, app/tests/AGENTS.md
Action: Tightened the bootstrap contract so missing `.venv/bin/python`, missing test tooling, missing frontend dependencies, and missing Chromium browser binaries fail through the same small `system-result.json` contract instead of raw shell-only errors. The browser prerequisite probe now resolves Playwright from `app/ui`, which keeps the check accurate in this repo layout.
Completion check: representative prerequisite failures exit through the same documented artifact contract instead of producing an unstructured shell-only failure.

3. [x] [scripts]
Files: .github/workflows/ci.yml, README.md, app/tests/AGENTS.md, app/ui/e2e/README.md
Action: Finished converging on the supported commands by removing stale CI and documentation references to the deleted stubbed Playwright project. CI now calls the canonical real-system command and uses the full real Playwright suite as the secondary browser validation instead of `--project=stubbed`.
Completion check: `.github/workflows/ci.yml` contains no `stubbed` Playwright references and the docs consistently describe the same primary command and supported secondary checks.

4. [x] [test]
Files: app/scripts/test-real-failfast.sh, app/scripts/test-system.sh, app/tests/test_real_test_runner_contract.py
Action: Added focused automated verification for the runner contract itself. The new pytest coverage shells into both runner scripts with a controlled bootstrap failure and asserts the canonical artifact shape, failure-stage naming, and retired legacy path behavior.
Completion check: the runner contract has automated coverage where the new implementation introduces logic that is not already protected by the existing shell-script integration flow.

## Test impact review

1. [x] [test]
Files: app/scripts/test-real-failfast.sh
Action: update — the wrapper now preserves the documented canonical artifact contract on delegated failure and should be validated with a controlled failing run.
Completion check: `artifact_dir=$(mktemp -d) && export MALCOM_TEST_ARTIFACT_DIR="$artifact_dir" MALCOM_TEST_DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:1/malcom_test SKIP_BROWSER_SUITE=1 && bash app/scripts/test-real-failfast.sh >/tmp/task30-failfast.log 2>&1 || true && python3 - <<'PY'
import json
import os
from pathlib import Path
artifact_dir = Path(os.environ["MALCOM_TEST_ARTIFACT_DIR"])
data = json.loads((artifact_dir / "system-result.json").read_text())
assert set(data) == {"step", "exit_code", "command", "first_error_lines"}
assert data["step"] == "bootstrap"
assert data["exit_code"] != 0
assert not (artifact_dir / "failfast-result.json").exists()
PY`

2. [x] [test]
Files: app/scripts/test-system.sh
Action: update — prerequisite/bootstrap failures should return the same small artifact shape rather than raw shell-only failures.
Completion check: `artifact_dir=$(mktemp -d) && export MALCOM_TEST_ARTIFACT_DIR="$artifact_dir" MALCOM_TEST_DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:1/malcom_test SKIP_BROWSER_SUITE=1 && bash app/scripts/test-system.sh >/tmp/task30-system.log 2>&1 || true && python3 - <<'PY'
import json
import os
from pathlib import Path
data = json.loads((Path(os.environ["MALCOM_TEST_ARTIFACT_DIR"]) / "system-result.json").read_text())
assert set(data) == {"step", "exit_code", "command", "first_error_lines"}
assert data["step"] == "bootstrap"
assert data["exit_code"] != 0
assert isinstance(data["first_error_lines"], list)
PY`

3. [x] [test]
Files: .github/workflows/ci.yml, README.md, app/tests/AGENTS.md, app/ui/e2e/README.md
Action: update — the CI and documentation layer must be revalidated after the final single-command convergence changes land.
Completion check: `rg -n "stubbed|project=stubbed" .github/workflows/ci.yml README.md app/tests/AGENTS.md app/ui/e2e/README.md`

## Testing

1. [x] [test]
Files: app/scripts/test-real-failfast.sh, app/scripts/test-system.sh, app/tests/test-artifacts/
Action: Validate the controlled bootstrap-failure path and confirm the runner writes the documented minimal artifact contract for the failing stage.
Completion check: `artifact_dir=$(mktemp -d) && export MALCOM_TEST_ARTIFACT_DIR="$artifact_dir" MALCOM_TEST_DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:1/malcom_test SKIP_BROWSER_SUITE=1 && bash app/scripts/test-real-failfast.sh >/tmp/task30-failfast.log 2>&1 || true && cat "$artifact_dir/system-result.json"`

2. [x] [test]
Files: app/scripts/test-system.sh, app/tests/test-artifacts/
Action: Run the canonical real-system command in a supported environment and confirm the success artifact is still written after the bootstrap/contract hardening work.
Completion check: `bash app/scripts/test-system.sh`

3. [x] [test]
Files: .github/workflows/ci.yml, README.md, app/tests/AGENTS.md, app/ui/e2e/README.md, app/scripts/check-policy.sh
Action: Re-run the policy/docs/workflow checks after the one-command convergence changes land.
Completion check: `bash app/scripts/check-policy.sh`

## GitHub update

1. [ ] [github]
Files: app/scripts/test-real-failfast.sh, app/scripts/test-system.sh, app/tests/test_real_test_runner_contract.py, .github/workflows/ci.yml, AGENTS.md, README.md, app/tests/AGENTS.md, app/ui/e2e/README.md, app/scripts/check-policy.sh, .github/tasks/closed/TASK-030-finish-single-command-real-system-test-runner.md
Action: When the work is complete, stage the relevant files only and update GitHub using the repo’s required workflow in AGENTS.md#github-update-workflow.
Completion check: `git add app/scripts/test-real-failfast.sh app/scripts/test-system.sh app/tests/test_real_test_runner_contract.py .github/workflows/ci.yml AGENTS.md README.md app/tests/AGENTS.md app/ui/e2e/README.md app/scripts/check-policy.sh .github/tasks/closed/TASK-030-finish-single-command-real-system-test-runner.md && git commit -m "Finish single-command real-system test runner" && git push`
