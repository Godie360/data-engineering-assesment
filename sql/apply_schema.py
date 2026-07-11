"""Applies sql/schema.sql to the configured PostgreSQL database. Idempotent."""
import os
import sys
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

load_dotenv()

DDL_FILE = Path(__file__).parent / "schema.sql"


def get_connection():
    return psycopg2.connect(
        host=os.environ["POSTGRES_HOST"],
        port=int(os.environ.get("POSTGRES_PORT", 5432)),
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
    )


def apply_schema():
    ddl = DDL_FILE.read_text()
    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(ddl)
        print("Schema applied successfully.")
    finally:
        conn.close()


if __name__ == "__main__":
    try:
        apply_schema()
    except KeyError as e:
        print(f"Missing environment variable: {e}")
        sys.exit(1)
    except psycopg2.OperationalError as e:
        print(f"Database connection failed: {e}")
        sys.exit(1)
