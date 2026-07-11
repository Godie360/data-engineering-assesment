-- Table: mobile_money_transactions
-- Stores cleaned and enriched transaction records from the synthetic mobile money dataset.
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

-- Table: transaction_summary
-- Pre-aggregated metrics per (transaction_day, transaction_type).
-- Computed once after the full load; enables fast analytical queries without scanning 4.2M rows.
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
