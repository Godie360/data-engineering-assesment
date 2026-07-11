"""
FastAPI backend — exposes the RAG pipeline over HTTP.
The Next.js frontend calls POST /api/chat with the user's message.
"""
import os
from contextlib import asynccontextmanager

import psycopg2
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from pydantic import BaseModel

load_dotenv()

from rag.schema import get_schema_context
from rag.query_gen import generate_sql, NotAnswerableError
from rag.executor import execute_query
from rag.hallucination import validate as validate_hallucination
from rag.response_gen import generate_response

# ── Shared state (initialised once at startup) ────────────────────────────────
_resources: dict = {}


def _get_conn():
    """Return a live psycopg2 connection, reconnecting if needed."""
    conn = _resources.get("conn")
    if conn is None or conn.closed:
        conn = psycopg2.connect(
            host=os.environ["POSTGRES_HOST"],
            port=int(os.environ.get("POSTGRES_PORT", 5432)),
            dbname=os.environ["POSTGRES_DB"],
            user=os.environ["POSTGRES_USER"],
            password=os.environ["POSTGRES_PASSWORD"],
        )
        _resources["conn"] = conn
    return conn


@asynccontextmanager
async def lifespan(app: FastAPI):
    _resources["client"] = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    _resources["schema_ctx"] = get_schema_context()
    _get_conn()  # warm up connection
    yield
    conn = _resources.get("conn")
    if conn and not conn.closed:
        conn.close()


app = FastAPI(title="Selcom RAG API", lifespan=lifespan)

_CORS_ORIGINS = os.environ.get(
    "CORS_ORIGINS", "http://localhost:3000"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)


# ── Request / Response models ─────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    answer: str
    sql: str
    explanation: str
    rows_returned: int
    confidence_label: str       # HIGH / MEDIUM / LOW
    final_confidence: float     # 0.0 – 1.0
    back_question: str
    warnings: list[str]
    results_preview: list[dict] # first 10 rows for the UI table


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    question = req.message.strip()
    client: OpenAI = _resources["client"]
    schema_ctx: str = _resources["schema_ctx"]
    conn = _get_conn()

    # 1. Generate SQL
    try:
        query = generate_sql(question, schema_ctx, client)
    except NotAnswerableError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # 2. Execute
    try:
        results = execute_query(query.sql, conn)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"SQL execution failed: {exc}")

    # 3. Hallucination check + response generation (parallel-ish but sync is fine here)
    try:
        validation = validate_hallucination(
            question, query.sql, query.llm_confidence, results, client
        )
        answer = generate_response(question, query.sql, results, client)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Response generation failed: {exc}")

    return ChatResponse(
        answer=answer,
        sql=query.sql,
        explanation=query.explanation,
        rows_returned=len(results),
        confidence_label=validation.label,
        final_confidence=validation.final_confidence,
        back_question=validation.back_question,
        warnings=validation.warnings,
        results_preview=results[:10],
    )
