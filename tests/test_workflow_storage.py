import logging
from pathlib import Path
import json

from backend.schemas.automation import AutomationStepDefinition, AutomationStepConfig
from backend.services.workflow_storage import execute_file_write


def make_step(name: str, storage_type: str | None = None, target: str | None = None, new_file: bool | None = None) -> AutomationStepDefinition:
    cfg = AutomationStepConfig()
    cfg.storage_type = storage_type
    cfg.storage_target = target
    cfg.storage_new_file = new_file
    return AutomationStepDefinition(id=None, type="log", name=name, config=cfg)


def test_csv_appends(tmp_path: Path) -> None:
    logger = logging.getLogger("test")
    step = make_step("csv-step", storage_type="csv", target="mytable")
    ctx = {"payload": {"col1": "v1", "col2": 2}}

    # first write
    res1 = execute_file_write(logger, automation_id="a1", step=step, context=ctx, root_dir=Path("."), configured_path=str(tmp_path))
    assert res1.status == "completed"
    f = tmp_path / "mytable.csv"
    assert f.exists()
    lines = f.read_text(encoding="utf-8").splitlines()
    assert lines[0].split(",") == ["col1", "col2"]
    assert "v1" in lines[1]

    # second write (append)
    ctx2 = {"payload": {"col1": "v2", "col2": 3}}
    res2 = execute_file_write(logger, automation_id="a1", step=step, context=ctx2, root_dir=Path("."), configured_path=str(tmp_path))
    assert res2.status == "completed"
    lines = f.read_text(encoding="utf-8").splitlines()
    # header + two rows
    assert len(lines) == 3
    assert "v2" in lines[2]


def test_json_newfile_and_override(tmp_path: Path) -> None:
    logger = logging.getLogger("test")
    step_new = make_step("json-step", storage_type="json", target="jtarget", new_file=True)
    ctx = {"payload": {"x": 1}}

    # new file mode should create a timestamped file
    res = execute_file_write(logger, automation_id="a2", step=step_new, context=ctx, root_dir=Path("."), configured_path=str(tmp_path))
    assert res.status == "completed"
    files = list(tmp_path.glob("jtarget-*.json"))
    assert len(files) == 1
    content = json.loads(files[0].read_text(encoding="utf-8"))
    assert content["x"] == 1

    # override to append to same file
    step_append = make_step("json-step", storage_type="json", target="jtarget", new_file=False)
    ctx2 = {"payload": {"x": 2}}
    res2 = execute_file_write(logger, automation_id="a2", step=step_append, context=ctx2, root_dir=Path("."), configured_path=str(tmp_path))
    assert res2.status == "completed"
    f = tmp_path / "jtarget.json"
    assert f.exists()
    # appended newline-delimited JSON
    lines = [l for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert any("\"x\": 2" in l for l in lines)
