from __future__ import annotations

import logging
from pathlib import Path

from backend.schemas.automation import AutomationStepConfig, AutomationStepDefinition
from backend.services.automation_step_executors.storage import execute_storage_step


def test_execute_storage_step_writes_payload_to_default_workflow_storage(tmp_path: Path) -> None:
    step = AutomationStepDefinition(
        type="storage",
        name="Persist payload",
        config=AutomationStepConfig(storage_type="json", storage_target="events", storage_new_file=False),
    )
    result = execute_storage_step(
        None,
        logging.getLogger("test-storage-step"),
        step=step,
        context={"payload": {"event_id": 123, "status": "queued"}},
        root_dir=tmp_path,
    )

    runtime_result = result["result"]
    assert runtime_result.status == "completed"
    assert runtime_result.detail["storage_type"] == "json"
    assert runtime_result.detail["target"] == "events"
    dest = Path(runtime_result.detail["file"])
    assert dest.exists()
    assert dest.read_text().strip() == "{\"event_id\": 123, \"status\": \"queued\"}"
