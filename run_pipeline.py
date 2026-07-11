"""
Entry point for the data pipeline.

Usage:
  python run_pipeline.py              # full load
  python run_pipeline.py --validate   # dry-run: prints counts and a sample row
"""
import os
import sys
import time
import argparse
from pathlib import Path

import psycopg2
from dotenv import load_dotenv
from tqdm import tqdm

load_dotenv()

from engine.loader import iter_chunks
from engine.cleaner import clean
from engine.transformer import transform
from engine.loader_db import truncate, copy_chunk
from engine.aggregator import build_summary
from engine.logger import get_logger

logger = get_logger("pipeline")

CSV_PATH = Path("data/MoMTSim_20240722202413_1000_dataset.csv")


def get_connection() -> psycopg2.extensions.connection:
    return psycopg2.connect(
        host=os.environ["POSTGRES_HOST"],
        port=int(os.environ.get("POSTGRES_PORT", 5432)),
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
    )


def run_validate() -> None:
    """Dry-run: load first chunk, clean, transform, print stats. No DB writes."""
    logger.info("=== VALIDATE MODE (no DB writes) ===")
    for idx, raw in iter_chunks(CSV_PATH):
        cleaned = clean(raw)
        enriched = transform(cleaned)
        logger.info("Raw rows:     %d", len(raw))
        logger.info("Cleaned rows: %d", len(cleaned))
        logger.info("Columns: %s", list(enriched.columns))
        logger.info("Sample row:\n%s", enriched.iloc[0].to_string())
        break  # only first chunk


def run_pipeline() -> None:
    logger.info("=== PIPELINE START ===")
    start = time.time()

    conn = get_connection()
    try:
        truncate(conn)

        total_rows = 0
        total_dropped = 0

        with tqdm(unit="chunk", desc="Loading chunks", colour="green", dynamic_ncols=True) as pbar:
            for idx, raw in iter_chunks(CSV_PATH):
                cleaned = clean(raw)
                enriched = transform(cleaned)
                copy_chunk(conn, enriched, idx)

                chunk_inserted = len(enriched)
                chunk_dropped = len(raw) - len(cleaned)
                total_rows += chunk_inserted
                total_dropped += chunk_dropped

                pbar.update(1)
                pbar.set_postfix({
                    "rows_loaded": f"{total_rows:,}",
                    "dropped": total_dropped,
                    "this_chunk": chunk_inserted,
                })

        logger.info(
            "All chunks loaded — inserted: %d, dropped: %d", total_rows, total_dropped
        )

        logger.info("Building transaction_summary ...")
        build_summary(conn)

    finally:
        conn.close()

    elapsed = time.time() - start
    logger.info("=== PIPELINE COMPLETE in %.1fs ===", elapsed)


def main() -> None:
    parser = argparse.ArgumentParser(description="Selcom assessment data pipeline")
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Dry-run: process first chunk only, print stats, no DB writes",
    )
    args = parser.parse_args()

    try:
        if args.validate:
            run_validate()
        else:
            run_pipeline()
    except KeyError as exc:
        logger.error("Missing environment variable: %s", exc)
        sys.exit(1)
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        sys.exit(1)
    except psycopg2.OperationalError as exc:
        logger.error("Database connection failed: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
