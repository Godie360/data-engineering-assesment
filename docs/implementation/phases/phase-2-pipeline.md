# Phase 2 — Processing Engine

## Status

pending

## Scope

- `engine/loader.py`
- `engine/cleaner.py`
- `engine/transformer.py`
- `engine/loader_db.py`
- `engine/aggregator.py`
- `engine/logger.py`
- `run_pipeline.py`

## Features

- Chunked CSV reading (100k rows/chunk) to control memory usage
- Data cleaning: null fills for balance columns (0.00), drop null/zero amounts, deduplicate, normalise types, cast booleans
- Derived column transformation: transaction_hour, transaction_day, amount_bucket (standardisation), balance_discrepancy, has_balance_error, is_merchant_recipient, net_recipient_gain
- Bulk COPY insert to `mobile_money_transactions` (idempotent via TRUNCATE CASCADE before load)
- Post-load aggregation: single INSERT...SELECT populates `transaction_summary` (day × type)
- Structured logging with per-run summary: rows_in, rows_dropped, rows_with_balance_errors, rows_loaded, summary_rows_written

## Tasks

- [ ] TASK-05: Chunked loader (`engine/loader.py`)
- [ ] TASK-06: Cleaner (`engine/cleaner.py`)
- [ ] TASK-07: Transformer (`engine/transformer.py`)
- [ ] TASK-08: DB writer (`engine/loader_db.py`)
- [ ] TASK-09: Aggregator (`engine/aggregator.py`)
- [ ] TASK-10: Pipeline orchestrator (`run_pipeline.py`)

## Acceptance Criteria

- `python run_pipeline.py` completes without unhandled exception
- `SELECT COUNT(*) FROM mobile_money_transactions` matches `rows_loaded` in log
- Running `run_pipeline.py` twice produces the same row count (idempotent)
- `SELECT COUNT(*) FROM transaction_summary` returns > 0 rows
- No balance column contains NULL in the loaded data
- No column uses type TEXT where NUMERIC or BOOLEAN is defined in schema
- Log output includes: rows_in, rows_dropped, rows_with_balance_errors, rows_loaded, summary_rows_written
