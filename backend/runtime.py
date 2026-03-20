from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from threading import Event, Lock, Thread
from typing import Any, Callable


@dataclass(frozen=True)
class RuntimeTrigger:
    type: str
    api_id: str
    event_id: str
    payload: Any
    received_at: str


@dataclass(frozen=True)
class RuntimeTriggerJob:
    job_id: str
    run_id: str
    step_id: str
    trigger: RuntimeTrigger
    status: str
    worker_id: str | None
    worker_name: str | None
    claimed_at: str | None
    completed_at: str | None


@dataclass(frozen=True)
class RegisteredWorker:
    worker_id: str
    name: str
    hostname: str
    address: str
    capabilities: tuple[str, ...]
    status: str
    created_at: str
    updated_at: str
    last_seen_at: str


class RuntimeEventBus:
    def __init__(self, max_history: int = 10000, max_jobs: int = 5000) -> None:
        self._lock = Lock()
        self._history: deque[RuntimeTrigger] = deque(maxlen=max_history)
        self._jobs: deque[RuntimeTriggerJob] = deque(maxlen=max_jobs)
        self._workers: dict[str, RegisteredWorker] = {}
        self._queue_paused = False
        self._queue_updated_at: str | None = None

    def emit(self, trigger: RuntimeTrigger, *, job_id: str, run_id: str, step_id: str) -> RuntimeTriggerJob:
        with self._lock:
            job = RuntimeTriggerJob(
                job_id=job_id,
                run_id=run_id,
                step_id=step_id,
                trigger=trigger,
                status="pending",
                worker_id=None,
                worker_name=None,
                claimed_at=None,
                completed_at=None,
            )
            self._jobs.append(job)
            return job

    def record_history(self, trigger: RuntimeTrigger) -> None:
        with self._lock:
            self._history.append(trigger)

    def history(self) -> list[RuntimeTrigger]:
        with self._lock:
            return list(self._history)

    def pending_jobs(self) -> list[RuntimeTriggerJob]:
        with self._lock:
            return [job for job in self._jobs if job.status in {"pending", "claimed"}]

    def claim_next(self, *, worker_id: str, worker_name: str, claimed_at: str) -> RuntimeTriggerJob | None:
        with self._lock:
            if self._queue_paused:
                return None

            for index, job in enumerate(self._jobs):
                if job.status != "pending":
                    continue

                claimed_job = RuntimeTriggerJob(
                    job_id=job.job_id,
                    run_id=job.run_id,
                    step_id=job.step_id,
                    trigger=job.trigger,
                    status="claimed",
                    worker_id=worker_id,
                    worker_name=worker_name,
                    claimed_at=claimed_at,
                    completed_at=None,
                )
                self._jobs[index] = claimed_job
                return claimed_job

            return None

    def set_queue_paused(self, paused: bool) -> dict[str, Any]:
        with self._lock:
            self._queue_paused = paused
            self._queue_updated_at = utc_now_iso()
            return {
                "is_paused": self._queue_paused,
                "status": "paused" if self._queue_paused else "running",
                "updated_at": self._queue_updated_at,
            }

    def queue_status(self) -> dict[str, Any]:
        with self._lock:
            updated_at = self._queue_updated_at or utc_now_iso()
            return {
                "is_paused": self._queue_paused,
                "status": "paused" if self._queue_paused else "running",
                "updated_at": updated_at,
            }

    def get_job(self, job_id: str) -> RuntimeTriggerJob | None:
        with self._lock:
            for job in self._jobs:
                if job.job_id == job_id:
                    return job
            return None

    def complete_job(self, *, job_id: str, worker_id: str, status_value: str, completed_at: str) -> RuntimeTriggerJob | None:
        with self._lock:
            for index, job in enumerate(self._jobs):
                if job.job_id != job_id or job.worker_id != worker_id:
                    continue

                completed_job = RuntimeTriggerJob(
                    job_id=job.job_id,
                    run_id=job.run_id,
                    step_id=job.step_id,
                    trigger=job.trigger,
                    status=status_value,
                    worker_id=job.worker_id,
                    worker_name=job.worker_name,
                    claimed_at=job.claimed_at,
                    completed_at=completed_at,
                )
                self._jobs[index] = completed_job
                return completed_job

            return None

    def register_worker(
        self,
        *,
        worker_id: str,
        name: str,
        hostname: str,
        address: str,
        capabilities: list[str],
        seen_at: str,
    ) -> RegisteredWorker:
        with self._lock:
            existing = self._workers.get(worker_id)
            worker = RegisteredWorker(
                worker_id=worker_id,
                name=name,
                hostname=hostname,
                address=address,
                capabilities=tuple(capabilities),
                status="healthy",
                created_at=existing.created_at if existing else seen_at,
                updated_at=seen_at,
                last_seen_at=seen_at,
            )
            self._workers[worker_id] = worker
            return worker

    def list_workers(self) -> list[RegisteredWorker]:
        with self._lock:
            return list(self._workers.values())

    def clear(self) -> None:
        with self._lock:
            self._history.clear()
            self._jobs.clear()
            self._workers.clear()
            self._queue_paused = False
            self._queue_updated_at = utc_now_iso()


runtime_event_bus = RuntimeEventBus()


def utc_now() -> datetime:
    return datetime.now(UTC)


def utc_now_iso() -> str:
    return utc_now().isoformat()


def parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None

    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def next_daily_run_at(scheduled_time: str, now: datetime | None = None) -> str:
    reference = now or utc_now()
    hour, minute = scheduled_time.split(":")
    candidate = reference.replace(hour=int(hour), minute=int(minute), second=0, microsecond=0)
    if candidate <= reference:
        candidate += timedelta(days=1)
    return candidate.isoformat()


@dataclass(frozen=True)
class RuntimeExecutionResult:
    status: str
    response_summary: str | None = None
    detail: dict[str, Any] | None = None
    output: Any = None


class RuntimeScheduler:
    def __init__(self) -> None:
        self._lock = Lock()
        self._stop_event = Event()
        self._thread: Thread | None = None
        self._last_tick_started_at: str | None = None
        self._last_tick_finished_at: str | None = None
        self._last_error: str | None = None
        self._registered_jobs: list[dict[str, Any]] = []

    def start(self, tick: Callable[[], None], *, interval_seconds: int = 30) -> None:
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return

            self._stop_event.clear()

            def run() -> None:
                while not self._stop_event.wait(interval_seconds):
                    started_at = utc_now_iso()
                    with self._lock:
                        self._last_tick_started_at = started_at
                    try:
                        tick()
                        with self._lock:
                            self._last_tick_finished_at = utc_now_iso()
                            self._last_error = None
                    except Exception as error:  # pragma: no cover - defensive scheduler guard
                        with self._lock:
                            self._last_tick_finished_at = utc_now_iso()
                            self._last_error = str(error)

            self._thread = Thread(target=run, name="malcom-runtime-scheduler", daemon=True)
            self._thread.start()

    def stop(self) -> None:
        with self._lock:
            self._stop_event.set()
            thread = self._thread
            self._thread = None
        if thread is not None:
            thread.join(timeout=1)

    def update_jobs(self, jobs: list[dict[str, Any]]) -> None:
        with self._lock:
            self._registered_jobs = jobs

    def status(self) -> dict[str, Any]:
        with self._lock:
            active = self._thread is not None and self._thread.is_alive()
            return {
                "active": active,
                "last_tick_started_at": self._last_tick_started_at,
                "last_tick_finished_at": self._last_tick_finished_at,
                "last_error": self._last_error,
                "job_count": len(self._registered_jobs),
            }

    def jobs(self) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(job) for job in self._registered_jobs]


runtime_scheduler = RuntimeScheduler()
