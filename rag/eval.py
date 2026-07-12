"""
Offline eval for the RAG pipeline.

Runs a fixed set of questions against the live database and checks:
  - question_type routing is correct
  - data queries return HIGH or MEDIUM confidence
  - out-of-scope questions are blocked
  - SQL contains expected keywords

Usage:
  python rag/eval.py

Requires .env with POSTGRES_* and OPENAI_API_KEY set.
"""
import os
import sys
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

import psycopg2
from openai import OpenAI
from psycopg2.pool import ThreadedConnectionPool

from rag.graph import build_graph

# ── Test cases ────────────────────────────────────────────────────────────────

@dataclass
class Case:
    question: str
    expect_type: str                  # "data_query" | "clarification" | "not_answerable"
    min_confidence: Optional[float]   # None = don't check (clarification / blocked)
    sql_must_contain: Optional[str]   # substring expected in generated SQL


CASES: list[Case] = [
    # Data queries — must return HIGH/MEDIUM confidence
    Case("Give me an overview of this data",
         "data_query", 0.70, "COUNT(*)"),
    Case("What is the total value of fraudulent transfers?",
         "data_query", 0.75, "is_fraud"),
    Case("Which transaction type has the highest average amount?",
         "data_query", 0.75, "AVG"),
    Case("What is the busiest hour for transaction volume?",
         "data_query", 0.75, "transaction_hour"),
    Case("Show fraud rate by transaction type",
         "data_query", 0.70, "fraud_rate"),
    Case("Compare total deposits vs total withdrawals",
         "data_query", 0.70, "transaction_type"),
    Case("Which day had the highest number of fraudulent transactions?",
         "data_query", 0.70, "transaction_day"),
    Case("How many transactions have balance errors?",
         "data_query", 0.75, "has_balance_error"),

    # Out-of-scope — must be blocked
    Case("Who is Elon Musk?",          "not_answerable", None, None),
    Case("What is the weather today?", "not_answerable", None, None),
    Case("xkqwzplm foobar",            "not_answerable", None, None),
]


# ── Runner ────────────────────────────────────────────────────────────────────

def run_eval():
    pool = ThreadedConnectionPool(
        minconn=1, maxconn=3,
        host=os.environ["POSTGRES_HOST"],
        port=int(os.environ.get("POSTGRES_PORT", 5432)),
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
    )
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    graph = build_graph(client, pool)

    passed = 0
    failed = 0

    print(f"\n{'═' * 70}")
    print(f"  RAG EVAL  —  {len(CASES)} test cases")
    print(f"{'═' * 70}\n")

    for i, case in enumerate(CASES, 1):
        thread_id = f"eval-{i}"
        result = graph.invoke(
            {
                "question": case.question,
                "question_type": "data_query",
                "sql": None, "explanation": None, "llm_confidence": None,
                "results": None, "rows_returned": 0,
                "back_question": None, "final_confidence": None,
                "confidence_label": None, "warnings": [], "answer": None, "error": None,
            },
            config={"configurable": {"thread_id": thread_id}},
        )

        actual_type = result.get("question_type", "unknown")
        confidence  = result.get("final_confidence") or 0.0
        sql         = result.get("sql") or ""
        failures    = []

        # Check 1: routing
        if actual_type != case.expect_type:
            failures.append(f"type={actual_type!r} (expected {case.expect_type!r})")

        # Check 2: confidence floor for data queries
        if case.min_confidence is not None and confidence < case.min_confidence:
            failures.append(f"confidence={confidence:.2f} < {case.min_confidence}")

        # Check 3: SQL keyword present
        if case.sql_must_contain and case.sql_must_contain.lower() not in sql.lower():
            failures.append(f"SQL missing {case.sql_must_contain!r}")

        status = "PASS" if not failures else "FAIL"
        icon   = "✓" if not failures else "✗"
        print(f"  {icon} [{status}] {case.question[:60]}")
        if failures:
            for f in failures:
                print(f"         → {f}")
            failed += 1
        else:
            passed += 1

    print(f"\n{'─' * 70}")
    print(f"  Results: {passed} passed, {failed} failed  ({len(CASES)} total)")
    print(f"{'─' * 70}\n")

    pool.closeall()
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    run_eval()
