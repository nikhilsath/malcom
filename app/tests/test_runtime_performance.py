"""Micro-benchmark tests for RuntimeEventBus performance."""
from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta

from backend.runtime import (
    RUNTIME_TRIGGER_CLAIM_LEASE_SECONDS,
    RuntimeEventBus,
    RuntimeTrigger,
)


def _make_trigger(n: int) -> RuntimeTrigger:
    return RuntimeTrigger(
        type="inbound",
        api_id=f"api-{n}",
        event_id=f"evt-{n}",
        payload={"n": n},
        received_at=datetime.now(UTC).isoformat(),
    )


def test_runtime_eventbus_requeue_performance() -> None:
    """Enqueue N jobs, claim half, then measure _requeue_expired_claims latency."""
    bus = RuntimeEventBus(max_history=100, max_jobs=6000)
    n_jobs = 5000

    # Enqueue jobs
    for i in range(n_jobs):
        bus.emit(_make_trigger(i), job_id=f"job-{i}", run_id=f"run-{i}", step_id=f"step-{i}")

    # Claim every other job so roughly half are "claimed"
    claimed_at = (datetime.now(UTC) - timedelta(seconds=RUNTIME_TRIGGER_CLAIM_LEASE_SECONDS + 5)).isoformat()
    with bus._lock:
        for idx, job in enumerate(bus._jobs):
            if idx % 2 == 0:
                from backend.runtime import RuntimeTriggerJob
                bus._jobs[idx] = RuntimeTriggerJob(
                    job_id=job.job_id,
                    run_id=job.run_id,
                    step_id=job.step_id,
                    trigger=job.trigger,
                    status="claimed",
                    worker_id="test-worker",
                    worker_name="test",
                    claimed_at=claimed_at,
                    completed_at=None,
                )

    # Measure pending_jobs() which calls _requeue_expired_claims_locked internally
    start = time.perf_counter()
    jobs = bus.pending_jobs()
    elapsed_ms = (time.perf_counter() - start) * 1000

    assert len(jobs) == n_jobs, f"Expected {n_jobs} pending jobs after requeue, got {len(jobs)}"
    # Should complete in well under 500 ms on any reasonable machine
    assert elapsed_ms < 500, f"pending_jobs() took {elapsed_ms:.1f} ms, expected < 500 ms"


def test_runtime_eventbus_claim_next_performance() -> None:
    """Measure claim_next() latency with a full queue of pending jobs."""
    bus = RuntimeEventBus(max_history=100, max_jobs=5000)
    n_jobs = 5000

    for i in range(n_jobs):
        bus.emit(_make_trigger(i), job_id=f"job-{i}", run_id=f"run-{i}", step_id=f"step-{i}")

    claimed_at = datetime.now(UTC).isoformat()

    start = time.perf_counter()
    job = bus.claim_next(worker_id="w1", worker_name="worker-1", claimed_at=claimed_at)
    elapsed_ms = (time.perf_counter() - start) * 1000

    assert job is not None
    assert job.status == "claimed"
    assert elapsed_ms < 100, f"claim_next() took {elapsed_ms:.1f} ms, expected < 100 ms"
