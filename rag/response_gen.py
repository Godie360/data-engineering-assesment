"""Converts SQL query results into a grounded natural language answer."""
import json

from openai import OpenAI

_SYSTEM_PROMPT = """You are a data analyst assistant. Answer the user's question using ONLY the data provided in the SQL query results.

Rules:
1. Cite exact numbers from the results — do not round unless asked.
2. Do not fabricate, extrapolate, or add information not in the results.
3. If the results are empty, say so clearly.
4. Write in clear, concise prose. Use bullet points for lists longer than 3 items.
5. Do not repeat the SQL in your answer."""


def _format_results(results: list[dict]) -> str:
    if not results:
        return "No rows returned."
    if len(results) == 1:
        return "\n".join(f"  {k}: {v}" for k, v in results[0].items())
    # Table-style for multiple rows (compact JSON is readable for LLM)
    return json.dumps(results, default=str, indent=2)


def generate_response(
    question: str,
    sql: str,
    results: list[dict],
    client: OpenAI,
) -> str:
    """Returns a grounded natural language answer. Raises on OpenAI error."""
    user_content = (
        f"Question: {question}\n\n"
        f"SQL used:\n{sql}\n\n"
        f"Query results ({len(results)} rows):\n{_format_results(results)}"
    )
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.3,
        max_tokens=800,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
    )
    return response.choices[0].message.content.strip()
