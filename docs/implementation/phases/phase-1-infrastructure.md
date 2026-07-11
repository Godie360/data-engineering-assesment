# Phase 1 — Infrastructure

## Status

pending

## Scope

- `docker-compose.yml`
- `.env`, `.env.example`
- `requirements.txt`
- `sql/schema.sql`, `sql/apply_schema.py`
- `data/raw/` directory (git-ignored)
- `engine/`, `rag/`, `sql/` directory skeletons

## Features

- PostgreSQL 15 running in Docker, reachable at localhost:5432
- `selcom_assessment` database with `mobile_money_transactions` table and all indexes
- Python dependencies installable from `requirements.txt`
- Dataset placed at `data/raw/paysim.csv`

## Tasks

- [ ] TASK-01: Project structure and dependencies
- [ ] TASK-02: Docker PostgreSQL setup
- [ ] TASK-03: Database schema creation
- [ ] TASK-04: Dataset download and placement

## Acceptance Criteria

- `docker compose up -d` starts PostgreSQL with no errors
- `python -c "import psycopg2, pandas, openai, streamlit"` exits 0
- `data/raw/paysim.csv` exists and has > 50,000 rows
- `python sql/apply_schema.py` exits 0 and is idempotent
- `mobile_money_transactions` table exists with correct column types
