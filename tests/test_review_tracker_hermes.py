import json
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from modules.review_tracker.hermes_runtime import (
    ReviewRunLock,
    RunState,
    SUPPORTED_STATES,
    _duplicate_report_date,
    _run_command,
    build_hermes_execution_proof,
    deterministic_qa,
)


ROOT = Path(__file__).resolve().parents[1]


class HermesRuntimeTests(unittest.TestCase):
    def test_all_required_states_are_supported(self):
        required = {
            "RUN_INITIALIZED", "SCOPE_BUILT", "SCOPE_ANOMALY_REVIEW_REQUIRED", "PREFLIGHT_PASSED", "PREFLIGHT_FAILED",
            "COLLECTING", "NEEDS_HUMAN_VERIFICATION", "COLLECTION_COMPLETE", "QA_PASSED", "DATA_ANOMALY_REVIEW_REQUIRED",
            "QA_FAILED", "REPORT_BUILT", "ARCHIVED", "PUBLISHING", "PUBLISH_FAILED", "SUCCESS",
            "SUCCESS_WITH_PLATFORM_LIMITATION", "TECHNICAL_FAILED", "INTEGRATION_FAILED_DATABASE_MUTATION",
            "SMOKE_TEST_SUCCESS",
        }
        self.assertTrue(required.issubset(SUPPORTED_STATES))

    def test_run_state_checkpoint_survives_resume(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "run_state.json"
            state = RunState(path, "RUN1", "2026-08-13", "DRY_RUN")
            state.checkpoint("scope", {"count": 35})
            state.transition("NEEDS_HUMAN_VERIFICATION", "CAPTCHA", "HUMAN")
            resumed = RunState(path, "RUN1", "2026-08-13", "DRY_RUN")
            self.assertTrue(resumed.completed("scope"))
            self.assertEqual("NEEDS_HUMAN_VERIFICATION", resumed.state)

    def test_resume_rejects_mode_change(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "run_state.json"
            RunState(path, "RUN1", "2026-08-13", "SMOKE_TEST")
            with self.assertRaisesRegex(RuntimeError, "run_state identity"):
                RunState(path, "RUN1", "2026-08-13", "PRODUCTION")

    def test_active_review_lock_blocks_second_run(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "review_tracker.lock"
            with mock.patch.object(ReviewRunLock, "_pid_alive", return_value=True) as pid_alive:
                with ReviewRunLock(path, "RUN1", False):
                    with self.assertRaisesRegex(RuntimeError, "REVIEW_RUN_ALREADY_ACTIVE:RUN1"):
                        ReviewRunLock(path, "RUN2", False).acquire()
            pid_alive.assert_called_once_with(os.getpid())

    def test_nonzero_subprocess_is_captured(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            completed = _run_command(
                [sys.executable, "-c", "raise SystemExit(7)"],
                root,
                root / "failure.json",
                0,
            )
            self.assertEqual(7, completed.returncode)
            evidence = json.loads((root / "failure.json").read_text(encoding="utf-8"))
            self.assertEqual(7, evidence["attempts"][0]["returncode"])

    def test_execution_proof_requires_live_gateway_owned_kanban_task(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "project"
            root.mkdir()
            entrypoint = root / "scripts" / "run_weekly_review_tracker.py"
            entrypoint.parent.mkdir()
            entrypoint.write_text("# fixture\n", encoding="utf-8")
            kanban_db = Path(temporary) / "kanban.db"
            connection = sqlite3.connect(kanban_db)
            try:
                connection.execute(
                    "CREATE TABLE tasks (id TEXT, title TEXT, status TEXT, current_run_id INTEGER, "
                    "worker_pid INTEGER, workspace_kind TEXT, workspace_path TEXT, assignee TEXT)"
                )
                connection.execute(
                    "INSERT INTO tasks VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    ("t_fixture", "review_tracker_weekly", "running", 17, os.getpid(), "dir", str(root), "default"),
                )
                connection.commit()
            finally:
                connection.close()
            (Path(temporary) / "gateway.pid").write_text(
                json.dumps({"pid": os.getpid(), "kind": "hermes-gateway"}),
                encoding="utf-8",
            )
            environment = {
                "HERMES_KANBAN_TASK": "t_fixture",
                "HERMES_KANBAN_RUN_ID": "17",
                "HERMES_KANBAN_BOARD": "default",
                "HERMES_KANBAN_DB": str(kanban_db),
                "HERMES_SESSION_SOURCE": "kanban",
                "HERMES_PROFILE": "default",
                "HERMES_HOME": temporary,
            }
            with mock.patch.dict(os.environ, environment, clear=False), mock.patch.object(
                Path, "cwd", return_value=root
            ), mock.patch.object(ReviewRunLock, "_pid_alive", return_value=True) as pid_alive:
                proof = build_hermes_execution_proof(root, "HERMES_REVIEW_TRACKER_SMOKE_TEST", "2026-08-12T00:00:00Z")
            pid_alive.assert_called_once_with(os.getpid())
            self.assertEqual("HERMES", proof["execution_owner"])
            self.assertEqual("HERMES_GATEWAY_KANBAN_DISPATCHER", proof["execution_source"])
            self.assertEqual("review_tracker_weekly", proof["job_name"])
            self.assertTrue(all(proof["checks"].values()))

    def test_duplicate_formal_report_date_is_blocked(self):
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary) / "existing"
            run.mkdir()
            (run / "run_state.json").write_text(json.dumps({"run_id": "EXISTING", "report_date": "2026-08-13", "mode": "PRODUCTION", "state": "PREFLIGHT_PASSED"}), encoding="utf-8")
            self.assertEqual(run, _duplicate_report_date(Path(temporary), "2026-08-13", "NEW"))

    def test_deterministic_qa_routes_plausibility_to_reviewer(self):
        scope = [{"record_id": "WALMART_A", "platform_code": "WALMART", "internal_sku": "A", "listing_url": "https://www.walmart.com/ip/1"}]
        current = [{"record_id": "WALMART_A", "platform": "Walmart", "sku": "A", "totalReviews": 50, "rating1": 5, "rating2": 5, "rating3": 5, "rating4": 15, "rating5": 20, "avgRating": 2.0}]
        previous = [{"record_id": "WALMART_A", "platform": "Walmart", "sku": "A", "totalReviews": 100, "rating1": 10, "rating2": 10, "rating3": 10, "rating4": 30, "rating5": 40, "avgRating": 4.0}]
        result = deterministic_qa(scope, current, previous, {"review_count_drop_ratio_requires_review": 0.1, "average_rating_change_requires_review": 0.75})
        self.assertTrue(result["passed"])
        self.assertGreaterEqual(len(result["anomalies"]), 2)

    def test_policy_keeps_database_incremental_writes_disabled(self):
        policy = json.loads((ROOT / "config" / "review_tracker_policy.json").read_text(encoding="utf-8"))
        self.assertFalse(policy["database_incremental_write_enabled"])

    def test_scheduler_definition_is_weekly_and_dry_run_by_default(self):
        script = (ROOT / "scripts" / "register_review_tracker_weekly_task.ps1").read_text(encoding="utf-8")
        self.assertIn("Sunseeker Review Tracker Weekly", script)
        self.assertIn("-DaysOfWeek Thursday -At $Time", script)
        self.assertIn("if ($DryRun -or -not $Enable)", script)
        self.assertIn("TASK_SCHEDULER_DRY_RUN_ONLY", script)
        self.assertIn("MultipleInstances IgnoreNew", script)
        self.assertIn("-Mode Production -Resume", script)

    def test_gateway_smoke_entrypoint_is_explicit_and_python_is_absolute(self):
        wrapper = (ROOT / "scripts" / "run_weekly_review_tracker.ps1").read_text(encoding="utf-8")
        cli = (ROOT / "scripts" / "run_weekly_review_tracker.py").read_text(encoding="utf-8")
        runtime = (ROOT / "modules" / "review_tracker" / "hermes_runtime.py").read_text(encoding="utf-8")
        self.assertIn("'SmokeTest'", wrapper)
        self.assertIn("pythoncore-3.14-64\\python.exe", wrapper)
        self.assertIn("PythonPath must be an absolute path", wrapper)
        self.assertIn('"SMOKE_TEST"', cli)
        self.assertIn('"SMOKE_TEST_SUCCESS"', runtime)
        self.assertNotIn('"CODEX"', runtime)


if __name__ == "__main__":
    unittest.main()
