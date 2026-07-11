"""
Back-translation hallucination detection and confidence scoring.

How it works:
  1. Send the generated SQL back to the LLM: "What question does this SQL answer?"
  2. Compare that back-translated question to the original using LLM-as-judge.
  3. Return an alignment score (0–1) and combine with the LLM's self-confidence.

This catches cases where the SQL is syntactically valid but answers the wrong question.
"""
import json
from dataclasses import dataclass, field

from openai import OpenAI

from engine.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ValidationResult:
    back_question: str       # what the LLM thinks the SQL answers
    alignment_score: float   # 0–1: how well SQL matches the original question
    final_confidence: float  # (llm_confidence + alignment_score) / 2
    label: str               # HIGH / MEDIUM / LOW
    warnings: list[str] = field(default_factory=list)


def _label(score: float) -> str:
    if score >= 0.80:
        return "HIGH"
    if score >= 0.55:
        return "MEDIUM"
    return "LOW"


def validate(
    original_question: str,
    sql: str,
    llm_confidence: float,
    results: list[dict],
    client: OpenAI,
) -> ValidationResult:
    """
    Runs back-translation + alignment check in a single API call.
    Also performs basic result sanity checks (no LLM needed).
    """
    warnings: list[str] = []

    # ── Back-translation + alignment (1 API call) ─────────────────────────────
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0,
            max_tokens=200,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Given a SQL query and the original question it was generated for, "
                        "output JSON with:\n"
                        "1. \"back_question\": one sentence describing what this SQL actually computes\n"
                        "2. \"alignment\": float 0.0–1.0 — does the SQL correctly answer the original question?\n"
                        "   1.0 = perfect match, 0.0 = completely wrong\n"
                        "JSON only."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Original question: {original_question}\n\n"
                        f"Generated SQL:\n{sql}"
                    ),
                },
            ],
        )
        data = json.loads(response.choices[0].message.content)
        back_question = data.get("back_question", "")
        alignment_score = float(data.get("alignment", 0.5))
    except Exception as exc:
        logger.warning("Back-translation check failed: %s", exc)
        back_question = ""
        alignment_score = 0.5  # neutral fallback

    if alignment_score < 0.55:
        warnings.append(
            f"The SQL may not fully answer your question "
            f"(alignment score: {alignment_score:.0%}). "
            f"It appears to answer: \"{back_question}\""
        )

    # ── Result sanity checks (no LLM needed) ─────────────────────────────────
    if not results:
        warnings.append("Query returned no rows — the filter conditions may be too strict.")

    if results and len(results) == 500:
        warnings.append("Results are capped at 500 rows — the actual result set may be larger.")

    # ── Final confidence ──────────────────────────────────────────────────────
    final_confidence = round((llm_confidence + alignment_score) / 2, 3)

    return ValidationResult(
        back_question=back_question,
        alignment_score=alignment_score,
        final_confidence=final_confidence,
        label=_label(final_confidence),
        warnings=warnings,
    )
