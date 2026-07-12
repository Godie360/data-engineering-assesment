"""Typed state for the LangGraph RAG pipeline."""
from __future__ import annotations

from typing import Annotated, Optional

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class RAGState(TypedDict):
    # Conversation memory — add_messages reducer appends each turn
    messages: Annotated[list[BaseMessage], add_messages]

    # Per-turn inputs (reset each invocation)
    question: str
    question_type: str          # "data_query" | "clarification" | "not_answerable"

    # SQL generation
    sql: Optional[str]
    explanation: Optional[str]
    llm_confidence: Optional[float]

    # Execution
    results: Optional[list[dict]]
    rows_returned: int

    # Validation
    back_question: Optional[str]
    final_confidence: Optional[float]
    confidence_label: Optional[str]
    warnings: list[str]

    # Output
    answer: Optional[str]
    error: Optional[str]
