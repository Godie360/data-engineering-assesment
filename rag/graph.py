"""
LangGraph RAG pipeline.

Graph:
  START → classify
            ├─ data_query    → gen_sql → execute → validate → respond → END
            ├─ clarification → clarify → END
            └─ not_answerable → block  → END

MemorySaver checkpointer stores conversation history per thread_id,
so follow-up questions like "what do you mean by hour 0?" have full context.
"""
from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from openai import OpenAI

from rag.executor import execute_query
from rag.hallucination import validate as validate_hallucination
from rag.query_gen import NotAnswerableError, generate_sql
from rag.response_gen import generate_response
from rag.schema import get_schema_context
from rag.state import RAGState

_SCHEMA = get_schema_context()


def _history_text(messages: list, n: int = 3) -> str:
    """Format the last n exchanges as a readable context string."""
    lines = []
    for msg in messages[-(n * 2):]:
        role = "User" if isinstance(msg, HumanMessage) else "Sele"
        content = msg.content[:350] + "..." if len(msg.content) > 350 else msg.content
        lines.append(f"{role}: {content}")
    return "\n".join(lines)


def build_graph(client: OpenAI, pool):
    """
    Build and compile the LangGraph RAG graph.

    client — OpenAI client
    pool   — psycopg2 ThreadedConnectionPool (nodes acquire/release per request)
    """

    # ── Nodes ─────────────────────────────────────────────────────────────────

    def classify(state: RAGState) -> dict:
        """Route to data_query or clarification based on conversation context."""
        history = state.get("messages", [])
        if not history:
            return {"question_type": "data_query"}

        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0,
            max_tokens=10,
            messages=[{
                "role": "user",
                "content": (
                    f"Conversation so far:\n{_history_text(history)}\n\n"
                    f'New message: "{state["question"]}"\n\n'
                    "Is this:\n"
                    'A) A follow-up or clarification about the conversation above '
                    '(e.g. "what does that mean?", "explain hour 0", "why is that?", '
                    '"is that normal?", "what is TRANSFER?")\n'
                    'B) A new data question about the mobile money dataset\n\n'
                    'Reply with only one word: "clarification" or "data_query"'
                ),
            }],
        )
        label = resp.choices[0].message.content.strip().lower().strip('"')
        if label not in ("clarification", "data_query"):
            label = "data_query"
        return {"question_type": label}

    def gen_sql(state: RAGState) -> dict:
        """Generate SQL, optionally enriched with conversation context."""
        history = state.get("messages", [])
        schema = _SCHEMA
        if history:
            schema += f"\n\nCONVERSATION CONTEXT (recent exchanges):\n{_history_text(history)}"

        try:
            q = generate_sql(state["question"], schema, client)
            return {
                "sql": q.sql,
                "explanation": q.explanation,
                "llm_confidence": q.llm_confidence,
                "error": None,
            }
        except (NotAnswerableError, ValueError) as e:
            return {"question_type": "not_answerable", "error": str(e)}

    def execute(state: RAGState) -> dict:
        """Execute SQL against PostgreSQL using a pooled connection."""
        conn = pool.getconn()
        try:
            rows = execute_query(state["sql"], conn)
            return {"results": rows, "rows_returned": len(rows), "error": None}
        except Exception as e:
            return {"results": [], "rows_returned": 0, "error": str(e)}
        finally:
            pool.putconn(conn)

    def validate(state: RAGState) -> dict:
        """Back-translation hallucination check + confidence scoring."""
        v = validate_hallucination(
            state["question"], state["sql"],
            state["llm_confidence"], state["results"], client,
        )
        return {
            "back_question": v.back_question,
            "final_confidence": v.final_confidence,
            "confidence_label": v.label,
            "warnings": v.warnings,
        }

    def respond(state: RAGState) -> dict:
        """Generate a grounded natural-language answer from SQL results."""
        answer = generate_response(state["question"], state["sql"], state["results"], client)
        return {
            "answer": answer,
            "messages": [
                HumanMessage(content=state["question"]),
                AIMessage(content=answer),
            ],
        }

    def clarify(state: RAGState) -> dict:
        """Answer a follow-up or clarification question conversationally."""
        history = state.get("messages", [])
        ctx = _history_text(history, n=4) if history else "(no prior context)"

        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.4,
            max_tokens=300,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are Sele the Analyst, an AI data assistant for Selcom Paytech's mobile money data. "
                        "You are answering a follow-up or clarification about a previous response. "
                        "Be clear, friendly, and concise — explain data concepts in plain language. "
                        "Examples: 'hour 0' means midnight 00:00–00:59; "
                        "'TRANSFER' is a peer-to-peer money transfer transaction type; "
                        "'balance discrepancy' means the ledger doesn't add up correctly. "
                        "Keep your answer to 2–4 sentences."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Conversation:\n{ctx}\n\nFollow-up question: {state['question']}",
                },
            ],
        )
        answer = resp.choices[0].message.content.strip()
        return {
            "answer": answer,
            "question_type": "clarification",
            "final_confidence": 1.0,
            "confidence_label": "HIGH",
            "warnings": [],
            "messages": [
                HumanMessage(content=state["question"]),
                AIMessage(content=answer),
            ],
        }

    def block(state: RAGState) -> dict:
        """Return a polite rejection for out-of-scope questions."""
        reason = state.get("error") or "Please ask a question about the mobile money transaction data."
        answer = f"I can only answer questions about Selcom's mobile money dataset. {reason}"
        return {
            "answer": answer,
            "question_type": "not_answerable",
            "final_confidence": 0.0,
            "confidence_label": "LOW",
            "warnings": [],
            "messages": [
                HumanMessage(content=state["question"]),
                AIMessage(content=answer),
            ],
        }

    # ── Routing ───────────────────────────────────────────────────────────────

    def route_classify(state: RAGState) -> str:
        return state["question_type"]

    def route_sql(state: RAGState) -> str:
        if state.get("error") or state.get("question_type") == "not_answerable":
            return "not_answerable"
        return "execute"

    def route_execute(state: RAGState) -> str:
        return "not_answerable" if state.get("error") else "validate"

    # ── Graph assembly ────────────────────────────────────────────────────────

    g = StateGraph(RAGState)

    g.add_node("classify", classify)
    g.add_node("gen_sql", gen_sql)
    g.add_node("execute", execute)
    g.add_node("validate", validate)
    g.add_node("respond", respond)
    g.add_node("clarify", clarify)
    g.add_node("block", block)

    g.add_edge(START, "classify")

    g.add_conditional_edges("classify", route_classify, {
        "data_query":     "gen_sql",
        "clarification":  "clarify",
        "not_answerable": "block",
    })
    g.add_conditional_edges("gen_sql", route_sql, {
        "execute":        "execute",
        "not_answerable": "block",
    })
    g.add_conditional_edges("execute", route_execute, {
        "validate":       "validate",
        "not_answerable": "block",
    })

    g.add_edge("validate", "respond")
    g.add_edge("respond", END)
    g.add_edge("clarify", END)
    g.add_edge("block", END)

    return g.compile(checkpointer=MemorySaver())
