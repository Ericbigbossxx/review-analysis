-- Initial schema migration marker. Apply through scripts/apply_initial_schema.py
-- after migration approval; that runner executes database/schema.sql and records
-- this migration atomically. This file is intentionally data-free.
CREATE TABLE IF NOT EXISTS schema_migrations (
  migration_id TEXT PRIMARY KEY,
  applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  checksum TEXT NOT NULL
);
