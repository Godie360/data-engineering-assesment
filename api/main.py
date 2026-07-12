"""
FastAPI backend — exposes the LangGraph RAG pipeline over HTTP.
POST /api/chat   — accepts message + thread_id for per-session conversation memory
GET  /health     — liveness probe
"""
import os
from contextlib import asynccontextmanager
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from psycopg2.pool import ThreadedConnectionPool
from pydantic import BaseModel

load_dotenv()

from rag.graph import build_graph

_resources: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    pool = ThreadedConnectionPool(
        minconn=1,
        maxconn=10,
        host=os.environ["POSTGRES_HOST"],
        port=int(os.environ.get("POSTGRES_PORT", 5432)),
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
    )
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    _resources["graph"] = build_graph(client, pool)
    _resources["pool"] = pool
    yield
    pool.closeall()


app = FastAPI(title="Selcom RAG API", lifespan=lifespan)

_CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)


# ── Request / Response models ─────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    thread_id: str = "default"  # per-session ID for conversation memory


class ChatResponse(BaseModel):
    answer: str
    question_type: str                  # "data_query" | "clarification" | "not_answerable"
    sql: Optional[str] = None
    explanation: Optional[str] = None
    rows_returned: int = 0
    confidence_label: str = "HIGH"      # HIGH / MEDIUM / LOW
    final_confidence: float = 1.0       # 0.0 – 1.0
    back_question: Optional[str] = None
    warnings: list[str] = []
    results_preview: list[dict] = []    # first 10 rows for the UI table


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    config = {"configurable": {"thread_id": req.thread_id}}

    result = _resources["graph"].invoke(
        {
            "question": req.message.strip(),
            "question_type": "data_query",
            "sql": None,
            "explanation": None,
            "llm_confidence": None,
            "results": None,
            "rows_returned": 0,
            "back_question": None,
            "final_confidence": None,
            "confidence_label": None,
            "warnings": [],
            "answer": None,
            "error": None,
        },
        config=config,
    )

    return ChatResponse(
        answer=result.get("answer") or "",
        question_type=result.get("question_type", "data_query"),
        sql=result.get("sql"),
        explanation=result.get("explanation"),
        rows_returned=result.get("rows_returned") or 0,
        confidence_label=result.get("confidence_label") or "HIGH",
        final_confidence=result.get("final_confidence") or 1.0,
        back_question=result.get("back_question"),
        warnings=result.get("warnings") or [],
        results_preview=(result.get("results") or [])[:10],
    )
