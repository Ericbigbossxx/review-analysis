"""CLI entry point for the Hermes Weekly Review runtime."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.review_tracker.hermes_runtime import run_weekly


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=ROOT)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--report-date", required=True)
    parser.add_argument("--mode", choices=("DRY_RUN", "SMOKE_TEST", "PRODUCTION"), default="DRY_RUN")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--scope-decision", choices=("APPROVE_RUN", "HOLD_RUN"))
    parser.add_argument("--data-decision", choices=("APPROVE_RUN", "HOLD_RUN"))
    args = parser.parse_args()
    result = run_weekly(
        args.project_root,
        args.run_id,
        args.report_date,
        args.mode,
        args.resume,
        args.scope_decision,
        args.data_decision,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] in {"READY_FOR_HERMES_WEEKLY_SUPERVISED_RUN", "SMOKE_TEST_SUCCESS", "REVIEW_TRACKER_SUCCESS"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
