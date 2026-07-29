"""Evidence naming, hashing, and database registration helpers."""

from __future__ import annotations

import hashlib
from pathlib import Path


def sha256_file(path: Path | str) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def evidence_name(run_id: str, record_id: str, suffix: str) -> str:
    return f"{run_id}__{record_id}__{suffix}".replace("/", "_").replace("\\", "_")


def register_evidence(connection, run_id: str, record_id: str | None, evidence_type: str, path: Path | str, captured_at: str, source_url: str | None = None) -> None:
    evidence_path = str(path)
    connection.execute(
        "INSERT OR IGNORE INTO evidence_files (run_id, record_id, evidence_type, evidence_path, sha256, captured_at, source_url) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (run_id, record_id, evidence_type, evidence_path, sha256_file(path), captured_at, source_url),
    )
