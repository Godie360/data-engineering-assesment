"""Applies null fills, type casts, deduplication, and drop rules to a raw chunk."""
import pandas as pd

from engine.logger import get_logger

logger = get_logger(__name__)

VALID_TYPES = {"PAYMENT", "TRANSFER", "DEPOSIT", "WITHDRAWAL", "DEBIT"}


def clean(df: pd.DataFrame) -> pd.DataFrame:
    initial = len(df)

    # ── Normalise transaction type first so validity check works ──────────────
    df["transactionType"] = df["transactionType"].str.strip().str.upper()

    # ── Drop rows that cannot be recovered ───────────────────────────────────
    df = df.dropna(subset=["step", "transactionType", "amount", "initiator", "recipient"])
    df = df[df["amount"] > 0]
    df = df[df["transactionType"].isin(VALID_TYPES)]

    # ── Fill recoverable nulls ────────────────────────────────────────────────
    for col in ["oldBalInitiator", "newBalInitiator", "oldBalRecipient", "newBalRecipient"]:
        df[col] = df[col].fillna(0.0)
    df["isFraud"] = df["isFraud"].fillna(0)

    # ── Type casts ───────────────────────────────────────────────────────────
    df["step"] = df["step"].astype(int)
    df["isFraud"] = df["isFraud"].astype(bool)
    for col in ["amount", "oldBalInitiator", "newBalInitiator",
                "oldBalRecipient", "newBalRecipient"]:
        df[col] = df[col].astype(float)

    # ── Deduplicate within chunk ──────────────────────────────────────────────
    df = df.drop_duplicates()

    dropped = initial - len(df)
    if dropped:
        logger.info("Dropped %d rows during cleaning (chunk of %d)", dropped, initial)

    return df.reset_index(drop=True)
