"""Tests for backend/services/workflow_storage.py file-write helpers."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.services.workflow_storage import (
    execute_workflow_write,
    write_csv_row,
    write_json_file,
    write_other_file,
)


class TestWriteCsvRow:
    def test_first_write_appends_headers_when_provided(self, tmp_path: Path) -> None:
        dest = write_csv_row(tmp_path, "events", ["2024-01-01", "click", "1"], headers=["ts", "evt", "value"])
        lines = dest.read_text().splitlines()
        assert lines[0] == "ts,evt,value"
        assert lines[1] == "2024-01-01,click,1"

    def test_second_write_appends_without_repeating_headers(self, tmp_path: Path) -> None:
        write_csv_row(tmp_path, "events", ["2024-01-01", "a", "1"], headers=["ts", "evt", "value"])
        write_csv_row(tmp_path, "events", ["2024-01-02", "b", "2"], headers=["ts", "evt", "value"])
        lines = (tmp_path / "events.csv").read_text().splitlines()
        assert len(lines) == 3  # header + 2 rows
        assert lines[0] == "ts,evt,value"
        assert lines[2] == "2024-01-02,b,2"

    def test_no_headers_writes_only_row(self, tmp_path: Path) -> None:
        dest = write_csv_row(tmp_path, "data", ["a", "b"])
        assert dest.read_text().strip() == "a,b"


class TestWriteJsonFile:
    def test_new_file_true_creates_timestamped_file(self, tmp_path: Path) -> None:
        dest = write_json_file(tmp_path, "export", {"key": "value"}, new_file=True)
        assert dest.name.startswith("export-")
        assert dest.name.endswith(".json")
        assert json.loads(dest.read_text()) == {"key": "value"}

    def test_two_new_file_true_calls_create_distinct_files(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        import time
        dest1 = write_json_file(tmp_path, "export", {"n": 1}, new_file=True)
        time.sleep(0.01)
        dest2 = write_json_file(tmp_path, "export", {"n": 2}, new_file=True)
        assert json.loads(dest1.read_text()) == {"n": 1}
        assert json.loads(dest2.read_text()) == {"n": 2}

    def test_new_file_false_appends_ndjson(self, tmp_path: Path) -> None:
        write_json_file(tmp_path, "stream", {"n": 1}, new_file=False)
        write_json_file(tmp_path, "stream", {"n": 2}, new_file=False)
        lines = (tmp_path / "stream.json").read_text().strip().splitlines()
        assert len(lines) == 2
        assert json.loads(lines[0]) == {"n": 1}
        assert json.loads(lines[1]) == {"n": 2}


class TestExecuteWorkflowWrite:
    def test_csv_dispatches_to_csv_writer(self, tmp_path: Path) -> None:
        result = execute_workflow_write(
            root_dir=tmp_path,
            storage_path_setting="workflows",
            storage_type="csv",
            target="runs",
            payload={"row": ["ts1", "v1"], "headers": ["ts", "v"]},
        )
        assert result["storage_type"] == "csv"
        dest = Path(result["file"])
        assert dest.exists()
        lines = dest.read_text().splitlines()
        assert lines[0] == "ts,v"
        assert lines[1] == "ts1,v1"

    def test_table_dispatches_to_csv_writer(self, tmp_path: Path) -> None:
        result = execute_workflow_write(
            root_dir=tmp_path,
            storage_path_setting="workflows",
            storage_type="table",
            target="rows",
            payload=["a", "b"],
        )
        assert result["storage_type"] == "table"
        dest = Path(result["file"])
        assert dest.exists()

    def test_json_creates_timestamped_file(self, tmp_path: Path) -> None:
        result = execute_workflow_write(
            root_dir=tmp_path,
            storage_path_setting="workflows",
            storage_type="json",
            target="data",
            payload={"foo": "bar"},
            new_file=True,
        )
        assert result["storage_type"] == "json"
        dest = Path(result["file"])
        assert dest.name.startswith("data-")
        assert json.loads(dest.read_text()) == {"foo": "bar"}

    def test_other_writes_timestamped_fallback(self, tmp_path: Path) -> None:
        result = execute_workflow_write(
            root_dir=tmp_path,
            storage_path_setting="workflows",
            storage_type="other",
            target="misc",
            payload="raw",
        )
        dest = Path(result["file"])
        assert dest.exists()

    def test_storage_dir_created_when_missing(self, tmp_path: Path) -> None:
        result = execute_workflow_write(
            root_dir=tmp_path,
            storage_path_setting="deep/nested/workflows",
            storage_type="json",
            target="x",
            payload=1,
            new_file=True,
        )
        assert Path(result["file"]).exists()
