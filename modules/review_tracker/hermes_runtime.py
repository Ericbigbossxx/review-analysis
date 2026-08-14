"""Hermes-style weekly orchestration for the existing Review Tracker.

This module owns run state, checkpoints, scope, retry, resume and publication
coordination.  Collection and report calculations remain in the existing
Review Tracker scripts.
"""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import subprocess
import sys
import time
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from modules.review_tracker.preflight import run_preflight
from modules.review_tracker.scope import (
    build_frozen_scope,
    canonical_scope_row,
    diff_scopes,
    evaluate_scope_gate,
    find_previous_successful_weekly_run,
    read_json,
    scope_hash,
    sha256,
    write_json_atomic,
)


SUPPORTED_STATES = {
    "RUN_INITIALIZED",
    "SCOPE_BUILT",
    "SCOPE_ANOMALY_REVIEW_REQUIRED",
    "PREFLIGHT_PASSED",
    "PREFLIGHT_FAILED",
    "COLLECTING",
    "NEEDS_HUMAN_VERIFICATION",
    "COLLECTION_COMPLETE",
    "QA_PASSED",
    "DATA_ANOMALY_REVIEW_REQUIRED",
    "QA_FAILED",
    "REPORT_BUILT",
    "ARCHIVED",
    "PUBLISHING",
    "PUBLISH_FAILED",
    "SUCCESS",
    "SUCCESS_WITH_PLATFORM_LIMITATION",
    "TECHNICAL_FAILED",
    "INTEGRATION_FAILED_DATABASE_MUTATION",
    "SUPERVISED_DRY_RUN_COMPLETE",
    "SMOKE_TEST_SUCCESS",
}
TERMINAL_STATES = {
    "SUCCESS",
    "SUCCESS_WITH_PLATFORM_LIMITATION",
    "TECHNICAL_FAILED",
    "INTEGRATION_FAILED_DATABASE_MUTATION",
    "PUBLISH_FAILED",
    "SUPERVISED_DRY_RUN_COMPLETE",
    "SMOKE_TEST_SUCCESS",
}
HUMAN_MARKERS = ("CAPTCHA", "ROBOT CHECK", "ROBOT_CHECK", "NEEDS_HUMAN_VERIFICATION")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class RunState:
    def __init__(self, path: Path, run_id: str, report_date: str, mode: str) -> None:
        self.path = path
        if path.exists():
            self.data = read_json(path)
            if (
                self.data.get("run_id") != run_id
                or self.data.get("report_date") != report_date
                or self.data.get("mode") != mode
            ):
                raise RuntimeError("run_state identity does not match requested run")
        else:
            self.data = {
                "run_id": run_id,
                "report_date": report_date,
                "report_type": "WEEKLY_REVIEW",
                "mode": mode,
                "state": "RUN_INITIALIZED",
                "created_at": utc_now(),
                "updated_at": utc_now(),
                "required_owner": "HERMES",
                "reason": None,
                "checkpoints": {},
                "history": [{"state": "RUN_INITIALIZED", "at": utc_now(), "reason": "run state created"}],
            }
            self.save()

    @property
    def state(self) -> str:
        return str(self.data["state"])

    def save(self) -> None:
        self.data["updated_at"] = utc_now()
        write_json_atomic(self.path, self.data)

    def transition(self, state: str, reason: str | None = None, owner: str = "HERMES") -> None:
        if state not in SUPPORTED_STATES:
            raise ValueError(f"unsupported run state: {state}")
        self.data.update({"state": state, "reason": reason, "required_owner": owner})
        self.data["history"].append({"state": state, "at": utc_now(), "reason": reason, "owner": owner})
        self.save()

    def checkpoint(self, name: str, detail: Any = None) -> None:
        self.data["checkpoints"][name] = {"status": "COMPLETED", "completed_at": utc_now(), "detail": detail}
        self.save()

    def completed(self, name: str) -> bool:
        return self.data.get("checkpoints", {}).get(name, {}).get("status") == "COMPLETED"


class ReviewRunLock:
    def __init__(self, path: Path, run_id: str, resume: bool) -> None:
        self.path = path
        self.run_id = run_id
        self.resume = resume
        self.acquired = False

    @staticmethod
    def _pid_alive(pid: int) -> bool:
        if pid <= 0:
            return False
        if os.name == "nt":
            import ctypes
            from ctypes import wintypes

            process_query_limited_information = 0x1000
            still_active = 259
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
            kernel32.OpenProcess.restype = wintypes.HANDLE
            kernel32.GetExitCodeProcess.argtypes = (wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD))
            kernel32.GetExitCodeProcess.restype = wintypes.BOOL
            kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
            kernel32.CloseHandle.restype = wintypes.BOOL
            handle = kernel32.OpenProcess(process_query_limited_information, False, pid)
            if not handle:
                return False
            try:
                exit_code = wintypes.DWORD()
                if not kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
                    return False
                return exit_code.value == still_active
            finally:
                kernel32.CloseHandle(handle)
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False

    def acquire(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            existing = read_json(self.path)
            if self._pid_alive(int(existing.get("pid") or 0)):
                raise RuntimeError(f"REVIEW_RUN_ALREADY_ACTIVE:{existing.get('run_id')}")
            if not self.resume or existing.get("run_id") != self.run_id:
                raise RuntimeError(f"STALE_REVIEW_LOCK_REQUIRES_REVIEW:{existing.get('run_id')}")
            stale = self.path.with_name(f"{self.path.name}.stale.{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            self.path.replace(stale)
        payload = {"run_id": self.run_id, "pid": os.getpid(), "started_at": utc_now(), "hostname": os.environ.get("COMPUTERNAME")}
        descriptor = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        try:
            os.write(descriptor, (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
        finally:
            os.close(descriptor)
        self.acquired = True

    def release(self) -> None:
        if not self.acquired or not self.path.exists():
            return
        try:
            owner = read_json(self.path).get("run_id")
        except (ValueError, json.JSONDecodeError):
            owner = None
        if owner == self.run_id:
            self.path.unlink()
        self.acquired = False

    def __enter__(self) -> "ReviewRunLock":
        self.acquire()
        return self

    def __exit__(self, *_: object) -> None:
        self.release()


def _hash_tree(root: Path) -> dict[str, str]:
    if not root.exists():
        return {}
    return {str(path.relative_to(root)): sha256(path) for path in sorted(root.rglob("*")) if path.is_file()}


def _database_snapshot(project_root: Path) -> dict[str, Any]:
    database = project_root / "database" / "tracker.db"
    with sqlite3.connect(f"file:{database.resolve().as_posix()}?mode=ro", uri=True) as connection:
        counts = {
            table: int(connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])
            for table in ("reviews", "review_snapshots", "review_changes")
        }
        integrity = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
        foreign_key_errors = len(connection.execute("PRAGMA foreign_key_check").fetchall())
    return {
        "sha256": sha256(database),
        "counts": counts,
        "integrity_check": integrity,
        "foreign_key_errors": foreign_key_errors,
    }


def _optional_file_hash(path: Path) -> str | None:
    return sha256(path) if path.is_file() else None


def _git_control_snapshot(project_root: Path) -> dict[str, str | None]:
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=project_root,
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    index = subprocess.run(
        ["git", "rev-parse", "--git-path", "index"],
        cwd=project_root,
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    index_path = Path(index.stdout.strip()) if index.returncode == 0 and index.stdout.strip() else None
    if index_path is not None and not index_path.is_absolute():
        index_path = project_root / index_path
    return {
        "head": head.stdout.strip() if head.returncode == 0 else None,
        "index_sha256": _optional_file_hash(index_path) if index_path is not None else None,
    }


def _protected_snapshot(project_root: Path) -> dict[str, Any]:
    return {
        "database": sha256(project_root / "database" / "tracker.db"),
        "archive_manifest": sha256(project_root / "archive_manifest.json"),
        "index": sha256(project_root / "index.html"),
        "reports": _hash_tree(project_root / "reports"),
        "archive": _hash_tree(project_root / "archive"),
        "outputs_latest": _hash_tree(project_root / "outputs" / "latest"),
        "git": _git_control_snapshot(project_root),
    }


def _find_gateway_pid_file(hermes_home: Path, kanban_db: Path) -> Path | None:
    candidates = [hermes_home / "gateway.pid"]
    candidates.extend(parent / "gateway.pid" for parent in kanban_db.parents)
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    return None


def build_hermes_execution_proof(project_root: Path, run_id: str, started_at: str) -> dict[str, Any]:
    """Validate that a live Gateway-owned Kanban run launched this process."""

    task_id = str(os.environ.get("HERMES_KANBAN_TASK") or "").strip()
    task_run_id = str(os.environ.get("HERMES_KANBAN_RUN_ID") or "").strip()
    board = str(os.environ.get("HERMES_KANBAN_BOARD") or "").strip()
    session_source = str(os.environ.get("HERMES_SESSION_SOURCE") or "").strip()
    profile = str(os.environ.get("HERMES_PROFILE") or "default").strip() or "default"
    kanban_db_raw = str(os.environ.get("HERMES_KANBAN_DB") or "").strip()
    hermes_home_raw = str(os.environ.get("HERMES_HOME") or "").strip()
    if not task_id or not task_run_id or not board or not kanban_db_raw or session_source != "kanban":
        raise RuntimeError("HERMES_GATEWAY_EXECUTION_NOT_PROVEN:missing Kanban dispatcher environment")

    kanban_db = Path(kanban_db_raw).resolve()
    hermes_home = Path(hermes_home_raw).resolve() if hermes_home_raw else kanban_db.parent
    connection = sqlite3.connect(f"file:{kanban_db.as_posix()}?mode=ro", uri=True)
    try:
        connection.row_factory = sqlite3.Row
        task = connection.execute(
            "SELECT id, title, status, current_run_id, worker_pid, workspace_kind, workspace_path, assignee "
            "FROM tasks WHERE id = ?",
            (task_id,),
        ).fetchone()
    finally:
        connection.close()
    if task is None:
        raise RuntimeError(f"HERMES_GATEWAY_EXECUTION_NOT_PROVEN:unknown task {task_id}")

    gateway_pid_file = _find_gateway_pid_file(hermes_home, kanban_db)
    if gateway_pid_file is None:
        raise RuntimeError("HERMES_GATEWAY_EXECUTION_NOT_PROVEN:gateway.pid not found")
    gateway = read_json(gateway_pid_file)
    gateway_pid = int(gateway.get("pid") or 0)
    gateway_alive = ReviewRunLock._pid_alive(gateway_pid)
    task_workspace = Path(str(task["workspace_path"] or "")).resolve()
    checks = {
        "gateway_kind": gateway.get("kind") == "hermes-gateway",
        "gateway_alive": gateway_alive,
        "task_title": task["title"] == "review_tracker_weekly",
        "task_running": task["status"] == "running",
        "task_run_id": str(task["current_run_id"]) == task_run_id,
        "task_worker_pid": int(task["worker_pid"] or 0) > 0,
        "task_workspace_kind": task["workspace_kind"] == "dir",
        "task_workspace": task_workspace == project_root.resolve(),
        "process_working_directory": Path.cwd().resolve() == project_root.resolve(),
        "python_is_absolute": Path(sys.executable).is_absolute(),
        "runtime_entrypoint_exists": (project_root / "scripts" / "run_weekly_review_tracker.py").is_file(),
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    if failed:
        raise RuntimeError(f"HERMES_GATEWAY_EXECUTION_NOT_PROVEN:failed checks={failed}")
    return {
        "execution_owner": "HERMES",
        "execution_source": "HERMES_GATEWAY_KANBAN_DISPATCHER",
        "gateway_instance": f"{profile}:pid={gateway_pid}",
        "job_name": "review_tracker_weekly",
        "run_id": run_id,
        "started_at": started_at,
        "working_directory": str(project_root.resolve()),
        "python_executable": str(Path(sys.executable).resolve()),
        "runtime_entrypoint": str((project_root / "scripts" / "run_weekly_review_tracker.py").resolve()),
        "hermes_board": board,
        "hermes_task_id": task_id,
        "hermes_task_run_id": task_run_id,
        "hermes_worker_pid": int(task["worker_pid"]),
        "gateway_pid_file": str(gateway_pid_file),
        "checks": checks,
    }


def _backup_inputs(project_root: Path, run_id: str) -> dict[str, Any]:
    backup_dir = project_root / "backups" / "review_tracker_weekly_pre_run" / run_id
    backup_dir.mkdir(parents=True, exist_ok=True)
    sources = [
        project_root / "database" / "tracker.db",
        project_root / "config" / "listing_master.xlsx",
        project_root / "config" / "review_tracker_policy.json",
    ]
    files: list[dict[str, Any]] = []
    for source in sources:
        destination = backup_dir / source.name
        if destination.exists() and sha256(destination) != sha256(source):
            raise RuntimeError(f"existing backup differs from current protected input: {destination}")
        if not destination.exists():
            shutil.copy2(source, destination)
        files.append({"source": str(source), "backup": str(destination), "sha256": sha256(source), "verified": sha256(source) == sha256(destination)})
    manifest = {"run_id": run_id, "created_at": utc_now(), "files": files}
    write_json_atomic(backup_dir / "sha256_manifest.json", manifest)
    if not all(item["verified"] for item in files):
        raise RuntimeError("pre-run backup verification failed")
    return manifest


def _run_command(command: list[str], cwd: Path, log_path: Path, retries: int) -> subprocess.CompletedProcess[str]:
    attempts: list[dict[str, Any]] = []
    for attempt in range(1, retries + 2):
        completed = subprocess.run(command, cwd=cwd, text=True, capture_output=True, encoding="utf-8", errors="replace")
        attempts.append({"attempt": attempt, "returncode": completed.returncode, "stdout": completed.stdout, "stderr": completed.stderr})
        write_json_atomic(log_path, {"command": command, "attempts": attempts})
        if completed.returncode == 0:
            return completed
        combined = f"{completed.stdout}\n{completed.stderr}".upper()
        if any(marker in combined for marker in HUMAN_MARKERS):
            return completed
        if attempt <= retries:
            time.sleep(min(attempt, 2))
    return completed


def _summary_key(row: dict[str, Any]) -> str:
    if row.get("record_id"):
        return str(row["record_id"])
    platform = str(row.get("platform") or "").upper().replace("HOMEDEPOT", "THD").replace("LOWES", "LOWES")
    return f"{platform}_{str(row.get('sku') or '').strip()}"


def deterministic_qa(
    current_scope: list[dict[str, Any]],
    current_summary: list[dict[str, Any]],
    previous_summary: list[dict[str, Any]] | None,
    policy: dict[str, Any],
) -> dict[str, Any]:
    expected_ids = {canonical_scope_row(row)["record_id"] for row in current_scope}
    current_map = {_summary_key(row): row for row in current_summary}
    failures: list[dict[str, Any]] = []
    anomalies: list[dict[str, Any]] = []
    duplicate_count = len(current_summary) - len(current_map)
    if duplicate_count:
        failures.append({"code": "DUPLICATE_CURRENT_SUMMARY_ROWS", "count": duplicate_count})
    missing = sorted(expected_ids - current_map.keys())
    if missing:
        failures.append({"code": "MISSING_CURRENT_SCOPE_ROWS", "record_ids": missing})
    extra = sorted(current_map.keys() - expected_ids)
    if extra:
        failures.append({"code": "OUT_OF_SCOPE_CURRENT_ROWS", "record_ids": extra})
    for record_id, row in current_map.items():
        available = row.get("dataAvailable", True) is not False and row.get("totalReviews") is not None
        if not available:
            if not str(row.get("availabilityStatus") or "").strip():
                failures.append({"code": "UNAVAILABLE_WITHOUT_STATUS", "record_id": record_id})
            continue
        total = int(row.get("totalReviews") or 0)
        ratings = [int(row.get(f"rating{star}") or 0) for star in range(1, 6)]
        if total < 0 or any(value < 0 for value in ratings) or sum(ratings) != total:
            failures.append({"code": "RATING_RECONCILIATION_FAILED", "record_id": record_id, "total": total, "rating_sum": sum(ratings)})
    previous_map = {_summary_key(row): row for row in (previous_summary or [])}
    drop_threshold = float(policy.get("review_count_drop_ratio_requires_review", 0.1))
    rating_threshold = float(policy.get("average_rating_change_requires_review", 0.75))
    for record_id in sorted(expected_ids & previous_map.keys() & current_map.keys()):
        current = current_map[record_id]
        previous = previous_map[record_id]
        if current.get("dataAvailable", True) is False or previous.get("dataAvailable", True) is False:
            continue
        current_total = current.get("totalReviews")
        previous_total = previous.get("totalReviews")
        if current_total is not None and previous_total and int(current_total) < int(previous_total):
            ratio = (int(previous_total) - int(current_total)) / int(previous_total)
            if ratio >= drop_threshold:
                anomalies.append({"code": "TOTAL_REVIEWS_DROPPED", "record_id": record_id, "ratio": ratio})
        if current.get("avgRating") is not None and previous.get("avgRating") is not None:
            change = abs(float(current["avgRating"]) - float(previous["avgRating"]))
            if change >= rating_threshold:
                anomalies.append({"code": "AVERAGE_RATING_CHANGED", "record_id": record_id, "change": change})
    return {"passed": not failures, "failures": failures, "anomalies": anomalies, "scope_count": len(expected_ids)}


def _duplicate_report_date(runs_root: Path, report_date: str, run_id: str) -> Path | None:
    if not runs_root.exists():
        return None
    for state_path in runs_root.glob("*/run_state.json"):
        data = read_json(state_path)
        if data.get("run_id") != run_id and data.get("mode") == "PRODUCTION" and data.get("report_date") == report_date:
            return state_path.parent
    return None


def _action_result(state: RunState) -> dict[str, Any]:
    return {
        "status": "REVIEW_TRACKER_ACTION_REQUIRED",
        "run_id": state.data["run_id"],
        "state": state.state,
        "reason": state.data.get("reason"),
        "completed": sorted(name for name, value in state.data.get("checkpoints", {}).items() if value.get("status") == "COMPLETED"),
        "pending": "Resume the same run after the required owner resolves the gate.",
        "required_owner": state.data.get("required_owner"),
    }


def run_weekly(
    project_root: Path,
    run_id: str,
    report_date: str,
    mode: str = "DRY_RUN",
    resume: bool = False,
    scope_decision: str | None = None,
    data_decision: str | None = None,
) -> dict[str, Any]:
    root = project_root.resolve()
    mode = mode.upper()
    if mode not in {"DRY_RUN", "SMOKE_TEST", "PRODUCTION"}:
        raise ValueError("mode must be DRY_RUN, SMOKE_TEST or PRODUCTION")
    run_dir = root / "runs" / run_id
    if run_dir.exists() and not resume:
        raise RuntimeError(f"run directory already exists; use --resume for {run_id}")
    duplicate = _duplicate_report_date(root / "runs", report_date, run_id) if mode == "PRODUCTION" else None
    if duplicate:
        raise RuntimeError(f"formal run already exists for report_date {report_date}: {duplicate.name}")
    run_dir.mkdir(parents=True, exist_ok=True)
    state = RunState(run_dir / "run_state.json", run_id, report_date, mode)
    if state.state in {"SUCCESS", "SUCCESS_WITH_PLATFORM_LIMITATION"} and (run_dir / "final_status.json").exists():
        return {**read_json(run_dir / "final_status.json"), "run_id": run_id, "state": state.state, "idempotent_resume": True}
    if state.state == "SUPERVISED_DRY_RUN_COMPLETE" and (run_dir / "supervised_weekly_dry_run_audit.json").exists():
        audit = read_json(run_dir / "supervised_weekly_dry_run_audit.json")
        return {"status": audit["readiness"], "run_id": run_id, "state": state.state, "audit": audit, "idempotent_resume": True}
    if state.state == "SMOKE_TEST_SUCCESS" and (run_dir / "hermes_smoke_test_audit.json").exists():
        audit = read_json(run_dir / "hermes_smoke_test_audit.json")
        return {"status": "SMOKE_TEST_SUCCESS", "run_id": run_id, "state": state.state, "audit": audit, "idempotent_resume": True}
    lock = ReviewRunLock(root / "runtime" / "review_tracker.lock", run_id, resume)
    policy = read_json(root / "config" / "review_tracker_policy.json")
    protected_before = _protected_snapshot(root)
    database_before = _database_snapshot(root)
    with lock:
        try:
            execution_proof: dict[str, Any] | None = None
            if mode == "SMOKE_TEST":
                if not state.completed("execution_owner"):
                    execution_proof = build_hermes_execution_proof(root, run_id, str(state.data["created_at"]))
                    write_json_atomic(run_dir / "execution_owner_proof.json", execution_proof)
                    state.checkpoint(
                        "execution_owner",
                        {
                            "owner": execution_proof["execution_owner"],
                            "source": execution_proof["execution_source"],
                            "hermes_task_id": execution_proof["hermes_task_id"],
                            "hermes_task_run_id": execution_proof["hermes_task_run_id"],
                        },
                    )
                else:
                    execution_proof = read_json(run_dir / "execution_owner_proof.json")
            if not state.completed("scope"):
                current_scope, manifest = build_frozen_scope(root / "config" / "listing_master.xlsx", run_dir, run_id, report_date)
                previous_dir = find_previous_successful_weekly_run(root / "runs", report_date, exclude_run_id=run_id)
                previous_scope = read_json(previous_dir / "listing_sources.json") if previous_dir else []
                scope_diff = diff_scopes(current_scope, previous_scope)
                gate = evaluate_scope_gate(scope_diff, current_scope, previous_scope, policy)
                scope_payload = {
                    "run_id": run_id,
                    "report_date": report_date,
                    "previous_successful_run_id": previous_dir.name if previous_dir else None,
                    "current_scope_hash": manifest["scope_hash"],
                    "previous_scope_hash": scope_hash(previous_scope) if previous_scope else None,
                    "summary": scope_diff["summary"],
                    "categories": scope_diff["categories"],
                    "gate": gate,
                }
                write_json_atomic(run_dir / "scope_diff.json", scope_payload)
                state.checkpoint("scope", {"count": len(current_scope), "previous_run": previous_dir.name if previous_dir else None})
                state.transition("SCOPE_BUILT")
            current_scope = read_json(run_dir / "listing_sources.json")
            scope_payload = read_json(run_dir / "scope_diff.json")
            previous_id = scope_payload.get("previous_successful_run_id")
            previous_dir = root / "runs" / previous_id if previous_id else None
            if scope_payload["gate"]["requires_review"] and not state.completed("scope_review"):
                request = {
                    "gate": "SCOPE_ANOMALY",
                    "allowed_decisions": ["APPROVE_RUN", "HOLD_RUN"],
                    "scope_diff": str(run_dir / "scope_diff.json"),
                    "reasons": scope_payload["gate"]["reasons"],
                }
                write_json_atomic(run_dir / "sol_scope_review_request.json", request)
                if scope_decision not in {"APPROVE_RUN", "HOLD_RUN"}:
                    state.transition("SCOPE_ANOMALY_REVIEW_REQUIRED", "Deterministic scope gate requires Sol review.", "SOL")
                    return _action_result(state)
                write_json_atomic(run_dir / "sol_scope_review_decision.json", {"decision": scope_decision, "decided_at": utc_now()})
                if scope_decision == "HOLD_RUN":
                    state.transition("SCOPE_ANOMALY_REVIEW_REQUIRED", "Sol reviewer held the run.", "SOL")
                    return _action_result(state)
                state.checkpoint("scope_review", {"decision": scope_decision})

            if not state.completed("backup"):
                state.checkpoint("backup", _backup_inputs(root, run_id))
            if not state.completed("preflight"):
                preflight = run_preflight(
                    root,
                    run_dir / "listing_sources.json",
                    scope_manifest_path=run_dir / "scope_manifest.json",
                    expected_lock_run_id=run_id,
                )
                write_json_atomic(run_dir / "preflight_result.json", preflight)
                if preflight["status"] != "PREFLIGHT_PASSED":
                    state.transition("PREFLIGHT_FAILED", "Read-only preflight failed.", "HERMES")
                    return _action_result(state)
                state.checkpoint("preflight", {"status": preflight["status"]})
                state.transition("PREFLIGHT_PASSED")

            if mode in {"DRY_RUN", "SMOKE_TEST"}:
                required = (
                    [
                        "scripts/run_review_tracker_bv.py",
                        "scripts/run_review_tracker_walmart_bv.py",
                        "build_biweekly_report_data.ps1",
                        "scripts/build_review_period_comparison.py",
                        "build_visual_dashboard.ps1",
                        "update_archive_portal.ps1",
                        "scripts/register_review_tracker_weekly_task.ps1",
                    ]
                    if mode == "DRY_RUN"
                    else [
                        "scripts/run_weekly_review_tracker.ps1",
                        "scripts/run_weekly_review_tracker.py",
                        "modules/review_tracker/hermes_runtime.py",
                    ]
                )
                missing = [path for path in required if not (root / path).exists()]
                protected_after = _protected_snapshot(root)
                database_after = _database_snapshot(root)
                database_unchanged = database_before == database_after
                protected_assets_unchanged = protected_before == protected_after
                if mode == "SMOKE_TEST":
                    audit = {
                        "run_id": run_id,
                        "report_date": report_date,
                        "mode": "HERMES_GATEWAY_SMOKE_TEST",
                        "execution_owner_proof": execution_proof,
                        "scope": read_json(run_dir / "scope_manifest.json"),
                        "scope_diff": scope_payload["summary"],
                        "previous_successful_weekly_run_id": previous_id,
                        "preflight": read_json(run_dir / "preflight_result.json")["status"],
                        "entrypoints_missing": missing,
                        "database_before": database_before,
                        "database_after": database_after,
                        "database_unchanged": database_unchanged,
                        "protected_assets_unchanged": protected_assets_unchanged,
                        "protected_before": protected_before,
                        "protected_after": protected_after,
                        "collection_invoked": False,
                        "report_invoked": False,
                        "archive_invoked": False,
                        "publish_invoked": False,
                        "git_invoked": False,
                        "notification_invoked": False,
                        "scheduler_invoked": False,
                    }
                    if not database_unchanged:
                        state.transition(
                            "INTEGRATION_FAILED_DATABASE_MUTATION",
                            "Review database changed during Hermes smoke test.",
                            "HERMES",
                        )
                        audit["final_state"] = state.state
                        audit["state_history"] = state.data["history"]
                        write_json_atomic(run_dir / "hermes_smoke_test_audit.json", audit)
                        return {"status": state.state, "run_id": run_id, "state": state.state, "audit": audit}
                    if missing or not protected_assets_unchanged:
                        state.transition(
                            "TECHNICAL_FAILED",
                            "Smoke-test entrypoint or protected-asset check failed.",
                            "HERMES",
                        )
                        audit["final_state"] = state.state
                        audit["state_history"] = state.data["history"]
                        write_json_atomic(run_dir / "hermes_smoke_test_audit.json", audit)
                        return {"status": state.state, "run_id": run_id, "state": state.state, "audit": audit}
                    state.checkpoint("smoke_test", {"audit": str(run_dir / "hermes_smoke_test_audit.json")})
                    state.transition(
                        "SMOKE_TEST_SUCCESS",
                        "Gateway-owned smoke test completed without collection, database mutation, reporting, publication, notification or scheduling.",
                        "HERMES",
                    )
                    audit["final_state"] = state.state
                    audit["state_history"] = state.data["history"]
                    write_json_atomic(run_dir / "hermes_smoke_test_audit.json", audit)
                    write_json_atomic(
                        run_dir / "smoke_test_log.json",
                        {
                            "status": state.state,
                            "execution_source": execution_proof["execution_source"] if execution_proof else None,
                            "states": [entry["state"] for entry in state.data["history"]],
                            "safe_short_circuit": {
                                "collectors": True,
                                "report": True,
                                "archive": True,
                                "publish": True,
                                "notification": True,
                                "scheduler": True,
                            },
                        },
                    )
                    return {"status": "SMOKE_TEST_SUCCESS", "run_id": run_id, "state": state.state, "audit": audit}
                audit = {
                    "run_id": run_id,
                    "report_date": report_date,
                    "mode": "SUPERVISED_WEEKLY_DRY_RUN",
                    "scope": read_json(run_dir / "scope_manifest.json"),
                    "scope_diff": scope_payload["summary"],
                    "previous_successful_weekly_run_id": previous_id,
                    "preflight": read_json(run_dir / "preflight_result.json")["status"],
                    "entrypoints_missing": missing,
                    "database_incremental_write_enabled": policy["database_incremental_write_enabled"],
                    "collection_invoked": False,
                    "archive_invoked": False,
                    "publish_invoked": False,
                    "notification_invoked": False,
                    "protected_assets_unchanged": protected_assets_unchanged,
                    "protected_before": protected_before,
                    "protected_after": protected_after,
                    "readiness": "READY_FOR_HERMES_WEEKLY_SUPERVISED_RUN" if not missing and protected_before == protected_after else "BLOCKED",
                }
                write_json_atomic(run_dir / "supervised_weekly_dry_run_audit.json", audit)
                if audit["readiness"] == "BLOCKED":
                    state.transition("TECHNICAL_FAILED", "Dry-run entrypoint or protected-asset check failed.", "HERMES")
                    return _action_result(state)
                state.checkpoint("dry_run", {"audit": str(run_dir / "supervised_weekly_dry_run_audit.json")})
                state.transition("SUPERVISED_DRY_RUN_COMPLETE", "No collection, archive, publish, notification or database write was invoked.")
                return {"status": audit["readiness"], "run_id": run_id, "state": state.state, "audit": audit}

            # Production stages are checkpointed so a human verification pause or
            # process interruption resumes the same logical run.
            state.transition("COLLECTING")
            collector_retries = int(policy.get("collector_retry_count", 2))
            if previous_dir and not (run_dir / "raw" / "bv_config").exists() and (previous_dir / "raw" / "bv_config").exists():
                shutil.copytree(previous_dir / "raw" / "bv_config", run_dir / "raw" / "bv_config")
            collectors = [
                ("thd_lowes_bv", [sys.executable, str(root / "scripts" / "run_review_tracker_bv.py"), "--run-dir", str(run_dir)]),
                ("walmart_bv", [sys.executable, str(root / "scripts" / "run_review_tracker_walmart_bv.py"), "--run-dir", str(run_dir)]),
            ]
            for name, command in collectors:
                if state.completed(name):
                    continue
                completed = _run_command(command, root, run_dir / "logs" / f"{name}.json", collector_retries)
                combined = f"{completed.stdout}\n{completed.stderr}".upper()
                if any(marker in combined for marker in HUMAN_MARKERS):
                    state.transition("NEEDS_HUMAN_VERIFICATION", f"{name} encountered CAPTCHA or Robot Check.", "HUMAN")
                    return _action_result(state)
                if completed.returncode != 0:
                    state.transition("TECHNICAL_FAILED", f"{name} failed after retry policy.", "HERMES")
                    return _action_result(state)
                state.checkpoint(name)
            storefront = run_dir / "walmart_storefront_current.json"
            if not storefront.exists():
                state.transition("NEEDS_HUMAN_VERIFICATION", "Walmart product-page input is not yet present; resume after supervised capture.", "HUMAN")
                return _action_result(state)
            storefront_text = storefront.read_text(encoding="utf-8-sig").upper()
            if any(marker in storefront_text for marker in HUMAN_MARKERS):
                state.transition("NEEDS_HUMAN_VERIFICATION", "Walmart product page requires human verification.", "HUMAN")
                return _action_result(state)
            state.checkpoint("walmart_product_page")
            state.transition("COLLECTION_COMPLETE")

            if not state.completed("report_data"):
                completed = _run_command(
                    ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(root / "build_biweekly_report_data.ps1"), "-RunDir", str(run_dir)],
                    root,
                    run_dir / "logs" / "report_data.json",
                    0,
                )
                if completed.returncode != 0:
                    state.transition("TECHNICAL_FAILED", "Existing Review report-data builder failed.", "HERMES")
                    return _action_result(state)
                state.checkpoint("report_data")
            current_summary = read_json(run_dir / "review_summary.json")
            previous_summary = read_json(previous_dir / "review_summary.json") if previous_dir and (previous_dir / "review_summary.json").exists() else []
            qa = deterministic_qa(current_scope, current_summary, previous_summary, policy)
            write_json_atomic(run_dir / "deterministic_qa.json", qa)
            if not qa["passed"]:
                state.transition("QA_FAILED", "Deterministic QA failed.", "HERMES")
                return _action_result(state)
            if qa["anomalies"] and not state.completed("data_review"):
                write_json_atomic(run_dir / "sol_data_review_request.json", {"gate": "DATA_ANOMALY", "allowed_decisions": ["APPROVE_RUN", "HOLD_RUN"], "anomalies": qa["anomalies"]})
                if data_decision not in {"APPROVE_RUN", "HOLD_RUN"}:
                    state.transition("DATA_ANOMALY_REVIEW_REQUIRED", "Business plausibility requires Sol review.", "SOL")
                    return _action_result(state)
                write_json_atomic(run_dir / "sol_data_review_decision.json", {"decision": data_decision, "decided_at": utc_now()})
                if data_decision == "HOLD_RUN":
                    state.transition("DATA_ANOMALY_REVIEW_REQUIRED", "Sol reviewer held the data.", "SOL")
                    return _action_result(state)
                state.checkpoint("data_review", {"decision": data_decision})
            state.checkpoint("qa")
            state.transition("QA_PASSED")

            # Formal rendering/archive/publish remain production-only. They are
            # intentionally unreachable from the supervised dry run above.
            report_path = root / "reports" / f"{run_id}.html"
            comparison_path = run_dir / "period_comparison.json"
            if not state.completed("comparison"):
                if previous_dir and (previous_dir / "review_summary.json").exists():
                    comparison_command = [
                        sys.executable,
                        str(root / "scripts" / "build_review_period_comparison.py"),
                        "--current-summary", str(run_dir / "review_summary.json"),
                        "--prior-summary", str(previous_dir / "review_summary.json"),
                        "--current-reviews", str(run_dir / "low_star_reviews.json"),
                        "--current-date", report_date,
                        "--prior-date", str(read_json(previous_dir / "run_manifest.json").get("report_date") if (previous_dir / "run_manifest.json").exists() else read_json(previous_dir / "run_state.json").get("report_date")),
                        "--current-scope", str(run_dir / "listing_sources.json"),
                        "--prior-scope", str(previous_dir / "listing_sources.json"),
                        "--scope-diff", str(run_dir / "scope_diff.json"),
                        "--output", str(comparison_path),
                    ]
                    completed = _run_command(comparison_command, root, run_dir / "logs" / "comparison.json", 0)
                    if completed.returncode != 0:
                        state.transition("TECHNICAL_FAILED", "Scope-aware comparison builder failed.", "HERMES")
                        return _action_result(state)
                else:
                    write_json_atomic(
                        comparison_path,
                        {"currentReportDate": report_date, "priorReportDate": None, "comparisonScope": "FIRST_WEEKLY_BASELINE", "platforms": [], "totals": None, "skus": [], "scopeChangeAudit": {}},
                    )
                state.checkpoint("comparison")

            if not state.completed("report"):
                title = f"{report_date} WEEKLY REVIEW — THD / Lowe's / Walmart"
                report_command = [
                    "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(root / "build_visual_dashboard.ps1"),
                    "-SummaryPath", str(run_dir / "review_summary.json"),
                    "-ReviewsPath", str(run_dir / "low_star_reviews.json"),
                    "-ReportPath", str(report_path),
                    "-ReportDate", report_date,
                    "-Period", "WEEKLY REVIEW",
                    "-ReportTitle", title,
                    "-SourceNote", "Current active Review scope; product-page metrics plus readable public review text",
                    "-ComparisonPath", str(comparison_path),
                ]
                completed = _run_command(report_command, root, run_dir / "logs" / "report.json", 0)
                if completed.returncode != 0 or not report_path.exists():
                    state.transition("TECHNICAL_FAILED", "Existing Review report renderer failed.", "HERMES")
                    return _action_result(state)
                state.checkpoint("report", {"path": str(report_path), "sha256": sha256(report_path)})
                state.transition("REPORT_BUILT")

            if not state.completed("archive"):
                archive_command = [
                    "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(root / "update_archive_portal.ps1"),
                    "-SummaryPath", str(run_dir / "review_summary.json"),
                    "-ReviewsPath", str(run_dir / "low_star_reviews.json"),
                    "-RunId", run_id,
                    "-ReportDate", report_date,
                    "-ReportTitle", f"{report_date} WEEKLY REVIEW — THD / Lowe's / Walmart",
                    "-Period", "WEEKLY REVIEW",
                    "-ReportType", "weekly",
                    "-ReportUrl", f"reports/{run_id}.html",
                    "-Notes", "Weekly Review Tracker; scope changes are audited separately.",
                ]
                completed = _run_command(archive_command, root, run_dir / "logs" / "archive.json", 0)
                if completed.returncode != 0:
                    state.transition("TECHNICAL_FAILED", "Existing archive builder failed.", "HERMES")
                    return _action_result(state)
                state.checkpoint("archive", {"manifest_sha256": sha256(root / "archive_manifest.json")})
                state.transition("ARCHIVED")

            state.transition("PUBLISHING")
            if not state.completed("publish"):
                publish_retries = int(policy.get("publish_retry_count", 2))
                add = _run_command(
                    ["git", "add", str(report_path.relative_to(root)), "archive_manifest.json", "index.html"],
                    root,
                    run_dir / "logs" / "git_add.json",
                    0,
                )
                if add.returncode != 0:
                    state.transition("PUBLISH_FAILED", "Git staging failed after report build.", "HERMES")
                    return _action_result(state)
                staged = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=root)
                if staged.returncode == 1:
                    commit = _run_command(
                        ["git", "commit", "-m", f"chore: publish weekly review {report_date}"],
                        root,
                        run_dir / "logs" / "git_commit.json",
                        0,
                    )
                    if commit.returncode != 0:
                        state.transition("PUBLISH_FAILED", "Git commit failed.", "HERMES")
                        return _action_result(state)
                push = _run_command(["git", "push"], root, run_dir / "logs" / "git_push.json", publish_retries)
                if push.returncode != 0:
                    state.transition("PUBLISH_FAILED", "Git push failed after retry policy.", "HERMES")
                    return _action_result(state)
                base_url = str(policy["github_pages_base_url"]).rstrip("/") + "/"
                report_url = f"{base_url}reports/{run_id}.html"
                verified = False
                verification_errors: list[str] = []
                for attempt in range(1, publish_retries + 2):
                    try:
                        with urllib.request.urlopen(f"{report_url}?verify={int(time.time())}", timeout=30) as response:
                            body = response.read()
                            verified = response.status == 200 and len(body) > 1000
                    except Exception as exc:  # verification evidence is recorded below
                        verification_errors.append(f"attempt {attempt}: {exc}")
                    if verified:
                        break
                    time.sleep(min(attempt * 5, 15))
                write_json_atomic(run_dir / "github_pages_verification.json", {"url": report_url, "verified": verified, "errors": verification_errors, "verified_at": utc_now()})
                if not verified:
                    state.transition("PUBLISH_FAILED", "GitHub Pages endpoint verification failed.", "HERMES")
                    return _action_result(state)
                state.checkpoint("publish", {"url": report_url, "verified": True})

            unavailable = sum(1 for row in current_summary if row.get("dataAvailable", True) is False)
            final_state = "SUCCESS_WITH_PLATFORM_LIMITATION" if unavailable else "SUCCESS"
            state.transition(final_state)
            counts = Counter(canonical_scope_row(row)["platform_code"] for row in current_scope)
            low_reviews = read_json(run_dir / "low_star_reviews.json")
            readable_new = sum(
                1
                for row in low_reviews
                if str(row.get("title") or "").strip() or str(row.get("text") or "").strip()
            )
            p0 = sum(1 for row in current_summary if str(row.get("urgency") or "").startswith("P0"))
            p1 = sum(1 for row in current_summary if str(row.get("urgency") or "").startswith("P1"))
            final_status = {
                "status": "REVIEW_TRACKER_SUCCESS",
                "report_date": report_date,
                "scope": {**dict(counts), "TOTAL": len(current_scope)},
                "scope_change": {
                    "added": scope_payload["summary"]["NEW_TO_SCOPE"],
                    "removed": scope_payload["summary"]["REMOVED_FROM_SCOPE"],
                    "changed": scope_payload["summary"]["LINK_CHANGED"] + scope_payload["summary"]["RECORD_IDENTITY_CHANGED"],
                },
                "collection": {"available": len(current_summary) - unavailable, "unavailable": unavailable},
                "new_low_rating_reviews": readable_new,
                "P0": p0,
                "P1": p1,
                "report": "BUILT",
                "archive": "UPDATED",
                "github_pages": "VERIFIED",
                "external_notification_sent": False,
            }
            write_json_atomic(run_dir / "final_status.json", final_status)
            return {**final_status, "run_id": run_id, "state": final_state}
        except Exception as exc:
            if mode == "SMOKE_TEST" and _database_snapshot(root) != database_before:
                state.transition("INTEGRATION_FAILED_DATABASE_MUTATION", str(exc), "HERMES")
            elif state.state not in TERMINAL_STATES and state.state not in {"PREFLIGHT_FAILED", "QA_FAILED", "NEEDS_HUMAN_VERIFICATION", "SCOPE_ANOMALY_REVIEW_REQUIRED", "DATA_ANOMALY_REVIEW_REQUIRED"}:
                state.transition("TECHNICAL_FAILED", str(exc), "HERMES")
            raise
