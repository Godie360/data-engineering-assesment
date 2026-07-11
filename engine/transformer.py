"""Adds 7 derived columns to a cleaned chunk. No DB writes or cleaning here."""
import pandas as pd

from engine.logger import get_logger

logger = get_logger(__name__)


def _amount_bucket(amount: pd.Series) -> pd.Series:
    bins = [0, 1_000, 10_000, 100_000, float("inf")]
    labels = ["SMALL", "MEDIUM", "LARGE", "VERY_LARGE"]
    return pd.cut(amount, bins=bins, labels=labels, right=False).astype(str)


def transform(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df["transaction_hour"] = (df["step"] % 24).astype(int)
    df["transaction_day"] = ((df["step"] // 24) + 1).astype(int)

    df["amount_bucket"] = _amount_bucket(df["amount"])

    df["balance_discrepancy"] = (
        (df["oldBalInitiator"] - df["amount"]) - df["newBalInitiator"]
    ).abs()

    df["has_balance_error"] = df["balance_discrepancy"] > 0.01

    # Merchant account IDs contain a hyphen, e.g. "30-0000345"
    df["is_merchant_recipient"] = df["recipient"].str.contains("-", na=False)

    df["net_recipient_gain"] = df["newBalRecipient"] - df["oldBalRecipient"]

    logger.info("Transformed chunk: %d rows, 7 derived columns added", len(df))
    return df
