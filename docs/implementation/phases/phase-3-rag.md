# Phase 3 — RAG Application

## Status

pending

## Scope

- `rag/schema.py`
- `rag/query_gen.py`
- `rag/executor.py`
- `rag/response_gen.py`
- `app.py`

## Features

- Schema context builder: generates table/column description string for LLM prompts
- SQL generator: OpenAI `gpt-4o-mini` converts natural language question to SELECT query (temperature=0)
- Query executor: runs SQL against PostgreSQL, caps results at 500 rows
- Response generator: OpenAI synthesises grounded natural language answer from SQL results (temperature=0.3)
- Streamlit UI: text input, answer display, generated SQL expander, last 5 Q&A in sidebar
- Security: non-SELECT SQL blocked before execution

## Tasks

- [ ] TASK-10: Schema context builder (`rag/schema.py`)
- [ ] TASK-11: SQL generator (`rag/query_gen.py`)
- [ ] TASK-12: Query executor (`rag/executor.py`)
- [ ] TASK-13: Response generator (`rag/response_gen.py`)
- [ ] TASK-14: Streamlit UI (`app.py`)

## Acceptance Criteria

- `streamlit run app.py` launches on port 8501 with no errors
- "What is the total value of fraudulent TRANSFER transactions?" returns correct numeric answer
- "Which transaction type has the highest average amount?" returns correct type name
- Generated SQL displayed in collapsed expander in UI
- Non-SELECT SQL from LLM is blocked before execution (raises ValueError)
- DB connection error shows error message in UI without crashing
