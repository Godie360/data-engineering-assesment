# Selcom Paytech — Data Engineer Assessment

**Sele the Analyst** — an end-to-end data pipeline and RAG chatbot built on 4.2 million synthetic East African mobile money transactions.

---

## What This Does

1. **Data pipeline** — loads, cleans, transforms, and bulk-inserts 4.2M rows into PostgreSQL with chunked processing and a pre-aggregated summary table.
2. **RAG application** — a Next.js chatbot (Sele the Analyst) that translates plain English questions into SQL, executes them against PostgreSQL, validates the answer with hallucination detection, and returns a grounded response with a confidence score.

---

## Architecture

```
docker compose up
       │
       ├── postgres        PostgreSQL 15 (port 5433)
       │
       ├── pipeline        Python: apply schema → load 4.2M rows → build summary table
       │                   (exits on completion)
       │
       ├── api             FastAPI (port 8000) — RAG pipeline over HTTP
       │                   POST /api/chat  →  SQL generation + execution + hallucination check
       │
       └── frontend        Next.js (port 3000) — Sele the Analyst chat UI
```

**Data flow:**

```
CSV (4.2M rows)
  └─► loader.py      chunk reader (100k rows / chunk)
  └─► cleaner.py     null fills, type casts, drop invalid rows
  └─► transformer.py 7 derived columns
  └─► loader_db.py   PostgreSQL COPY (bulk insert)
  └─► aggregator.py  INSERT…SELECT → transaction_summary

PostgreSQL
  ├── mobile_money_transactions  (4.2M cleaned + enriched rows)
  └── transaction_summary        (9 days × 5 types = 45 summary rows)

RAG pipeline (per question)
  └─► query_gen.py    NL → SQL via GPT-4o-mini (JSON mode, temp=0)
  └─► executor.py     SQL syntax check → read-only transaction → results
  └─► hallucination.py back-translation alignment check + confidence score
  └─► response_gen.py results → grounded answer (temp=0.3)
```

---

## Stack

| Layer | Technology | Why |
|---|---|---|
| Dataset | Synthetic Mobile Money (denishazamuke, Kaggle) | 4.2M rows, M-Pesa-style, CC0 |
| Processing | Python 3.11 + pandas | Chunked reads — handles 4.2M rows without OOM |
| Database | PostgreSQL 15 via Docker | Portable, production-grade RDBMS |
| LLM | OpenAI `gpt-4o-mini` | Text-to-SQL + hallucination detection |
| Backend | FastAPI + uvicorn | Clean REST API between pipeline and UI |
| Frontend | Next.js 15 (App Router) | Streaming-ready chat UI with Tailwind CSS |
| Containers | Docker + docker-compose | One-command full-stack startup |

---

## Prerequisites

- Docker Desktop (or OrbStack)
- Python 3.11
- Node.js 20+
- OpenAI API key

---

## Setup

### Option A — Full Docker (recommended for demo)

```bash
cp .env.example .env
# Edit .env and set OPENAI_API_KEY=sk-...

# Place the source CSV at:
#   data/MoMTSim_20240722202413_1000_dataset.csv

docker compose up
# Opens at http://localhost:3000
```

Everything starts in the correct order:
1. PostgreSQL waits until healthy
2. Pipeline applies schema and loads all 4.2M rows (progress visible in logs)
3. FastAPI starts when pipeline completes
4. Next.js starts when API is healthy

Watch the pipeline load in real time:
```bash
docker compose logs pipeline -f
```

### Option B — Local development

```bash
# 1. Python environment
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. Environment variables
cp .env.example .env
# Edit .env: set OPENAI_API_KEY and confirm POSTGRES_PORT=5433

# 3. Start PostgreSQL
docker compose up postgres -d

# 4. Apply schema + run pipeline
python sql/apply_schema.py
python run_pipeline.py          # ~2 minutes for 4.2M rows
python run_pipeline.py --validate  # dry-run first chunk only

# 5. Start FastAPI backend (terminal 1)
uvicorn api.main:app --host 0.0.0.0 --port 8000

# 6. Start Next.js frontend (terminal 2)
cd frontend && npm install && npm run dev

# Open http://localhost:3000
```

---

## Project Structure

```
├── engine/
│   ├── loader.py          Chunked CSV reader (100k rows/chunk)
│   ├── cleaner.py         Null fills, drop rules, type casts, dedup
│   ├── transformer.py     7 derived columns
│   ├── loader_db.py       PostgreSQL COPY bulk insert
│   ├── aggregator.py      INSERT…SELECT → transaction_summary
│   └── logger.py          Shared logging config
│
├── rag/
│   ├── schema.py          Schema context + few-shot examples for LLM
│   ├── query_gen.py       NL question → SQL (structured JSON output)
│   ├── executor.py        sqlparse validation + read-only transaction
│   ├── hallucination.py   Back-translation check + confidence scoring
│   └── response_gen.py    Query results → grounded natural language answer
│
├── api/
│   └── main.py            FastAPI app (POST /api/chat, GET /health)
│
├── frontend/
│   ├── app/
│   │   ├── page.tsx       Sele the Analyst chat UI
│   │   ├── layout.tsx     Root layout + metadata
│   │   ├── globals.css    Selcom brand colours (red #E2001A / black / white)
│   │   └── api/chat/
│   │       └── route.ts   Next.js route → FastAPI proxy
│   ├── components/
│   │   └── SelcomLogo.tsx Selcom speech-bubble SVG wordmark
│   └── Dockerfile         Node.js multi-stage build
│
├── sql/
│   ├── schema.sql         DDL for both tables and all indexes
│   └── apply_schema.py    Idempotent schema runner
│
├── docs/
│   ├── design/            Architecture, schema, RAG design docs
│   └── implementation/    Phase plans and task backlog
│
├── run_pipeline.py        Pipeline entry point (with tqdm progress bar)
├── Dockerfile             Python backend image
├── docker-compose.yml     Full-stack orchestration
├── requirements.txt       Python dependencies
└── .env.example           Environment variable template
```

---

## Pipeline Design Decisions

### Chunked processing
The source CSV has 4,225,958 rows (~500 MB). Loading it all into RAM would require 2–3 GB for pandas operations. `chunksize=100_000` keeps memory under 200 MB regardless of dataset size — the same code handles 1M or 100M rows.

### PostgreSQL COPY vs INSERT
`COPY FROM STDIN` bypasses the SQL parser per-row: ~80,000 rows/second. `executemany INSERT` calls the parser per row: ~1,000 rows/second. For 4.2M rows that is the difference between 2 minutes and over an hour.

### 7 derived columns

| Column | Formula | Analytical value |
|---|---|---|
| `transaction_hour` | `step % 24` | Detect fraud peaks by hour |
| `transaction_day` | `(step // 24) + 1` | Trend analysis over simulation days |
| `amount_bucket` | SMALL / MEDIUM / LARGE / VERY_LARGE | Group amounts into comparable bands |
| `balance_discrepancy` | `abs((old_bal - amount) - new_bal)` | Ledger integrity check |
| `has_balance_error` | `discrepancy > 0.01` | Flag suspicious rows |
| `is_merchant_recipient` | `recipient LIKE '%-%'` | P2P vs merchant payments |
| `net_recipient_gain` | `new_bal_recipient - old_bal_recipient` | Actual credit vs reported amount |

### Pre-aggregation table
`transaction_summary` holds one row per `(transaction_day, transaction_type)` — 45 rows total. Queries like "fraud rate by type over time" scan 45 rows instead of 4.2M. Computed once after full load via `INSERT … ON CONFLICT DO UPDATE`.

---

## RAG Design Decisions

### Text-to-SQL, not vector RAG
The data is structured and tabular. Vector similarity retrieval is designed for unstructured text documents. For financial records in a relational database, the correct pattern is: question → SQL → execute → ground the answer in real results. The LLM cannot hallucinate a number because it reads from actual database rows.

### Hallucination detection
Every answer goes through three layers:
1. **SQL syntax validation** — sqlparse checks the statement before any DB round-trip
2. **Read-only transaction** — `BEGIN READ ONLY … ROLLBACK` prevents any write even if guardrails fail
3. **Back-translation check** — the generated SQL is sent back to the LLM: "what question does this answer?" The alignment between that and the original question is scored 0–1 and averaged with the LLM's self-confidence to produce the final confidence score shown in the UI

### Confidence scoring
```
final_confidence = (llm_self_confidence + back_translation_alignment) / 2
```
- GREEN  ≥ 80% — HIGH
- YELLOW ≥ 55% — MEDIUM
- RED    < 55% — LOW (review the SQL)

### Security guardrails (three layers)
1. Input validation in the UI (pre-LLM, zero API cost)
2. System prompt forbids non-SELECT and marks unrelated questions `NOT_ANSWERABLE`
3. Python regex blocks `INSERT|UPDATE|DELETE|DROP|TRUNCATE|ALTER|CREATE` before execution
4. DB read-only transaction as final safety net

---

## Sample Questions

```
Give me an overview of this data
What is the total value of fraudulent transfers?
What percentage of TRANSFER transactions are fraudulent?
Which transaction type has the highest average amount?
What is the busiest hour for transaction volume?
Show fraud rate by transaction type
Compare total deposits vs total withdrawals
Which day had the highest number of fraudulent transactions?
What is the largest single fraudulent transaction?
Show balance errors by transaction type
What is the net money flow per simulation day?
Show breakdown of transactions by amount bucket
How many unique merchant accounts received payments?
```

---

## Data Quality

| Metric | Value |
|---|---|
| Source rows | 4,225,958 |
| Rows loaded | 4,225,882 |
| Rows dropped | 76 (null required fields or amount ≤ 0) |
| Transaction types | PAYMENT, TRANSFER, DEPOSIT, WITHDRAWAL, DEBIT |
| Fraud transactions | 2,233,060 (52.84% — all in TRANSFER type) |
| Balance errors | 1,311,444 |
| Simulation days | 9 |
| Summary rows | 45 (9 days × 5 types) |

---

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `POSTGRES_HOST` | PostgreSQL host | `127.0.0.1` |
| `POSTGRES_PORT` | Host port for PostgreSQL | `5433` |
| `POSTGRES_DB` | Database name | `selcom_assessment` |
| `POSTGRES_USER` | Database user | `selcom` |
| `POSTGRES_PASSWORD` | Database password | `selcom_pass` |
| `OPENAI_API_KEY` | OpenAI API key | *(required)* |

---

*Built for the Selcom Paytech Data Engineer pre-interview assessment. Deadline: 2026-07-17.*
