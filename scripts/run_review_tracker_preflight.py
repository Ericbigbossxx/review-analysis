"""CLI for the Review Tracker read-only isolation preflight."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.review_tracker.preflight import run_preflight


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=ROOT)
    parser.add_argument("--source", type=Path, required=True, help="Frozen run listing_sources.json")
    parser.add_argument("--listing-master", type=Path)
    parser.add_argument("--scope-manifest", type=Path)
    args = parser.parse_args()
    result = run_preflight(args.project_root, args.source, args.listing_master, args.scope_manifest)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(result["status"])
    return 0 if result["status"] == "PREFLIGHT_PASSED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
