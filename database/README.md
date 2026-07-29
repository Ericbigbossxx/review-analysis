# Database boundary

`tracker.db` is the intended SQLite database location. It is intentionally absent in Phase 0: creating an operational database can be misread as approval to collect or migrate production data.

Before first approved use, invoke `scripts/apply_initial_schema.py database/tracker.db --approve`. It applies the reviewed DDL and records `0001_initial_schema`; it inserts no collection data.
