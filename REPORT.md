# Brief Technical Report
**Candidate:** Godfrey Enosh  
**Assessment:** Selcom Paytech — Data Engineer Pre-Interview Task  
**Deadline:** 17 July 2026

---

## 1. Approach

### Dataset
I selected the **Synthetic Mobile Money Transaction Dataset** (MoMTSim) from Kaggle — 4,225,958 rows of simulated East African mobile money transactions covering five transaction types (PAYMENT, TRANSFER, DEPOSIT, WITHDRAWAL, DEBIT) across nine simulation days. This dataset closely mirrors real M-Pesa-style transaction data in both structure and scale, exceeding the 50,000-row minimum by 84×.

### Data Pipeline
The pipeline is built in Python with pandas and PostgreSQL and follows a strict ETL pattern:

**Load → Clean → Transform → Store**

- **Chunked loading:** The CSV is read in 100,000-row chunks using `pandas.read_csv(chunksize=100_000)`. This keeps memory usage under 200 MB regardless of file size — the same code handles 4 million or 100 million rows without modification.
- **Cleaning:** Each chunk is normalised (uppercase transaction types, stripped whitespace), invalid rows are dropped (null required fields, amount ≤ 0, unrecognised transaction types), and missing balance columns are filled with 0.
- **Transformation:** Seven derived columns are added per row — `transaction_hour`, `transaction_day`, `amount_bucket`, `balance_discrepancy`, `has_balance_error`, `is_merchant_recipient`, and `net_recipient_gain`. These enable fraud and balance analysis without repeated computation at query time.
- **Bulk insert:** Each cleaned chunk is loaded into PostgreSQL using `COPY FROM STDIN` (via `psycopg2.copy_expert`), which achieves approximately 80,000 rows per second — roughly 80× faster than row-by-row `INSERT`.
- **Pre-aggregation:** After the full load, a `transaction_summary` table (45 rows: 9 days × 5 types) is computed via `INSERT … SELECT … ON CONFLICT DO UPDATE`. Queries like "fraud rate by type over time" scan 45 rows instead of 4.2 million.

### RAG Application — Sele the Analyst
Rather than vector similarity retrieval (designed for unstructured text), I implemented a **Text-to-SQL RAG** — the correct pattern for structured relational data.

The pipeline per question:
1. **Classify** — LangGraph routes the question: data query, conversational follow-up, or out-of-scope.
2. **Generate SQL** — GPT-4o-mini converts the natural-language question to a PostgreSQL SELECT statement using JSON-mode output (temperature=0) and a schema context with few-shot examples.
3. **Execute** — The SQL is validated with `sqlparse` (must be SELECT), wrapped in `BEGIN READ ONLY … ROLLBACK` (prevents writes), and executed against the live database.
4. **Hallucination detection** — Back-translation: the generated SQL is sent back to the LLM ("what question does this SQL answer?"). The alignment between that and the original question is scored 0–1. Final confidence = (LLM self-confidence + alignment score) / 2.
5. **Generate answer** — GPT-4o-mini produces a grounded natural-language response using only the actual query results (temperature=0.3).

**LangGraph** is used as the orchestration framework. It maintains per-session conversation memory via `MemorySaver`, enabling follow-up questions like "what do you mean by hour 0?" to receive contextual clarifications rather than SQL queries.

---

## 2. Challenges and How I Solved Them

| Challenge | Solution |
|---|---|
| **Out-of-memory on 4.2M rows** | Switched from full-file load to `chunksize=100_000`; memory stays flat at ~150 MB throughout the load |
| **Slow INSERT performance** | Replaced row-by-row `executemany` with PostgreSQL `COPY FROM STDIN` via StringIO buffer — load time dropped from ~70 minutes to ~2 minutes |
| **Fraud total returning NULL** | `SUM(amount) FILTER (WHERE is_fraud)` returns NULL when no fraud rows exist for a type. Fixed with `COALESCE(…, 0)` |
| **LLM querying wrong table** | The LLM used `transaction_summary.transaction_hour` (column does not exist). Fixed by adding explicit TABLE SELECTION RULES and a specific few-shot example to the schema context |
| **Gibberish questions returning results** | Added three-layer input guard: UI pre-validation, LLM `NOT_ANSWERABLE` signal, Python regex blocking unsafe SQL keywords |
| **Follow-up questions blocked** | Added LangGraph classification node: detects follow-up vs data query before routing; adds a `clarify` node that responds conversationally using conversation history |
| **Docker port conflict** | Local PostgreSQL occupied port 5432; mapped Docker PostgreSQL to host port 5433 |
| **curl not in Python slim image** | Replaced `curl`-based Docker healthcheck with `python -c "urllib.request.urlopen(...)"` |

---

## 3. Assumptions

- **Simulation time steps = hours:** The dataset `step` column represents elapsed simulation hours. `step % 24` gives the hour of day and `(step // 24) + 1` gives the simulation day (1–9). This is consistent with the PaySim/MoMTSim documentation.
- **Currency is local units:** No currency conversion is applied. All amounts are treated as a single local currency unit (consistent with M-Pesa-style simulation data).
- **Fraud label is ground truth:** The `isFraud` column is treated as the authoritative fraud label. No additional fraud detection model was built — the task asked for analysis, not prediction.
- **Dataset is static for the assessment:** The pipeline is designed to be idempotent (`TRUNCATE … RESTART IDENTITY` before load), so it can be re-run cleanly, but real-time ingestion was not in scope.
- **OpenAI API access is available:** The RAG application requires an OpenAI API key. The assessment environment was assumed to have internet access to the OpenAI API.
- **Single-user demo context:** `MemorySaver` stores conversation state in-memory. For a production multi-user system this would be replaced with a persistent store (Redis or PostgreSQL-backed checkpointer).

---

*Full source code, Docker setup, and running instructions are in the repository README.*
