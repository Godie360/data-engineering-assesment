# Transaction Schema

## Dataset Source

- **Name**: Synthetic Mobile Money Transaction Dataset
- **Author**: denishazamuke
- **URL**: https://www.kaggle.com/datasets/denishazamuke/synthetic-mobile-money-transaction-dataset
- **License**: CC0 (Public Domain) — no restrictions on use, distribution, or modification
- **Usage confirmation**: Public dataset, synthetic only, no real personal or confidential data
- **File**: `data/MoMTSim_20240722202413_1000_dataset.csv`
- **Rows**: 4,225,958
- **Columns**: 10
- **Domain**: Synthetic East African mobile money transactions (M-Pesa-style)

---

## Table: mobile_money_transactions

### Source Columns (from CSV)

| CSV Column | DB Column | Type | Null Rule |
|---|---|---|---|
| step | step | SMALLINT NOT NULL | Drop row if null; 0-based (step 0 = hour 0 of day 1) |
| transactionType | transaction_type | VARCHAR(12) NOT NULL | Drop row if null; uppercase, strip whitespace |
| amount | amount | NUMERIC(18,2) NOT NULL | Drop row if null or ≤ 0 |
| initiator | initiator | VARCHAR(25) NOT NULL | Drop row if null |
| oldBalInitiator | old_bal_initiator | NUMERIC(18,2) NOT NULL | Fill null with 0.00 |
| newBalInitiator | new_bal_initiator | NUMERIC(18,2) NOT NULL | Fill null with 0.00 |
| recipient | recipient | VARCHAR(25) NOT NULL | Drop row if null |
| oldBalRecipient | old_bal_recipient | NUMERIC(18,2) NOT NULL | Fill null with 0.00 |
| newBalRecipient | new_bal_recipient | NUMERIC(18,2) NOT NULL | Fill null with 0.00 |
| isFraud | is_fraud | BOOLEAN NOT NULL | Fill null with FALSE; cast 0/1 int to bool |

**Null fill rationale**: balance columns are filled with 0.00 when null — operationally a null balance means no prior record, equivalent to zero. This preserves the row and keeps derived calculations valid.

**Valid transaction_type values**: PAYMENT, TRANSFER, DEPOSIT, WITHDRAWAL, DEBIT

---

### Derived Columns

| Column | Type | Logic |
|---|---|---|
| transaction_hour | SMALLINT | `step % 24` — hour of day (0–23) |
| transaction_day | SMALLINT | `(step // 24) + 1` — simulation day (1-based) |
| amount_bucket | VARCHAR(12) | Standardisation: SMALL (<1,000) / MEDIUM (1k–10k) / LARGE (10k–100k) / VERY_LARGE (>100k) — groups raw amounts into comparable bands for analysis |
| balance_discrepancy | NUMERIC(18,4) | `abs((old_bal_initiator - amount) - new_bal_initiator)` — ledger inconsistency |
| has_balance_error | BOOLEAN | `balance_discrepancy > 0.01` |
| is_merchant_recipient | BOOLEAN | `recipient LIKE '%-%'` — merchant accounts use hyphenated IDs (e.g. 30-0000345) |
| net_recipient_gain | NUMERIC(18,2) | `new_bal_recipient - old_bal_recipient` — actual credit received |

---

### System Columns

| Column | Type | Value |
|---|---|---|
| id | BIGSERIAL | Auto-increment primary key |
| loaded_at | TIMESTAMPTZ | `NOW()` at insert time |

---

## Table: transaction_summary

Aggregated after all chunks are loaded. One row per `(transaction_day, transaction_type)`.

**Purpose**: enables fast analytical queries without scanning 4.2M rows; demonstrates aggregation as required by the assessment.

### Columns

| Column | Type | Description |
|---|---|---|
| id | SERIAL | Primary key |
| transaction_day | SMALLINT NOT NULL | Simulation day (1-based) |
| transaction_type | VARCHAR(12) NOT NULL | Transaction type |
| transaction_count | INTEGER NOT NULL | Number of transactions |
| total_amount | NUMERIC(18,2) NOT NULL | Sum of all amounts |
| avg_amount | NUMERIC(18,2) NOT NULL | Average amount |
| max_amount | NUMERIC(18,2) NOT NULL | Largest single transaction |
| fraud_count | INTEGER NOT NULL | Rows where is_fraud = TRUE |
| fraud_total_amount | NUMERIC(18,2) NOT NULL | Sum of fraudulent amounts |
| fraud_rate | NUMERIC(6,4) NOT NULL | fraud_count / transaction_count |
| balance_error_count | INTEGER NOT NULL | Rows where has_balance_error = TRUE |
| merchant_recipient_count | INTEGER NOT NULL | Rows where is_merchant_recipient = TRUE |
| computed_at | TIMESTAMPTZ NOT NULL | Timestamp of computation |

**Unique constraint**: `UNIQUE (transaction_day, transaction_type)`

---

## DDL

File: `sql/schema.sql`

```sql
CREATE TABLE IF NOT EXISTS mobile_money_transactions (
    id                    BIGSERIAL PRIMARY KEY,
    step                  SMALLINT       NOT NULL,
    transaction_hour      SMALLINT       NOT NULL,
    transaction_day       SMALLINT       NOT NULL,
    transaction_type      VARCHAR(12)    NOT NULL,
    amount                NUMERIC(18,2)  NOT NULL,
    amount_bucket         VARCHAR(12)    NOT NULL,
    initiator             VARCHAR(25)    NOT NULL,
    old_bal_initiator     NUMERIC(18,2)  NOT NULL,
    new_bal_initiator     NUMERIC(18,2)  NOT NULL,
    recipient             VARCHAR(25)    NOT NULL,
    old_bal_recipient     NUMERIC(18,2)  NOT NULL,
    new_bal_recipient     NUMERIC(18,2)  NOT NULL,
    is_merchant_recipient BOOLEAN        NOT NULL DEFAULT FALSE,
    net_recipient_gain    NUMERIC(18,2)  NOT NULL,
    balance_discrepancy   NUMERIC(18,4)  NOT NULL,
    has_balance_error     BOOLEAN        NOT NULL DEFAULT FALSE,
    is_fraud              BOOLEAN        NOT NULL DEFAULT FALSE,
    loaded_at             TIMESTAMPTZ    NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_mmt_type          ON mobile_money_transactions(transaction_type);
CREATE INDEX IF NOT EXISTS idx_mmt_is_fraud      ON mobile_money_transactions(is_fraud);
CREATE INDEX IF NOT EXISTS idx_mmt_amount_bucket ON mobile_money_transactions(amount_bucket);
CREATE INDEX IF NOT EXISTS idx_mmt_step          ON mobile_money_transactions(step);
CREATE INDEX IF NOT EXISTS idx_mmt_hour          ON mobile_money_transactions(transaction_hour);
CREATE INDEX IF NOT EXISTS idx_mmt_day           ON mobile_money_transactions(transaction_day);

CREATE TABLE IF NOT EXISTS transaction_summary (
    id                       SERIAL PRIMARY KEY,
    transaction_day          SMALLINT       NOT NULL,
    transaction_type         VARCHAR(12)    NOT NULL,
    transaction_count        INTEGER        NOT NULL,
    total_amount             NUMERIC(18,2)  NOT NULL,
    avg_amount               NUMERIC(18,2)  NOT NULL,
    max_amount               NUMERIC(18,2)  NOT NULL,
    fraud_count              INTEGER        NOT NULL,
    fraud_total_amount       NUMERIC(18,2)  NOT NULL,
    fraud_rate               NUMERIC(6,4)   NOT NULL,
    balance_error_count      INTEGER        NOT NULL,
    merchant_recipient_count INTEGER        NOT NULL,
    computed_at              TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
    UNIQUE (transaction_day, transaction_type)
);

CREATE INDEX IF NOT EXISTS idx_ts_day  ON transaction_summary(transaction_day);
CREATE INDEX IF NOT EXISTS idx_ts_type ON transaction_summary(transaction_type);
```

---

## Load Strategy

### mobile_money_transactions
- Method: `COPY` via `psycopg2.copy_expert` with `io.StringIO` buffer
- Idempotency: `TRUNCATE TABLE mobile_money_transactions RESTART IDENTITY CASCADE` before each full load
- Chunk size: 100,000 rows per chunk
- Type enforcement: all casts and null fills applied in Python before COPY

### transaction_summary
- Method: single `INSERT ... ON CONFLICT DO UPDATE` aggregation query after all chunks loaded
- Source: `mobile_money_transactions`
- Idempotency: `CASCADE` on main table TRUNCATE clears this table automatically
