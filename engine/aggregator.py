"""Computes transaction_summary from the fully-loaded mobile_money_transactions table."""
import psycopg2

from engine.logger import get_logger

logger = get_logger(__name__)

_AGGREGATE_SQL = """
INSERT INTO transaction_summary (
    transaction_day,
    transaction_type,
    transaction_count,
    total_amount,
    avg_amount,
    max_amount,
    fraud_count,
    fraud_total_amount,
    fraud_rate,
    balance_error_count,
    merchant_recipient_count,
    computed_at
)
SELECT
    transaction_day,
    transaction_type,
    COUNT(*)                                            AS transaction_count,
    ROUND(SUM(amount)::NUMERIC, 2)                     AS total_amount,
    ROUND(AVG(amount)::NUMERIC, 2)                     AS avg_amount,
    ROUND(MAX(amount)::NUMERIC, 2)                     AS max_amount,
    COUNT(*) FILTER (WHERE is_fraud)                   AS fraud_count,
    COALESCE(ROUND(SUM(amount) FILTER (WHERE is_fraud)::NUMERIC, 2), 0) AS fraud_total_amount,
    ROUND(
        (COUNT(*) FILTER (WHERE is_fraud))::NUMERIC
        / NULLIF(COUNT(*), 0),
        4
    )                                                  AS fraud_rate,
    COUNT(*) FILTER (WHERE has_balance_error)          AS balance_error_count,
    COUNT(*) FILTER (WHERE is_merchant_recipient)      AS merchant_recipient_count,
    NOW()                                              AS computed_at
FROM mobile_money_transactions
GROUP BY transaction_day, transaction_type
ON CONFLICT (transaction_day, transaction_type) DO UPDATE SET
    transaction_count        = EXCLUDED.transaction_count,
    total_amount             = EXCLUDED.total_amount,
    avg_amount               = EXCLUDED.avg_amount,
    max_amount               = EXCLUDED.max_amount,
    fraud_count              = EXCLUDED.fraud_count,
    fraud_total_amount       = EXCLUDED.fraud_total_amount,
    fraud_rate               = EXCLUDED.fraud_rate,
    balance_error_count      = EXCLUDED.balance_error_count,
    merchant_recipient_count = EXCLUDED.merchant_recipient_count,
    computed_at              = EXCLUDED.computed_at;
"""


def build_summary(conn: psycopg2.extensions.connection) -> None:
    """Runs the aggregation query and commits. Idempotent via ON CONFLICT DO UPDATE."""
    with conn.cursor() as cur:
        cur.execute(_AGGREGATE_SQL)
        rows = cur.rowcount
    conn.commit()
    logger.info("transaction_summary: %d rows upserted", rows)
