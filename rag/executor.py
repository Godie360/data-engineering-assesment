"""
Executes a SQL SELECT against PostgreSQL with two safety layers:
  1. sqlparse syntax validation before sending to the DB
  2. Read-only transaction — even if a dangerous query slips through guardrails,
     the DB rolls back automatically and the read-only session prevents writes.
"""
import psycopg2
import psycopg2.extras
import sqlparse

from engine.logger import get_logger

logger = get_logger(__name__)

MAX_ROWS = 500


def validate_syntax(sql: str) -> None:
    """
    Raises ValueError if sqlparse cannot parse the statement or detects
    it is not a SELECT. This runs before any DB round-trip.
    """
    parsed = sqlparse.parse(sql)
    if not parsed:
        raise ValueError("SQL is empty or could not be parsed.")

    stmt = parsed[0]
    stmt_type = stmt.get_type()
    if stmt_type != "SELECT":
        raise ValueError(
            f"Only SELECT statements are allowed. Detected type: {stmt_type or 'UNKNOWN'}"
        )


def execute_query(
    sql: str, conn: psycopg2.extensions.connection
) -> list[dict]:
    """
    Validates syntax, then executes in a read-only transaction.
    Returns up to MAX_ROWS rows as dicts. Raises on error.
    """
    validate_syntax(sql)

    limited_sql = f"SELECT * FROM ({sql}) _q LIMIT {MAX_ROWS}"

    # Read-only transaction: DB will reject any write attempt even if guardrails missed it
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        try:
            cur.execute("BEGIN READ ONLY")
            cur.execute(limited_sql)
            rows = cur.fetchall()
            cur.execute("ROLLBACK")  # always roll back — we never commit reads
        except psycopg2.Error as exc:
            conn.rollback()
            logger.error("SQL execution failed: %s", exc)
            raise

    logger.info("Query returned %d rows", len(rows))
    return [dict(row) for row in rows]
