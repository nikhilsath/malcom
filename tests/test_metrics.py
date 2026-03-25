from __future__ import annotations

from backend.services.metrics import get_metrics_collector


def test_metrics_collector_records_and_summarizes_operations() -> None:
    collector = get_metrics_collector()
    collector.clear()

    collector.record_execution(component="automation_executor", operation="step_tool", duration_ms=120.0, memory_mb=3.5, error=False)
    collector.record_execution(component="automation_executor", operation="step_tool", duration_ms=80.0, memory_mb=1.0, error=True)

    summary = collector.summary()
    assert summary["total_metrics"] == 1
    assert len(summary["metrics"]) == 1

    metric = summary["metrics"][0]
    assert metric["component"] == "automation_executor"
    assert metric["operation"] == "step_tool"
    assert metric["executions"] == 2
    assert metric["error_count"] == 1
    assert metric["max_duration_ms"] == 120.0
    assert metric["memory_peak_mb"] == 3.5

    collector.clear()


def test_metrics_collector_filters_by_component() -> None:
    collector = get_metrics_collector()
    collector.clear()

    collector.record_execution(component="automation_executor", operation="step_http", duration_ms=50.0)
    collector.record_execution(component="worker", operation="poll", duration_ms=10.0)

    component_metrics = collector.by_component("automation_executor")
    assert component_metrics["component"] == "automation_executor"
    assert len(component_metrics["operations"]) == 1
    assert component_metrics["operations"][0]["operation"] == "step_http"

    collector.clear()
