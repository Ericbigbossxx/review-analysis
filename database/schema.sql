-- US Local Channel Listing Tracker: canonical SQLite schema.
-- Phase 0 only: no business data is inserted by this script.
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS products (
  record_id TEXT PRIMARY KEY,
  active INTEGER NOT NULL CHECK (active IN (0, 1)),
  platform TEXT NOT NULL CHECK (platform IN ('WALMART', 'THD', 'LOWES')),
  brand TEXT,
  product_line TEXT,
  internal_sku TEXT NOT NULL,
  model TEXT,
  platform_item_id TEXT,
  product_name TEXT,
  listing_url TEXT NOT NULL,
  primary_keyword TEXT,
  secondary_keyword TEXT,
  third_keyword TEXT,
  zip_code TEXT,
  expected_seller TEXT,
  monitor_listing INTEGER NOT NULL DEFAULT 1 CHECK (monitor_listing IN (0, 1)),
  monitor_rank INTEGER NOT NULL DEFAULT 0 CHECK (monitor_rank IN (0, 1)),
  monitor_review INTEGER NOT NULL DEFAULT 1 CHECK (monitor_review IN (0, 1)),
  max_search_pages INTEGER CHECK (max_search_pages IS NULL OR max_search_pages > 0),
  notes TEXT,
  source_path TEXT NOT NULL,
  source_row_number INTEGER,
  source_hash TEXT,
  identity_status TEXT NOT NULL DEFAULT 'CONFIRMED_FROM_SOURCE',
  legacy_source TEXT,
  migrated_at TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(platform, internal_sku)
);

CREATE TABLE IF NOT EXISTS collection_runs (
  run_id TEXT PRIMARY KEY,
  module_name TEXT NOT NULL CHECK (module_name IN ('listing_monitor', 'review_tracker')),
  platform TEXT NOT NULL CHECK (platform IN ('WALMART', 'THD', 'LOWES')),
  run_mode TEXT NOT NULL CHECK (run_mode IN ('baseline', 'incremental', 'manual_retry', 'migration')),
  started_at TEXT NOT NULL,
  completed_at TEXT,
  status TEXT NOT NULL CHECK (status IN ('PENDING', 'RUNNING', 'SUCCEEDED', 'PARTIAL', 'FAILED', 'BLOCKED')),
  capture_status TEXT NOT NULL CHECK (capture_status IN ('NOT_STARTED', 'CAPTURED', 'NOT_AVAILABLE', 'ACCESS_BLOCKED', 'FAILED')),
  config_hash TEXT,
  collector_version TEXT,
  source_system TEXT NOT NULL,
  error_code TEXT,
  error_message TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS evidence_files (
  evidence_id INTEGER PRIMARY KEY,
  run_id TEXT NOT NULL REFERENCES collection_runs(run_id),
  record_id TEXT REFERENCES products(record_id),
  evidence_type TEXT NOT NULL CHECK (evidence_type IN ('SCREENSHOT', 'RAW_RESPONSE', 'HTML', 'LOG', 'OTHER')),
  evidence_path TEXT NOT NULL UNIQUE,
  sha256 TEXT,
  captured_at TEXT NOT NULL,
  source_url TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS listing_snapshots (
  listing_snapshot_id INTEGER PRIMARY KEY,
  run_id TEXT NOT NULL REFERENCES collection_runs(run_id),
  record_id TEXT NOT NULL REFERENCES products(record_id),
  observed_at TEXT NOT NULL,
  source_system TEXT NOT NULL,
  capture_status TEXT NOT NULL CHECK (capture_status IN ('CAPTURED', 'NOT_AVAILABLE', 'ACCESS_BLOCKED', 'FAILED')),
  error_status TEXT,
  currency TEXT,
  current_price REAL,
  original_price REAL,
  promotion_text TEXT,
  rating REAL,
  review_count INTEGER,
  inventory_status TEXT,
  delivery_status TEXT,
  seller_name TEXT,
  page_status TEXT,
  raw_evidence_path TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(run_id, record_id)
);

CREATE TABLE IF NOT EXISTS ranking_snapshots (
  ranking_snapshot_id INTEGER PRIMARY KEY,
  run_id TEXT NOT NULL REFERENCES collection_runs(run_id),
  record_id TEXT NOT NULL REFERENCES products(record_id),
  keyword TEXT NOT NULL,
  rank_kind TEXT NOT NULL CHECK (rank_kind IN ('ORGANIC', 'SPONSORED', 'RAW_SLOT')),
  observed_at TEXT NOT NULL,
  source_system TEXT NOT NULL,
  capture_status TEXT NOT NULL CHECK (capture_status IN ('CAPTURED', 'NOT_AVAILABLE', 'ACCESS_BLOCKED', 'FAILED')),
  error_status TEXT,
  zip_code TEXT,
  store_context TEXT,
  result_page INTEGER,
  result_position INTEGER,
  sponsored INTEGER CHECK (sponsored IN (0, 1)),
  raw_evidence_path TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(run_id, record_id, keyword, rank_kind)
);

CREATE TABLE IF NOT EXISTS review_snapshots (
  review_snapshot_id INTEGER PRIMARY KEY,
  run_id TEXT NOT NULL REFERENCES collection_runs(run_id),
  record_id TEXT NOT NULL REFERENCES products(record_id),
  observed_at TEXT NOT NULL,
  source_system TEXT NOT NULL,
  capture_status TEXT NOT NULL CHECK (capture_status IN ('CAPTURED', 'NOT_AVAILABLE', 'ACCESS_BLOCKED', 'FAILED')),
  error_status TEXT,
  average_rating REAL,
  total_review_count INTEGER,
  rating_1_count INTEGER,
  rating_2_count INTEGER,
  rating_3_count INTEGER,
  rating_4_count INTEGER,
  rating_5_count INTEGER,
  readable_review_count INTEGER,
  verified_purchase_count INTEGER,
  raw_evidence_path TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(run_id, record_id)
);

CREATE TABLE IF NOT EXISTS reviews (
  review_id INTEGER PRIMARY KEY,
  record_id TEXT NOT NULL REFERENCES products(record_id),
  first_seen_run_id TEXT NOT NULL REFERENCES collection_runs(run_id),
  last_seen_run_id TEXT NOT NULL REFERENCES collection_runs(run_id),
  source_system TEXT NOT NULL,
  source_review_id TEXT,
  platform_review_id TEXT,
  review_id_source TEXT NOT NULL DEFAULT 'PLATFORM_ID',
  legacy_review_key TEXT,
  identity_confidence TEXT,
  rating INTEGER CHECK (rating BETWEEN 1 AND 5),
  review_date TEXT,
  title TEXT,
  review_text TEXT,
  verified_purchase INTEGER CHECK (verified_purchase IN (0, 1)),
  syndicated INTEGER CHECK (syndicated IN (0, 1)),
  reviewer_display_name TEXT,
  raw_evidence_path TEXT,
  source_hash TEXT,
  source_file TEXT,
  source_row INTEGER,
  migrated_at TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(record_id, source_review_id),
  UNIQUE(record_id, platform_review_id),
  UNIQUE(record_id, legacy_review_key)
);

CREATE TABLE IF NOT EXISTS listing_changes (
  listing_change_id INTEGER PRIMARY KEY,
  run_id TEXT NOT NULL REFERENCES collection_runs(run_id),
  record_id TEXT NOT NULL REFERENCES products(record_id),
  change_type TEXT NOT NULL,
  field_name TEXT NOT NULL,
  previous_value TEXT,
  current_value TEXT,
  detected_at TEXT NOT NULL,
  evidence_path TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(run_id, record_id, change_type, field_name)
);

CREATE TABLE IF NOT EXISTS review_changes (
  review_change_id INTEGER PRIMARY KEY,
  run_id TEXT NOT NULL REFERENCES collection_runs(run_id),
  record_id TEXT NOT NULL REFERENCES products(record_id),
  change_type TEXT NOT NULL CHECK (change_type IN ('NEW_REVIEW', 'UPDATED_REVIEW', 'REMOVED_REVIEW', 'RATING_DELTA', 'COUNT_DELTA')),
  source_review_id TEXT,
  previous_value TEXT,
  current_value TEXT,
  detected_at TEXT NOT NULL,
  evidence_path TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(run_id, record_id, change_type, source_review_id)
);

CREATE TABLE IF NOT EXISTS collection_errors (
  collection_error_id INTEGER PRIMARY KEY,
  run_id TEXT NOT NULL REFERENCES collection_runs(run_id),
  record_id TEXT REFERENCES products(record_id),
  occurred_at TEXT NOT NULL,
  module_name TEXT NOT NULL,
  platform TEXT NOT NULL,
  error_code TEXT NOT NULL,
  error_message TEXT,
  retryable INTEGER NOT NULL DEFAULT 0 CHECK (retryable IN (0, 1)),
  raw_evidence_path TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_listing_snapshots_record_observed ON listing_snapshots(record_id, observed_at);
CREATE INDEX IF NOT EXISTS idx_ranking_snapshots_record_keyword_observed ON ranking_snapshots(record_id, keyword, observed_at);
CREATE INDEX IF NOT EXISTS idx_review_snapshots_record_observed ON review_snapshots(record_id, observed_at);
CREATE INDEX IF NOT EXISTS idx_reviews_record_review_date ON reviews(record_id, review_date);
CREATE INDEX IF NOT EXISTS idx_collection_errors_run ON collection_errors(run_id, occurred_at);
