"use client";

import { useState, useRef, useEffect, FormEvent } from "react";
import ReactMarkdown from "react-markdown";
import SelcomLogo from "@/components/SelcomLogo";

// ── Constants ─────────────────────────────────────────────────────────────────
const SELCOM_RED = "#E2001A";

// ── Types ─────────────────────────────────────────────────────────────────────
interface BotPayload {
  answer: string;
  question_type: "data_query" | "clarification" | "not_answerable";
  sql?: string;
  explanation?: string;
  rows_returned: number;
  confidence_label: "HIGH" | "MEDIUM" | "LOW";
  final_confidence: number;
  back_question?: string;
  warnings: string[];
  results_preview: Record<string, unknown>[];
}

type Role = "user" | "assistant" | "error";

interface Message {
  id: string;
  role: Role;
  text: string;
  payload?: BotPayload;
}

// ── Suggested questions ───────────────────────────────────────────────────────
const SUGGESTIONS = [
  "What is the total value of fraudulent transfers?",
  "Which transaction type has the highest average amount?",
  "What percentage of TRANSFER transactions are fraudulent?",
  "What is the busiest hour for transaction volume?",
  "Show fraud rate by transaction type",
  "Compare total deposits vs total withdrawals",
  "Which day had the highest number of fraudulent transactions?",
  "Show balance errors by transaction type",
];

// ── Confidence badge ──────────────────────────────────────────────────────────
function ConfidenceBadge({ label, score }: { label: string; score: number }) {
  const styles: Record<string, string> = {
    HIGH:   "bg-green-500/15 text-green-400 border-green-500/30",
    MEDIUM: "bg-amber-500/15 text-amber-400 border-amber-500/30",
    LOW:    "bg-red-500/15 text-[#E2001A] border-[#E2001A]/30",
  };
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold border ${styles[label] ?? styles.LOW}`}>
      <span className="w-1.5 h-1.5 rounded-full inline-block"
            style={{ background: label === "HIGH" ? "#4ade80" : label === "MEDIUM" ? "#fbbf24" : SELCOM_RED }} />
      {label} · {Math.round(score * 100)}%
    </span>
  );
}

// ── SQL expander ──────────────────────────────────────────────────────────────
function SqlExpander({ payload }: { payload: BotPayload }) {
  const [open, setOpen] = useState(false);
  const [tableOpen, setTableOpen] = useState(false);

  return (
    <div className="mt-3 space-y-2">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 text-xs text-zinc-500 hover:text-zinc-300 transition-colors w-full"
      >
        <span className="font-mono px-2 py-0.5 rounded border text-[10px]"
              style={{ borderColor: `${SELCOM_RED}40`, color: SELCOM_RED, background: `${SELCOM_RED}10` }}>
          SQL
        </span>
        <span>{payload.rows_returned} row{payload.rows_returned !== 1 ? "s" : ""} returned</span>
        <span className="ml-auto">{open ? "▲" : "▼"}</span>
      </button>

      {open && (
        <div className="rounded-xl border border-zinc-800 bg-black overflow-hidden text-xs">
          {/* Explanation */}
          <div className="px-4 py-3 border-b border-zinc-800 text-zinc-400 italic text-[11px]">
            {payload.explanation}
          </div>

          {/* SQL */}
          <pre className="px-4 py-3 overflow-x-auto font-mono leading-relaxed whitespace-pre-wrap text-[11px]"
               style={{ color: SELCOM_RED }}>
            {payload.sql}
          </pre>

          {/* Back-translation */}
          {payload.back_question && (
            <div className="px-4 py-3 border-t border-zinc-800 text-zinc-500 text-[11px]">
              <span className="text-zinc-400 font-semibold">Hallucination check: </span>
              {payload.back_question}
            </div>
          )}

          {/* Results table */}
          {payload.results_preview.length > 0 && (
            <div className="border-t border-zinc-800">
              <button
                onClick={() => setTableOpen(!tableOpen)}
                className="w-full px-4 py-2 text-left text-zinc-500 hover:text-zinc-300 transition-colors text-[11px]"
              >
                {tableOpen ? "Hide" : "Show"} data preview
                {payload.rows_returned > 10 && ` (showing 10 of ${payload.rows_returned})`}
              </button>
              {tableOpen && (
                <div className="overflow-x-auto px-4 pb-4">
                  <table className="w-full text-[11px] border-collapse">
                    <thead>
                      <tr>
                        {Object.keys(payload.results_preview[0]).map((col) => (
                          <th key={col}
                              className="text-left px-3 py-2 border-b border-zinc-800 whitespace-nowrap font-semibold text-zinc-400">
                            {col}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {payload.results_preview.map((row, i) => (
                        <tr key={i} className="border-b border-zinc-900 hover:bg-zinc-900/50">
                          {Object.values(row).map((val, j) => (
                            <td key={j} className="px-3 py-2 text-zinc-300 whitespace-nowrap">
                              {val === null
                                ? <span className="text-zinc-600 italic">null</span>
                                : String(val)}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Message bubble ────────────────────────────────────────────────────────────
function Avatar() {
  return (
    <div className="flex-shrink-0 w-9 h-9 rounded-full flex items-center justify-center text-white text-sm font-bold mt-0.5"
         style={{ background: SELCOM_RED }}>
      S
    </div>
  );
}

function MessageBubble({ msg }: { msg: Message }) {
  if (msg.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[75%] text-white rounded-2xl rounded-tr-sm px-4 py-3 text-sm"
             style={{ background: "#1e1e1e", border: "1px solid #2a2a2a" }}>
          {msg.text}
        </div>
      </div>
    );
  }

  if (msg.role === "error") {
    return (
      <div className="flex justify-start gap-3">
        <Avatar />
        <div className="max-w-[85%] rounded-2xl rounded-tl-sm px-4 py-3 text-sm border"
             style={{ background: `${SELCOM_RED}15`, borderColor: `${SELCOM_RED}40`, color: "#fca5a5" }}>
          {msg.text}
        </div>
      </div>
    );
  }

  const isDataQuery = msg.payload?.question_type === "data_query";

  return (
    <div className="flex justify-start gap-3">
      <Avatar />
      <div className="max-w-[85%] space-y-2">
        {/* Confidence badge + warnings — only for data queries */}
        {msg.payload && isDataQuery && (
          <div className="flex flex-wrap items-center gap-2">
            <ConfidenceBadge label={msg.payload.confidence_label} score={msg.payload.final_confidence} />
            {msg.payload.warnings.map((w, i) => (
              <span key={i} className="text-[11px] text-amber-400 bg-amber-500/10 border border-amber-500/20 rounded-full px-2.5 py-0.5">
                ⚠ {w}
              </span>
            ))}
          </div>
        )}

        {/* Answer bubble */}
        <div className="rounded-2xl rounded-tl-sm px-4 py-3 text-sm text-zinc-100"
             style={{ background: "#141414", border: "1px solid #222" }}>
          <div className="prose max-w-none text-sm leading-relaxed text-zinc-100">
            <ReactMarkdown>{msg.text}</ReactMarkdown>
          </div>
        </div>

        {/* SQL expander — only for data queries with SQL */}
        {msg.payload && isDataQuery && msg.payload.sql && (
          <SqlExpander payload={msg.payload} />
        )}
      </div>
    </div>
  );
}

// ── Typing indicator ──────────────────────────────────────────────────────────
function TypingIndicator() {
  return (
    <div className="flex justify-start gap-3">
      <Avatar />
      <div className="rounded-2xl rounded-tl-sm px-4 py-3" style={{ background: "#141414", border: "1px solid #222" }}>
        <div className="flex gap-1 items-center h-5">
          {[0, 1, 2].map((i) => (
            <span key={i} className="w-2 h-2 rounded-full animate-bounce inline-block"
                  style={{ background: SELCOM_RED, animationDelay: `${i * 0.15}s` }} />
          ))}
        </div>
      </div>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  // Stable thread ID for the lifetime of this browser session
  const threadId = useRef(crypto.randomUUID());

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function send(text: string) {
    if (!text.trim() || loading) return;

    setMessages((prev) => [...prev, { id: crypto.randomUUID(), role: "user", text: text.trim() }]);
    setInput("");
    setLoading(true);

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text.trim(), thread_id: threadId.current }),
      });
      const data = await res.json();

      if (!res.ok) {
        setMessages((prev) => [
          ...prev,
          { id: crypto.randomUUID(), role: "error", text: data.error ?? "Something went wrong. Please try again." },
        ]);
      } else {
        setMessages((prev) => [
          ...prev,
          { id: crypto.randomUUID(), role: "assistant", text: data.answer, payload: data as BotPayload },
        ]);
      }
    } catch {
      setMessages((prev) => [
        ...prev,
        { id: crypto.randomUUID(), role: "error", text: "Network error — is the API server running on port 8000?" },
      ]);
    } finally {
      setLoading(false);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }

  return (
    <div className="flex flex-col h-screen text-zinc-100" style={{ background: "#0A0A0A" }}>

      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <header className="flex-shrink-0 px-6 py-3" style={{ borderBottom: "1px solid #1a1a1a" }}>
        <div className="max-w-3xl mx-auto flex items-center gap-4">
          <SelcomLogo className="h-8 w-auto" color={SELCOM_RED} />
          <div className="w-px h-7 bg-zinc-800" />
          <div>
            <h1 className="font-bold text-white text-sm tracking-tight">Sele the Analyst</h1>
            <p className="text-[11px] text-zinc-500">Data Intelligence · 4.2M transactions</p>
          </div>
        </div>
      </header>

      {/* ── Messages ───────────────────────────────────────────────────────── */}
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-3xl mx-auto px-4 py-8 space-y-6">

          {/* Empty state */}
          {messages.length === 0 && (
            <div className="text-center space-y-8 py-8">
              <div>
                <SelcomLogo className="h-16 w-auto mx-auto" color={SELCOM_RED} />
                <h2 className="text-xl font-bold text-white mt-5">Hi, I&apos;m Sele the Analyst</h2>
                <p className="text-zinc-500 text-sm mt-2 max-w-md mx-auto">
                  Ask me anything about Selcom&apos;s mobile money transaction data.
                  I translate your question into SQL, query{" "}
                  <span className="text-white font-medium">4.2M records</span>, and give you a grounded answer with a confidence score.
                </p>
              </div>

              {/* Suggestion chips */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-left max-w-2xl mx-auto">
                {SUGGESTIONS.map((s) => (
                  <button
                    key={s}
                    onClick={() => send(s)}
                    className="px-4 py-3 rounded-xl text-sm text-zinc-400 text-left transition-all"
                    style={{ background: "#141414", border: "1px solid #222" }}
                    onMouseEnter={(e) => {
                      (e.currentTarget as HTMLButtonElement).style.borderColor = `${SELCOM_RED}60`;
                      (e.currentTarget as HTMLButtonElement).style.color = "#fff";
                    }}
                    onMouseLeave={(e) => {
                      (e.currentTarget as HTMLButtonElement).style.borderColor = "#222";
                      (e.currentTarget as HTMLButtonElement).style.color = "#a1a1aa";
                    }}
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((msg) => <MessageBubble key={msg.id} msg={msg} />)}
          {loading && <TypingIndicator />}
          <div ref={bottomRef} />
        </div>
      </main>

      {/* ── Input bar ──────────────────────────────────────────────────────── */}
      <footer className="flex-shrink-0 px-4 py-4" style={{ borderTop: "1px solid #1a1a1a" }}>
        <form
          onSubmit={(e: FormEvent) => { e.preventDefault(); send(input); }}
          className="max-w-3xl mx-auto flex gap-2"
        >
          <input
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask Sele about the transaction data…"
            disabled={loading}
            autoFocus
            className="flex-1 rounded-xl px-4 py-3 text-sm text-zinc-100 placeholder-zinc-600 focus:outline-none disabled:opacity-50 transition-colors"
            style={{ background: "#141414", border: "1px solid #2a2a2a" }}
            onFocus={(e) => (e.currentTarget.style.borderColor = `${SELCOM_RED}80`)}
            onBlur={(e) => (e.currentTarget.style.borderColor = "#2a2a2a")}
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="flex-shrink-0 rounded-xl px-4 py-3 text-sm font-semibold text-white transition-all disabled:opacity-40 disabled:cursor-not-allowed"
            style={{ background: loading || !input.trim() ? "#2a2a2a" : SELCOM_RED }}
          >
            {loading ? (
              <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
              </svg>
            ) : (
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
              </svg>
            )}
          </button>
        </form>
        <p className="text-center text-[11px] text-zinc-700 mt-2">
          Answers grounded in real database results · Hallucination detection enabled
        </p>
      </footer>
    </div>
  );
}
