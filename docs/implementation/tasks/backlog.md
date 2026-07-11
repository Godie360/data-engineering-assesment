# Task Backlog

## Status

pending

## Objective

All 19 tasks across 4 phases required to complete the Selcom Data Engineer Assessment by 2026-07-17 18:00.

## Implementation Checklist

- [ ] TASK-01: Project structure and dependencies
- [ ] TASK-02: Docker PostgreSQL setup
- [ ] TASK-03: Database schema creation
- [ ] TASK-04: Dataset download and placement
- [ ] TASK-05: Chunked loader
- [ ] TASK-06: Cleaner
- [ ] TASK-07: Transformer
- [ ] TASK-08: DB writer
- [ ] TASK-09: Aggregator
- [ ] TASK-10: Pipeline orchestrator
- [ ] TASK-11: Schema context builder
- [ ] TASK-12: SQL generator
- [ ] TASK-13: Query executor
- [ ] TASK-14: Response generator
- [ ] TASK-15: Streamlit UI
- [ ] TASK-16: README
- [ ] TASK-17: Brief report
- [ ] TASK-18: Repo cleanup
- [ ] TASK-19: Final smoke test

---

## TASK-01 — Project Structure and Dependencies

- **Status**: pending
- **Phase**: Phase 1
- **Objective**: Create directory layout and install all Python dependencies.
- **Scope Boundary**:
  - In: `requirements.txt`, directory skeleton (`engine/`, `rag/`, `sql/`, `data/`)
  - Out: application logic, Docker config
- **Acceptance Criteria**:
  - `requirements.txt` lists: pandas, psycopg2-binary, openai, streamlit, python-dotenv
  - All directories exist: `engine/`, `rag/`, `sql/`, `data/`
  - `pip install -r requirements.txt` exits 0
- **Agent Context**: Read `docs/design/architecture/pipeline-architecture.md`

---

## TASK-02 — Docker PostgreSQL Setup

- **Status**: pending
- **Phase**: Phase 1
- **Objective**: `docker-compose.yml` starts PostgreSQL 15 reachable at localhost:5432.
- **Scope Boundary**:
  - In: `docker-compose.yml`, `.env.example`
  - Out: schema, application code
- **Acceptance Criteria**:
  - `docker compose up -d` exits 0
  - `docker compose ps` shows postgres container healthy
  - `selcom_assessment` database exists and is reachable
- **Agent Context**: Read `docs/design/architecture/pipeline-architecture.md` → Environment Variables section

---

## TASK-03 — Database Schema Creation

- **Status**: pending
- **Phase**: Phase 1
- **Objective**: `sql/schema.sql` creates `mobile_money_transactions` table and indexes.
- **Scope Boundary**:
  - In: `sql/schema.sql`, `sql/apply_schema.py`
  - Out: data loading, application logic
- **Acceptance Criteria**:
  - `python sql/apply_schema.py` exits 0
  - Table has all columns with correct types per schema doc
  - Running `apply_schema.py` twice does not error (idempotent DDL)
- **Agent Context**: Read `docs/design/data-models/transaction-schema.md`

---

## TASK-04 — Dataset Download and Placement

- **Status**: pending
- **Phase**: Phase 1
- **Objective**: Dataset CSV is at `data/MoMTSim_20240722202413_1000_dataset.csv` with > 50,000 rows.
- **Scope Boundary**:
  - In: `data/MoMTSim_20240722202413_1000_dataset.csv`, Kaggle download instructions in README
  - Out: processing, loading
- **Acceptance Criteria**:
  - `wc -l data/MoMTSim_20240722202413_1000_dataset.csv` returns > 50,001
  - File is git-ignored
- **Agent Context**: Dataset: `https://www.kaggle.com/datasets/denishazamuke/synthetic-mobile-money-transaction-dataset`

---

## TASK-05 — Chunked Loader

- **Status**: pending
- **Phase**: Phase 2
- **Objective**: `engine/loader.py` reads CSV in 100k-row chunks and yields DataFrames.
- **Scope Boundary**:
  - In: `engine/loader.py`
  - Out: cleaning, transformation, DB write
- **Acceptance Criteria**:
  - `load_csv(path)` is a generator yielding DataFrames of ≤100,000 rows
  - Each chunk has all 10 source columns present
- **Agent Context**: Read `docs/design/architecture/pipeline-architecture.md`

---

## TASK-06 — Cleaner

- **Status**: pending
- **Phase**: Phase 2
- **Objective**: `engine/cleaner.py` applies all cleaning rules per chunk.
- **Scope Boundary**:
  - In: `engine/cleaner.py`
  - Out: derived columns, DB write
- **Acceptance Criteria**:
  - Rows with `amount` null or ≤ 0 dropped
  - Duplicates on `(initiator, recipient, step, amount, transactionType)` dropped
  - `transactionType` normalised to uppercase with no whitespace
  - `isFraud` cast to bool
  - Balance columns filled with 0.00 where null
  - Returns `{rows_in, rows_dropped}` dict alongside cleaned DataFrame
- **Agent Context**: Read `docs/design/data-models/transaction-schema.md` → Source Columns

---

## TASK-07 — Transformer

- **Status**: pending
- **Phase**: Phase 2
- **Objective**: `engine/transformer.py` adds all 7 derived columns to each cleaned chunk.
- **Scope Boundary**:
  - In: `engine/transformer.py`
  - Out: cleaning, DB write
- **Acceptance Criteria**:
  - All 7 derived columns present after transform
  - `amount_bucket` values are only: SMALL, MEDIUM, LARGE, VERY_LARGE
  - `has_balance_error` is True where `balance_discrepancy > 0.01`
- **Agent Context**: Read `docs/design/data-models/transaction-schema.md` → Derived Columns

---

## TASK-08 — DB Writer

- **Status**: pending
- **Phase**: Phase 2
- **Objective**: `engine/loader_db.py` bulk-inserts transformed chunks using PostgreSQL COPY.
- **Scope Boundary**:
  - In: `engine/loader_db.py`
  - Out: cleaning, transformation, RAG
- **Acceptance Criteria**:
  - Uses `psycopg2.copy_expert` with StringIO buffer
  - Column order matches table DDL
  - Failed chunk logs error and continues (does not abort load)
- **Agent Context**: Read `docs/design/data-models/transaction-schema.md` → Load Strategy

---

## TASK-09 — Aggregator

- **Status**: pending
- **Phase**: Phase 2
- **Objective**: `engine/aggregator.py` populates `transaction_summary` via a single INSERT...SELECT after all chunks are loaded.
- **Scope Boundary**:
  - In: `engine/aggregator.py`
  - Out: chunk loading, cleaning, transformer, RAG
- **Acceptance Criteria**:
  - `run_aggregation(conn)` executes INSERT...SELECT grouping by `(transaction_day, type)`
  - All 13 metric columns computed correctly
  - `SELECT COUNT(*) FROM transaction_summary` returns > 0 after run
  - Running twice does not duplicate rows (UNIQUE constraint enforces idempotency)
- **Agent Context**: Read `docs/design/data-models/transaction-schema.md` → transaction_summary table

---

## TASK-10 — Pipeline Orchestrator

- **Status**: pending
- **Phase**: Phase 2
- **Objective**: `run_pipeline.py` runs full extract-clean-transform-load-aggregate sequence and prints summary.
- **Scope Boundary**:
  - In: `run_pipeline.py`, `engine/logger.py`
  - Out: RAG, Streamlit
- **Acceptance Criteria**:
  - Completes without unhandled exception
  - Logs: `rows_in`, `rows_dropped`, `rows_with_balance_errors`, `rows_loaded`, `summary_rows_written`
  - `SELECT COUNT(*) FROM mobile_money_transactions` matches `rows_loaded`
  - Running twice produces same count (idempotent: TRUNCATE CASCADE before load)
- **Agent Context**: Read `docs/design/architecture/pipeline-architecture.md` → Entry Points

---

## TASK-11 — Schema Context Builder

- **Status**: pending
- **Phase**: Phase 3
- **Objective**: `rag/schema.py` produces a schema context string covering both tables for OpenAI prompts.
- **Scope Boundary**:
  - In: `rag/schema.py`
  - Out: SQL generation, execution, response
- **Acceptance Criteria**:
  - `get_schema_context()` returns string describing both `mobile_money_transactions` and `transaction_summary`
  - Includes column names, types, and one-line descriptions
  - String length < 4000 characters
- **Agent Context**: Read `docs/design/data-models/transaction-schema.md`, `docs/design/features/rag-application.md`

---

## TASK-12 — SQL Generator

- **Status**: pending
- **Phase**: Phase 3
- **Objective**: `rag/query_gen.py` converts a natural language question to a PostgreSQL SELECT.
- **Scope Boundary**:
  - In: `rag/query_gen.py`
  - Out: execution, response, UI
- **Acceptance Criteria**:
  - `generate_sql(question, schema_context)` returns SQL string starting with `SELECT`
  - Raises `ValueError` if output contains `INSERT|UPDATE|DELETE|DROP|TRUNCATE|ALTER|CREATE`
  - Temperature = 0
- **Agent Context**: Read `docs/design/features/rag-application.md` → query_gen

---

## TASK-13 — Query Executor

- **Status**: pending
- **Phase**: Phase 3
- **Objective**: `rag/executor.py` executes SQL and returns results as list of dicts.
- **Scope Boundary**:
  - In: `rag/executor.py`
  - Out: SQL generation, response generation
- **Acceptance Criteria**:
  - `execute_query(sql)` returns `list[dict]`
  - Result capped at 500 rows
  - SQL error caught, logged, re-raised as `RuntimeError`
- **Agent Context**: Read `docs/design/features/rag-application.md` → executor

---

## TASK-14 — Response Generator

- **Status**: pending
- **Phase**: Phase 3
- **Objective**: `rag/response_gen.py` synthesises a grounded natural language answer.
- **Scope Boundary**:
  - In: `rag/response_gen.py`
  - Out: SQL generation, execution, UI
- **Acceptance Criteria**:
  - `generate_response(question, sql, results)` returns non-empty string
  - System prompt instructs no fabrication
  - Temperature = 0.3
- **Agent Context**: Read `docs/design/features/rag-application.md` → response_gen

---

## TASK-15 — Streamlit UI

- **Status**: pending
- **Phase**: Phase 3
- **Objective**: `app.py` provides browser UI for natural language queries.
- **Scope Boundary**:
  - In: `app.py`
  - Out: engine, rag modules (called, not modified)
- **Acceptance Criteria**:
  - `streamlit run app.py` launches on port 8501 with no import errors
  - Text input, submit button, answer display, SQL expander all present
  - Error shown (not crash) when DB is unavailable
  - Last 5 Q&A pairs in sidebar
- **Agent Context**: Read `docs/design/features/rag-application.md` → app.py

---

## TASK-16 — README

- **Status**: pending
- **Phase**: Phase 4
- **Objective**: `README.md` enables a reviewer to run the project from scratch.
- **Scope Boundary**:
  - In: `README.md`
  - Out: source code
- **Acceptance Criteria**:
  - Sections: Prerequisites, Setup, Download Dataset, Run Pipeline, Run App, Project Structure
  - All commands copy-pasteable and correct
  - Dependency list matches `requirements.txt`

---

## TASK-17 — Brief Report

- **Status**: pending
- **Phase**: Phase 4
- **Objective**: Report (≤3 pages) explains approach, decisions, challenges, assumptions.
- **Scope Boundary**:
  - In: `report.md`
  - Out: source code
- **Acceptance Criteria**:
  - Covers: dataset rationale, pipeline architecture, cleaning decisions, RAG pattern choice, challenges
  - ≤3 pages rendered
  - No fabricated metrics

---

## TASK-18 — Repo Cleanup

- **Status**: pending
- **Phase**: Phase 4
- **Objective**: Repository safe to share — no secrets, no large data files committed.
- **Scope Boundary**:
  - In: `.gitignore`, `.env.example`
  - Out: application code
- **Acceptance Criteria**:
  - `.env` git-ignored
  - `data/` directory git-ignored (dataset CSV must not be committed)
  - `git grep -r "sk-"` returns no matches
  - `.env.example` lists all required env var names with placeholder values

---

## TASK-19 — Final Smoke Test

- **Status**: pending
- **Phase**: Phase 4
- **Objective**: Full end-to-end run succeeds following README instructions only.
- **Scope Boundary**:
  - In: test run, no code changes
  - Out: all source files
- **Acceptance Criteria**:
  - `docker compose up -d` → `python sql/apply_schema.py` → `python run_pipeline.py` → `streamlit run app.py` all succeed in sequence
  - At least 3 example questions answered correctly in the UI
  - No TODO or placeholder text in committed files
