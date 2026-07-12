"""Reads the source CSV in fixed-size chunks. No cleaning or transformation here."""
from pathlib import Path
from typing import Iterator

import pandas as pd

from engine.logger import get_logger

logger = get_logger(__name__)

CHUNK_SIZE = 100_000

# Exact column names in the source CSV
CSV_COLUMNS = [
    "step",
    "transactionType",
    "amount",
    "initiator",
    "oldBalInitiator",
    "newBalInitiator",
    "recipient",
    "oldBalRecipient",
    "newBalRecipient",
    "isFraud",
]

# Dtypes for efficient reading (avoids pandas guessing on 4.2M rows)
DTYPE_MAP = {
    "step": "Int32",
    "transactionType": "object",
    "amount": "float64",
    "initiator": "object",
    "oldBalInitiator": "float64",
    "newBalInitiator": "float64",
    "recipient": "object",
    "oldBalRecipient": "float64",
    "newBalRecipient": "float64",
    "isFraud": "Int8",
}


def iter_chunks(csv_path: str | Path) -> Iterator[tuple[int, pd.DataFrame]]:
    """Yields (chunk_index, DataFrame) for each 100k-row chunk of the CSV."""
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    reader = pd.read_csv(
        csv_path,
        usecols=CSV_COLUMNS,
        dtype=DTYPE_MAP,
        chunksize=CHUNK_SIZE,
    )
    for idx, chunk in enumerate(reader):
        yield idx, chunk
