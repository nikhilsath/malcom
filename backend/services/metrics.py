"""In-memory resource metrics for runtime profiling.

Tracks per-component operation counts, latency, memory deltas, and error rates.
This module is intentionally lightweight and development-friendly.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from threading import Lock
from typing import Any


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _read_process_memory_mb() -> float:
    """Best-effort process RSS memory in MB."""
    try:
        import psutil  # type: ignore

        return float(psutil.Process().memory_info().rss) / (1024.0 * 1024.0)
    except Exception:
        return 0.0


@dataclass
class ComponentMetric:
    component: str
    operation: str
    execution_count: int = 0
    total_duration_ms: float = 0.0
    max_duration_ms: float = 0.0
    min_duration_ms: float = 0.0
    memory_peak_mb: float = 0.0
    error_count: int = 0
    last_executed_at: str = ""

    def record(self, *, duration_ms: float, memory_mb: float, error: bool) -> None:
        self.execution_count += 1
        self.total_duration_ms += duration_ms
        self.max_duration_ms = max(self.max_duration_ms, duration_ms)
        self.min_duration_ms = duration_ms if self.execution_count == 1 else min(self.min_duration_ms, duration_ms)
        self.memory_peak_mb = max(self.memory_peak_mb, memory_mb)
        if error:
            self.error_count += 1
        self.last_executed_at = _utc_now_iso()

    @property
    def avg_duration_ms(self) -> float:
        if self.execution_count <= 0:
            return 0.0
        return self.total_duration_ms / self.execution_count

    def as_dict(self) -> dict[str, Any]:
        error_rate_percent = 0.0
        if self.execution_count > 0:
            error_rate_percent = (self.error_count / self.execution_count) * 100.0

        return {
            "component": self.component,
            "operation": self.operation,
            "executions": self.execution_count,
            "avg_duration_ms": round(self.avg_duration_ms, 2),
            "max_duration_ms": round(self.max_duration_ms, 2),
            "min_duration_ms": round(self.min_duration_ms, 2),
            "total_duration_ms": round(self.total_duration_ms, 2),
            "memory_peak_mb": round(self.memory_peak_mb, 2),
            "error_count": self.error_count,
            "error_rate_percent": round(error_rate_percent, 2),
            "last_executed_at": self.last_executed_at,
        }


class MetricsCollector:
    """Thread-safe singleton-like collector used by runtime paths."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._metrics: dict[str, ComponentMetric] = {}

    def record_execution(
        self,
        *,
        component: str,
        operation: str,
        duration_ms: float,
        memory_mb: float = 0.0,
        error: bool = False,
    ) -> None:
        key = f"{component}:{operation}"
        with self._lock:
            metric = self._metrics.get(key)
            if metric is None:
                metric = ComponentMetric(component=component, operation=operation)
                self._metrics[key] = metric
            metric.record(duration_ms=duration_ms, memory_mb=max(0.0, memory_mb), error=error)

    def summary(self) -> dict[str, Any]:
        with self._lock:
            metrics = [metric.as_dict() for metric in self._metrics.values()]

        metrics.sort(key=lambda item: item["total_duration_ms"], reverse=True)
        return {
            "collected_at": _utc_now_iso(),
            "total_metrics": len(metrics),
            "metrics": metrics[:100],
        }

    def by_component(self, component: str) -> dict[str, Any]:
        with self._lock:
            items = [metric.as_dict() for metric in self._metrics.values() if metric.component == component]
        items.sort(key=lambda item: item["total_duration_ms"], reverse=True)
        return {
            "component": component,
            "operations": items,
        }

    def clear(self) -> None:
        with self._lock:
            self._metrics.clear()


_METRICS_COLLECTOR = MetricsCollector()


def get_metrics_collector() -> MetricsCollector:
    return _METRICS_COLLECTOR


def snapshot_process_memory_mb() -> float:
    return _read_process_memory_mb()


__all__ = [
    "ComponentMetric",
    "MetricsCollector",
    "get_metrics_collector",
    "snapshot_process_memory_mb",
]
