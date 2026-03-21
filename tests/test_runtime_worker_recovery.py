from __future__ import annotations

import logging
import unittest
from datetime import timedelta
from types import SimpleNamespace
from unittest import mock

from backend.runtime import (
    RUNTIME_TRIGGER_CLAIM_LEASE_SECONDS,
    RuntimeEventBus,
    RuntimeTrigger,
    utc_now,
    utc_now_iso,
)
from backend.services.helpers import run_remote_worker_loop


class RuntimeEventBusRecoveryTestCase(unittest.TestCase):
    def test_pending_jobs_requeues_expired_claims(self) -> None:
        bus = RuntimeEventBus()
        job = bus.emit(
            RuntimeTrigger(
                type="inbound_api",
                api_id="orders-webhook",
                event_id="evt_stale_01",
                payload={"order_id": "A100"},
                received_at=utc_now_iso(),
            ),
            job_id="job_stale_01",
            run_id="run_stale_01",
            step_id="step_stale_01",
        )

        bus.claim_next(
            worker_id="worker_old",
            worker_name="Old worker",
            claimed_at=(utc_now() - timedelta(seconds=RUNTIME_TRIGGER_CLAIM_LEASE_SECONDS + 5)).isoformat(),
        )

        pending_jobs = bus.pending_jobs()

        self.assertEqual(len(pending_jobs), 1)
        self.assertEqual(pending_jobs[0].job_id, job.job_id)
        self.assertEqual(pending_jobs[0].status, "pending")
        self.assertIsNone(pending_jobs[0].worker_id)
        self.assertIsNone(pending_jobs[0].claimed_at)

    def test_claim_next_reassigns_expired_claims(self) -> None:
        bus = RuntimeEventBus()
        job = bus.emit(
            RuntimeTrigger(
                type="inbound_api",
                api_id="orders-webhook",
                event_id="evt_stale_02",
                payload={"order_id": "A200"},
                received_at=utc_now_iso(),
            ),
            job_id="job_stale_02",
            run_id="run_stale_02",
            step_id="step_stale_02",
        )

        bus.claim_next(
            worker_id="worker_old",
            worker_name="Old worker",
            claimed_at=(utc_now() - timedelta(seconds=RUNTIME_TRIGGER_CLAIM_LEASE_SECONDS + 5)).isoformat(),
        )

        reclaimed_job = bus.claim_next(
            worker_id="worker_new",
            worker_name="New worker",
            claimed_at=utc_now_iso(),
        )

        self.assertIsNotNone(reclaimed_job)
        self.assertEqual(reclaimed_job.job_id, job.job_id)
        self.assertEqual(reclaimed_job.status, "claimed")
        self.assertEqual(reclaimed_job.worker_id, "worker_new")
        self.assertEqual(reclaimed_job.worker_name, "New worker")


class RemoteWorkerLoopRecoveryTestCase(unittest.TestCase):
    def test_remote_worker_loop_logs_poll_failures(self) -> None:
        app = SimpleNamespace(state=SimpleNamespace(logger=mock.Mock()))
        stop_event = mock.Mock()
        stop_event.is_set.side_effect = [False, False, True]
        stop_event.wait.return_value = True

        failing_client = mock.MagicMock()
        failing_client.__enter__.return_value = failing_client
        failing_client.post.side_effect = RuntimeError("coordinator unreachable")

        with (
            mock.patch("backend.services.helpers.get_local_worker_id", return_value="worker_remote_01"),
            mock.patch("backend.services.helpers.get_local_worker_name", return_value="Remote Worker"),
            mock.patch("backend.services.helpers.get_runtime_hostname", return_value="remote-worker.local"),
            mock.patch("backend.services.helpers.get_local_worker_address", return_value="10.0.0.20"),
            mock.patch("backend.services.helpers.httpx.Client", return_value=failing_client),
            mock.patch("backend.services.helpers.write_application_log") as write_application_log,
        ):
            run_remote_worker_loop(app, stop_event, "http://coordinator.test")

        write_application_log.assert_called_once()
        args, kwargs = write_application_log.call_args
        self.assertIs(args[0], app.state.logger)
        self.assertEqual(args[1], logging.WARNING)
        self.assertEqual(args[2], "remote_worker_poll_failed")
        self.assertEqual(kwargs["coordinator_url"], "http://coordinator.test")
        self.assertEqual(kwargs["worker_id"], "worker_remote_01")
        self.assertIn("coordinator unreachable", kwargs["error"])


if __name__ == "__main__":
    unittest.main()
