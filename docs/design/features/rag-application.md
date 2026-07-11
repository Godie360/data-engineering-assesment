# RAG Application Design

## Pattern: Text-to-SQL

User submits a natural language question → LLM generates SQL → SQL executes against PostgreSQL → LLM synthesises a grounded answer from real query results.

**Why not vector RAG**: data is structured with exact answers. Vector similarity retrieval is for unstructured text. Text-to-SQL is the correct retrieval pattern for tabular financial data.

## Component Responsibilities

### `rag/schema.py`
- Reads `sql/schema.sql` at startup
- Builds a concise schema context string: table name, column names, types, and plain-English descriptions
- Output: single string passed as system context to query_gen

### `rag/query_gen.py`
- Input: user question (str) + schema context (str)
- Calls OpenAI `gpt-4o-mini` with:
  - System prompt: enforce `SELECT` only, no DDL/DML, return raw SQL with no markdown
  - User prompt: question + schema context
- Output: SQL string
- Raises `ValueError` if response contains `INSERT`, `UPDATE`, `DELETE`, `DROP`, `TRUNCATE`

### `rag/executor.py`
- Input: SQL string
- Executes against PostgreSQL via `psycopg2`
- Caps result at 500 rows
- Output: list of dicts (column → value)
- Raises and logs on SQL error; does not retry

### `rag/response_gen.py`
- Input: original question (str) + SQL (str) + query results (list of dicts)
- Calls OpenAI `gpt-4o-mini` with:
  - System prompt: answer using only the provided data, cite numbers exactly, do not fabricate
  - User prompt: question + SQL used + results as formatted table
- Output: natural language answer string

### `app.py` (Streamlit)
- Text input: user question
- On submit: calls query_gen → executor → response_gen
- Displays: generated SQL (collapsed expander) + natural language answer
- Displays: error message if any step fails
- Session state: stores last 5 Q&A pairs in sidebar

## Example Queries the App Must Answer Correctly

| Question | Expected SQL pattern |
|---|---|
| Total value of fraudulent transfers | `SUM(amount) WHERE transaction_type='TRANSFER' AND is_fraud=TRUE` |
| Transaction type with highest average amount | `AVG(amount) GROUP BY transaction_type ORDER BY AVG DESC LIMIT 1` |
| Count of balance-error transactions | `COUNT(*) WHERE has_balance_error=TRUE` |
| Busiest hour by transaction volume | `COUNT(*) GROUP BY transaction_hour ORDER BY COUNT DESC LIMIT 1` |
| Fraud rate by transaction type | `fraud_rate FROM transaction_summary GROUP BY transaction_type` |
| Total deposits vs withdrawals | `SUM(amount) GROUP BY transaction_type WHERE transaction_type IN ('DEPOSIT','WITHDRAWAL')` |
| Days with highest fraud amounts | `SUM(fraud_total_amount) FROM transaction_summary GROUP BY transaction_day ORDER BY SUM DESC LIMIT 5` |

## OpenAI Model

- Model: `gpt-4o-mini`
- Temperature: 0 for query_gen (deterministic SQL), 0.3 for response_gen (natural language)
- Max tokens: 500 for SQL, 800 for response

## Security Constraints

- `query_gen` system prompt explicitly forbids non-SELECT statements
- Output SQL is validated in Python before execution: block if contains `INSERT|UPDATE|DELETE|DROP|TRUNCATE|ALTER|CREATE`
- No user input is interpolated into SQL strings; LLM generates complete SQL from schema context only
