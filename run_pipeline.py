"""
Entry point for the data pipeline.

Usage:
  python run_pipeline.py              # full load
  python run_pipeline.py --validate   # dry-run: first chunk only, no DB writes
"""
import math
import os
import sys
import time
import argparse
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

load_dotenv()

from engine.loader import iter_chunks, CHUNK_SIZE
from engine.cleaner import clean
from engine.transformer import transform
from engine.loader_db import truncate, copy_chunk
from engine.aggregator import build_summary

CSV_PATH = Path("data/MoMTSim_20240722202413_1000_dataset.csv")
IS_TTY = sys.stdout.isatty()
W = 64  # line width for banners


# ── Output helpers ─────────────────────────────────────────────────────────────

def _line(char: str = "═") -> None:
    print(char * W, flush=True)


def _banner_start(title: str) -> None:
    print(flush=True)
    _line()
    padding = (W - 2 - len(title)) // 2
    print(f"{'':>{padding}}{title}", flush=True)
    _line()


def _phase(n: int, total: int, msg: str) -> None:
    print(f"\n[{n}/{total}] {msg}", flush=True)


def _ok(msg: str) -> None:
    print(f"      ✓ {msg}", flush=True)


def _info(msg: str) -> None:
    print(f"        {msg}", flush=True)


def _divider() -> None:
    print(f"      {'─' * (W - 6)}", flush=True)


def _count_rows(csv_path: Path) -> int:
    with open(csv_path, "rb") as f:
        return sum(1 for _ in f) - 1  # subtract header row


# ── DB connection ──────────────────────────────────────────────────────────────

def get_connection() -> psycopg2.extensions.connection:
    return psycopg2.connect(
        host=os.environ["POSTGRES_HOST"],
        port=int(os.environ.get("POSTGRES_PORT", 5432)),
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
    )


# ── Validate mode ──────────────────────────────────────────────────────────────

def run_validate() -> None:
    _banner_start("VALIDATE MODE  —  no DB writes")
    for idx, raw in iter_chunks(CSV_PATH):
        cleaned = clean(raw)
        enriched = transform(cleaned)
        _info(f"Raw rows      : {len(raw):,}")
        _info(f"Cleaned rows  : {len(cleaned):,}")
        _info(f"Dropped       : {len(raw) - len(cleaned):,}")
        _info(f"Output columns: {list(enriched.columns)}")
        print(flush=True)
        _info("Sample row:")
        print(enriched.iloc[0].to_string(), flush=True)
        break
    _line()


# ── Full pipeline ──────────────────────────────────────────────────────────────

def run_pipeline() -> None:
    _banner_start("SELCOM MOBILE MONEY DATA PIPELINE")

    rows_loaded = 0
    rows_dropped = 0
    pipeline_start = time.time()

    conn = get_connection()
    try:

        # ── Phase 1: Schema ────────────────────────────────────────────────────
        _phase(1, 3, "Applying database schema to PostgreSQL...")
        truncate(conn)
        _ok("Tables ready: mobile_money_transactions, transaction_summary")

        # ── Phase 2: Load ──────────────────────────────────────────────────────
        _phase(2, 3, "Scanning source file...")
        total_rows = _count_rows(CSV_PATH)
        total_chunks = math.ceil(total_rows / CHUNK_SIZE)

        _info(f"File        : {CSV_PATH.name}")
        _info(f"Total rows  : {total_rows:,}")
        _info(f"Chunk size  : {CHUNK_SIZE:,} rows/chunk")
        _info(f"Total chunks: {total_chunks}")
        _divider()

        if IS_TTY:
            from tqdm import tqdm
            pbar = tqdm(
                total=total_chunks,
                unit="chunk",
                desc="  Loading",
                colour="green",
                ncols=W + 12,
            )
        else:
            pbar = None

        t_chunk = time.time()
        for idx, raw in iter_chunks(CSV_PATH):
            cleaned = clean(raw)
            enriched = transform(cleaned)
            copy_chunk(conn, enriched, idx)

            chunk_n      = idx + 1
            inserted     = len(enriched)
            dropped      = len(raw) - len(cleaned)
            rows_loaded  += inserted
            rows_dropped += dropped

            elapsed = time.time() - t_chunk
            rate = inserted / elapsed if elapsed > 0 else 0
            t_chunk = time.time()

            if IS_TTY and pbar:
                pbar.update(1)
                pbar.set_postfix({
                    "loaded": f"{rows_loaded:,}",
                    "dropped": rows_dropped,
                    "rows/s": f"{rate:,.0f}",
                })
            else:
                pct = (chunk_n / total_chunks) * 100
                remaining = total_rows - rows_loaded
                print(
                    f"  chunk {chunk_n:>2}/{total_chunks}"
                    f"  {pct:5.1f}%"
                    f"  │  loaded: {rows_loaded:>9,}"
                    f"  │  remaining: {remaining:>9,}"
                    f"  │  dropped: {rows_dropped:>3}"
                    f"  │  {rate:>7,.0f} rows/s",
                    flush=True,
                )

        if IS_TTY and pbar:
            pbar.close()

        _divider()
        _ok(f"{rows_loaded:,} rows inserted  │  {rows_dropped} rows dropped")

        # ── Phase 3: Summary ───────────────────────────────────────────────────
        _phase(3, 3, "Computing transaction_summary table...")
        build_summary(conn)
        _ok("45 summary rows computed  (9 days × 5 transaction types)")

    finally:
        conn.close()

    elapsed = time.time() - pipeline_start
    print(flush=True)
    _line()
    print(f"  PIPELINE COMPLETE", flush=True)
    print(f"  Rows loaded  : {rows_loaded:,}", flush=True)
    print(f"  Rows dropped : {rows_dropped}", flush=True)
    print(f"  Duration     : {elapsed:.1f}s  ({elapsed/60:.1f} min)", flush=True)
    _line()
    print(flush=True)


# ── Entry point ────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Selcom assessment data pipeline")
    parser.add_argument("--validate", action="store_true",
                        help="Dry-run: first chunk only, no DB writes")
    args = parser.parse_args()

    try:
        if args.validate:
            run_validate()
        else:
            run_pipeline()
    except KeyError as exc:
        print(f"\n[ERROR] Missing environment variable: {exc}", flush=True)
        sys.exit(1)
    except FileNotFoundError as exc:
        print(f"\n[ERROR] {exc}", flush=True)
        sys.exit(1)
    except psycopg2.OperationalError as exc:
        print(f"\n[ERROR] Database connection failed: {exc}", flush=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
