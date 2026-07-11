# Pipeline Architecture

## System Overview

End-to-end data pipeline: raw CSV → Python processing engine → PostgreSQL → RAG LLM application.

## Stack

| Layer | Technology | Rationale |
|---|---|---|
| Dataset | Synthetic Mobile Money Transaction Dataset (denishazamuke, Kaggle) | Synthetic mobile money, 4.2M rows, 10 columns, mirrors Selcom domain |
| Processing | Python 3.11, pandas | Chunked reads, well-understood, assessor-readable |
| Database | PostgreSQL 15 via Docker | Portable, no local install required |
| LLM | OpenAI `gpt-4o-mini` via `openai` SDK | Cost-efficient, fast, sufficient for Text-to-SQL |
| UI | Streamlit | Single-file app, browser demo, no frontend build step |
| Container | Docker + docker-compose | Reproducible environment for PostgreSQL |

## Data Flow

```
data/MoMTSim_20240722202413_1000_dataset.csv
      │
      ▼
engine/loader.py          ← chunked CSV reader (100k rows/chunk)
      │
      ▼  [per chunk]
engine/cleaner.py         ← fill nulls, drop invalids, deduplicate, fix types
      │
      ▼  [per chunk]
engine/transformer.py     ← add 7 derived columns (hour, bucket, error flags, etc.)
      │
      ▼  [per chunk]
engine/loader_db.py       ← COPY bulk insert → mobile_money_transactions
      │
      ▼  [once, after all chunks loaded]
engine/aggregator.py      ← INSERT ... SELECT → transaction_summary
      │
      ▼
PostgreSQL
  ├── mobile_money_transactions   (4.2M cleaned + enriched rows)
  └── transaction_summary         (days × 5 types: PAYMENT, TRANSFER, DEPOSIT, WITHDRAWAL, DEBIT)
      │
      ▼
rag/schema.py             ← builds schema context for both tables
rag/query_gen.py          ← natural language → SQL (OpenAI gpt-4o-mini, temp=0)
rag/executor.py           ← executes SELECT against PostgreSQL, caps at 500 rows
rag/response_gen.py       ← SQL results → grounded natural language answer (temp=0.3)
      │
      ▼
app.py (Streamlit)        ← question input, answer display, SQL expander, Q&A history
```

## Module Boundaries

| Module | Owns | Must not touch |
|---|---|---|
| `engine/loader.py` | chunked CSV reading | cleaning, transformation, DB |
| `engine/cleaner.py` | null fills, drop rules, type casts, dedup | derived columns, DB |
| `engine/transformer.py` | 7 derived columns | cleaning rules, DB |
| `engine/loader_db.py` | COPY insert to `mobile_money_transactions` | aggregation, RAG |
| `engine/aggregator.py` | INSERT...SELECT into `transaction_summary` | chunk processing |
| `rag/` | schema context, SQL gen, execution, response gen | CSV loading, cleaning |
| `app.py` | UI only, calls `rag/` | direct DB writes, engine internals |
| `docker-compose.yml` | PostgreSQL service definition | application code |
| `sql/schema.sql` | DDL for both tables, all indexes | data logic |

## Entry Points

| Command | Purpose |
|---|---|
| `docker compose up -d` | Start PostgreSQL |
| `python run_pipeline.py` | Load, clean, transform, write to DB |
| `streamlit run app.py` | Launch RAG application |
| `python run_pipeline.py --validate` | Dry-run: print row counts and sample |

## Environment Variables

All secrets in `.env` (git-ignored):

```
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=selcom_assessment
POSTGRES_USER=selcom
POSTGRES_PASSWORD=selcom_pass
OPENAI_API_KEY=sk-...
```
