"""Bulk-inserts a transformed chunk into mobile_money_transactions via PostgreSQL COPY."""
import io

import psycopg2

from engine.logger import get_logger

logger = get_logger(__name__)

# Maps transformed DataFrame column names → DB column names
_RENAME = {
    "transactionType": "transaction_type",
    "oldBalInitiator": "old_bal_initiator",
    "newBalInitiator": "new_bal_initiator",
    "oldBalRecipient": "old_bal_recipient",
    "newBalRecipient": "new_bal_recipient",
    "isFraud": "is_fraud",
}

# Ordered list of DB columns to write (excludes id and loaded_at which are DB-generated)
_DB_COLUMNS = [
    "step",
    "transaction_hour",
    "transaction_day",
    "transaction_type",
    "amount",
    "amount_bucket",
    "initiator",
    "old_bal_initiator",
    "new_bal_initiator",
    "recipient",
    "old_bal_recipient",
    "new_bal_recipient",
    "is_merchant_recipient",
    "net_recipient_gain",
    "balance_discrepancy",
    "has_balance_error",
    "is_fraud",
]

_COPY_SQL = (
    "COPY mobile_money_transactions ("
    + ", ".join(_DB_COLUMNS)
    + ") FROM STDIN WITH (FORMAT CSV, HEADER TRUE, NULL '')"
)


def truncate(conn: psycopg2.extensions.connection) -> None:
    """Removes all rows and resets the sequence. Called once before the first chunk."""
    with conn.cursor() as cur:
        cur.execute(
            "TRUNCATE TABLE mobile_money_transactions RESTART IDENTITY CASCADE"
        )
    conn.commit()
    logger.info("Truncated mobile_money_transactions")


def copy_chunk(conn: psycopg2.extensions.connection, df, chunk_idx: int) -> None:
    """Writes one transformed chunk to the DB using COPY FROM STDIN."""
    df = df.rename(columns=_RENAME)[_DB_COLUMNS]

    buf = io.StringIO()
    df.to_csv(buf, index=False)
    buf.seek(0)

    with conn.cursor() as cur:
        cur.copy_expert(_COPY_SQL, buf)
    conn.commit()

    logger.info("Inserted chunk %d: %d rows", chunk_idx, len(df))
