"""Converts a natural language question into a validated SQL SELECT statement."""
import json
import re
from dataclasses import dataclass

from openai import OpenAI

_FORBIDDEN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|TRUNCATE|ALTER|CREATE)\b", re.IGNORECASE
)

NOT_ANSWERABLE_PREFIX = "NOT_ANSWERABLE:"


class NotAnswerableError(Exception):
    """Raised when the question cannot be answered from the database schema."""
    pass


@dataclass
class GeneratedQuery:
    sql: str
    explanation: str   # one sentence: what this SQL does
    llm_confidence: float  # LLM's self-assessed confidence 0.0–1.0


_SYSTEM_PROMPT = """You are a PostgreSQL expert analysing mobile money transaction data.

Given a user question and schema context, return JSON with exactly these fields:
{
  "sql": "<valid SELECT statement — no semicolon, no markdown>",
  "explanation": "<one sentence: what does this SQL compute?>",
  "confidence": <float 0.0–1.0: how confident are you this SQL correctly answers the question?>
}

Only return not_answerable if the question is completely unrelated to mobile money data (e.g. weather,
sports, greetings) or is pure gibberish with no recognisable words.
Vague but data-related questions like "overview", "summary", "tell me about the data", or "what types
exist" ARE answerable — generate a meaningful aggregate SQL for them.

If truly not answerable, return:
{
  "not_answerable": true,
  "reason": "<one sentence explanation>"
}

Rules for SQL:
- Use exact column and table names from the schema.
- Never write INSERT, UPDATE, DELETE, DROP, TRUNCATE, ALTER, or CREATE.
- Do not include a semicolon at the end.
- Follow the few-shot examples closely for style."""


def generate_sql(question: str, schema_context: str, client: OpenAI) -> GeneratedQuery:
    """
    Returns a GeneratedQuery with sql, explanation, and llm_confidence.
    Raises NotAnswerableError if the question is unrelated or gibberish.
    Raises ValueError if the output contains unsafe SQL keywords.
    """
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0,
        max_tokens=600,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Schema:\n{schema_context}\n\nQuestion: {question}",
            },
        ],
    )

    try:
        data = json.loads(response.choices[0].message.content)
    except json.JSONDecodeError as exc:
        raise ValueError(f"LLM returned non-JSON output: {exc}") from exc

    if data.get("not_answerable"):
        raise NotAnswerableError(data.get("reason", "Question is not answerable from this dataset."))

    sql = data.get("sql", "").strip().rstrip(";")

    # Strip any accidental markdown fences
    sql = re.sub(r"^```(?:sql)?\s*", "", sql, flags=re.IGNORECASE)
    sql = re.sub(r"\s*```$", "", sql).strip()

    if _FORBIDDEN.search(sql):
        raise ValueError(f"Unsafe SQL generated: {sql[:120]}")

    # Clamp to valid range — model output is untrusted at this boundary
    raw_confidence = float(data.get("confidence", 0.5))
    llm_confidence = max(0.0, min(1.0, raw_confidence))

    return GeneratedQuery(
        sql=sql,
        explanation=data.get("explanation", ""),
        llm_confidence=llm_confidence,
    )
