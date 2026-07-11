"""Provides a concise schema context string for both PostgreSQL tables."""

SCHEMA_CONTEXT = """
You are querying a PostgreSQL database with two tables about synthetic East African mobile money transactions (M-Pesa-style).

TABLE: mobile_money_transactions
  Primary analysis table — one row per transaction (4.2 million rows).

  Columns:
    id                    BIGSERIAL       — auto-increment primary key
    step                  SMALLINT        — simulation time step (hour 0 = step 0)
    transaction_hour      SMALLINT        — hour of day (0–23), derived: step % 24
    transaction_day       SMALLINT        — simulation day (1-based), derived: (step // 24) + 1
    transaction_type      VARCHAR(12)     — one of: PAYMENT, TRANSFER, DEPOSIT, WITHDRAWAL, DEBIT
    amount                NUMERIC(18,2)   — transaction amount in local currency
    amount_bucket         VARCHAR(12)     — SMALL (<1000), MEDIUM (1k–10k), LARGE (10k–100k), VERY_LARGE (>100k)
    initiator             VARCHAR(25)     — account ID of the sender
    old_bal_initiator     NUMERIC(18,2)   — sender balance before transaction
    new_bal_initiator     NUMERIC(18,2)   — sender balance after transaction
    recipient             VARCHAR(25)     — account ID of the receiver
    old_bal_recipient     NUMERIC(18,2)   — receiver balance before transaction
    new_bal_recipient     NUMERIC(18,2)   — receiver balance after transaction
    is_merchant_recipient BOOLEAN         — TRUE if recipient is a merchant (account ID contains '-')
    net_recipient_gain    NUMERIC(18,2)   — new_bal_recipient - old_bal_recipient
    balance_discrepancy   NUMERIC(18,4)   — abs((old_bal_initiator - amount) - new_bal_initiator); ledger inconsistency
    has_balance_error     BOOLEAN         — TRUE if balance_discrepancy > 0.01
    is_fraud              BOOLEAN         — TRUE if the transaction is labelled fraudulent
    loaded_at             TIMESTAMPTZ     — when the row was loaded into the DB

  Indexes: transaction_type, is_fraud, amount_bucket, step, transaction_hour, transaction_day

TABLE: transaction_summary
  Pre-aggregated summary — one row per (transaction_day, transaction_type). Use this for fast day/type analytics.

  Columns:
    id                       SERIAL          — primary key
    transaction_day          SMALLINT        — simulation day (1-based)
    transaction_type         VARCHAR(12)     — PAYMENT, TRANSFER, DEPOSIT, WITHDRAWAL, or DEBIT
    transaction_count        INTEGER         — number of transactions for that day+type
    total_amount             NUMERIC(18,2)   — sum of all amounts for that day+type
    avg_amount               NUMERIC(18,2)   — average amount
    max_amount               NUMERIC(18,2)   — largest single transaction
    fraud_count              INTEGER         — count of fraudulent transactions
    fraud_total_amount       NUMERIC(18,2)   — total amount of fraudulent transactions
    fraud_rate               NUMERIC(6,4)    — fraud_count / transaction_count (0.0000 to 1.0000)
    balance_error_count      INTEGER         — count of transactions with balance discrepancies
    merchant_recipient_count INTEGER         — count of transactions to merchant accounts
    computed_at              TIMESTAMPTZ     — when this summary row was computed

TABLE SELECTION RULES — READ CAREFULLY:
- transaction_summary groups by (transaction_day, transaction_type) ONLY.
  It has NO transaction_hour column. Never query transaction_hour from transaction_summary.
- Use transaction_summary ONLY for questions about: daily totals, per-type aggregates, fraud_rate, daily fraud counts.
- Use mobile_money_transactions for: hour-of-day analysis, per-account queries, individual row filters,
  balance errors, merchant recipient patterns, or any column not in transaction_summary.
- transaction_type values are uppercase: 'PAYMENT', 'TRANSFER', 'DEPOSIT', 'WITHDRAWAL', 'DEBIT'.
- is_fraud, has_balance_error, is_merchant_recipient are BOOLEAN — use TRUE/FALSE (not 1/0).
- Always use lowercase column names exactly as listed above.

FEW-SHOT EXAMPLES (question → correct SQL):

Q: What is the total amount of fraudulent transfers?
SQL: SELECT SUM(amount) AS total_fraud_amount FROM mobile_money_transactions WHERE transaction_type = 'TRANSFER' AND is_fraud = TRUE

Q: Which hour of the day has the most transactions? / What is the busiest hour for transaction volume?
SQL: SELECT transaction_hour, COUNT(*) AS transaction_count, SUM(amount) AS total_volume FROM mobile_money_transactions GROUP BY transaction_hour ORDER BY transaction_count DESC LIMIT 5

Q: What is the fraud rate for each transaction type?
SQL: SELECT transaction_type, AVG(fraud_rate) AS avg_fraud_rate FROM transaction_summary GROUP BY transaction_type ORDER BY avg_fraud_rate DESC

Q: How many transactions have balance errors?
SQL: SELECT COUNT(*) AS balance_error_count FROM mobile_money_transactions WHERE has_balance_error = TRUE

Q: Compare total transaction volume per day
SQL: SELECT transaction_day, SUM(total_amount) AS daily_volume, SUM(transaction_count) AS daily_count FROM transaction_summary GROUP BY transaction_day ORDER BY transaction_day

Q: What is the breakdown of transactions by amount bucket?
SQL: SELECT amount_bucket, COUNT(*) AS count, SUM(amount) AS total_amount FROM mobile_money_transactions GROUP BY amount_bucket ORDER BY total_amount DESC

Q: Give me an overview of this data / summarise the dataset / what does the data look like?
SQL: SELECT COUNT(*) AS total_transactions, ROUND(SUM(amount)::NUMERIC, 2) AS total_volume, ROUND(AVG(amount)::NUMERIC, 2) AS avg_amount, COUNT(*) FILTER (WHERE is_fraud) AS fraud_transactions, ROUND(COUNT(*) FILTER (WHERE is_fraud) * 100.0 / COUNT(*), 2) AS fraud_rate_pct, COUNT(*) FILTER (WHERE has_balance_error) AS balance_errors, COUNT(DISTINCT transaction_type) AS transaction_types, COUNT(DISTINCT transaction_day) AS simulation_days FROM mobile_money_transactions
""".strip()


def get_schema_context() -> str:
    return SCHEMA_CONTEXT
