import React, { useEffect, useRef, useState } from "react";
import { FaRobot } from "react-icons/fa";
import { FiMessageCircle, FiSend, FiX, FiExternalLink } from "react-icons/fi";

const starterQuestions = [
  "What AI projects has Gulshan built?",
  "Tell me about his work experience",
  "What is he studying at BTH?",
  "Give me an overview of Gulshan",
];

const API_BASE = (process.env.REACT_APP_AI_API_URL ||
  (process.env.NODE_ENV === "development" ? "http://localhost:8000" : "")
).replace(/\/$/, "");

const welcome = {
  role: "assistant",
  content: "Hi! I'm Gulshan's portfolio AI assistant. Ask me about his software engineering experience, AI projects, education, and skills. I'll use his published portfolio and CV to answer.",
  sources: [],
};

const AIChatbot = () => {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState([welcome]);
  const [draft, setDraft] = useState("");
  const [loading, setLoading] = useState(false);
  const inputRef = useRef(null);
  const scrollRef = useRef(null);

  useEffect(() => {
    if (open) inputRef.current?.focus();
  }, [open]);

  useEffect(() => {
    if (open) scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [open, messages, loading]);

  const sendMessage = async (text) => {
    const question = text.trim();
    if (loading || !question) return;
    setDraft("");
    const previous = messages
      .filter((message) => message !== welcome && !message.error)
      .slice(-6)
      .map(({ role, content }) => ({ role, content: content.slice(0, 500) }));
    setMessages((current) => [...current, { role: "user", content: question }]);
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, history: previous }),
      });
      if (!response.ok) throw new Error(`API returned ${response.status}`);
      const data = await response.json();
      if (typeof data.answer !== "string") throw new Error("Invalid API response");
      setMessages((current) => [...current, {
        role: "assistant", content: data.answer,
        sources: Array.isArray(data.sources) ? data.sources : [],
        mode: data.mode,
      }]);
    } catch (error) {
      setMessages((current) => [...current, {
        role: "assistant",
        content: "I couldn't reach the AI backend. If you're testing locally, start it with: python -m uvicorn backend.main:app --reload --port 8000. If this is the public site, the backend still needs to be deployed and connected.",
        error: true,
      }]);
    } finally {
      setLoading(false);
    }
  };

  const onSubmit = (event) => {
    event.preventDefault();
    sendMessage(draft);
  };

  return (
    <div className="fixed bottom-5 right-4 z-[70] sm:bottom-6 sm:right-6">
      {open && (
        <section
          role="dialog"
          aria-label="Ask Gulshan AI assistant"
          className="mb-3 flex h-[min(73vh,560px)] w-[calc(100vw-2rem)] max-w-[420px] flex-col overflow-hidden rounded-2xl border border-cyan-700/70 bg-slate-950 text-gray-100 shadow-2xl shadow-cyan-950/70 sm:h-[560px]"
        >
          <header className="flex items-center justify-between border-b border-slate-700 bg-gradient-to-r from-slate-800 to-cyan-950 px-4 py-3">
            <div className="flex items-center gap-3">
              <span className="flex h-10 w-10 items-center justify-center rounded-full bg-cyan-800/70 text-cyan-100">
                <FaRobot size={20} aria-hidden="true" />
              </span>
              <div>
                <h2 className="text-base font-semibold">Ask Gulshan AI</h2>
                <p className="text-xs text-cyan-200">Answers from portfolio &amp; CV</p>
              </div>
            </div>
            <button
              type="button"
              aria-label="Close AI assistant"
              onClick={() => setOpen(false)}
              className="rounded-md p-2 text-gray-200 transition-colors hover:bg-slate-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-cyan-300"
            >
              <FiX size={20} aria-hidden="true" />
            </button>
          </header>

          <div className="flex-1 space-y-4 overflow-y-auto px-4 py-4" aria-live="polite" aria-relevant="additions text">
            {messages.map((message, index) => (
              <div key={index} className={message.role === "user" ? "flex justify-end" : "flex justify-start"}>
                <div className={
                  "max-w-[92%] rounded-xl px-3 py-2 text-sm leading-relaxed shadow-md " +
                  (message.role === "user"
                    ? "bg-cyan-800 text-white"
                    : "border border-slate-700 bg-slate-800 text-gray-100")
                }>
                  <p className="whitespace-pre-wrap break-words">{message.content}</p>
                  {message.sources?.length > 0 && (
                    <div className="mt-3 border-t border-slate-600 pt-2">
                      <p className="mb-1 text-xs font-semibold text-cyan-200">Sources</p>
                      <div className="flex flex-col gap-2">
                        {message.sources.slice(0, 5).map((source) => (
                          <a
                            key={source.id}
                            href={source.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex w-full items-start gap-2 break-words rounded px-1 py-1 text-xs leading-5 text-cyan-300 underline-offset-2 hover:bg-slate-700 hover:text-cyan-100 hover:underline"
                          >
                            <FiExternalLink className="mt-0.5 shrink-0" aria-hidden="true" />
                            <span>{source.title}</span>
                          </a>
                        ))}
                      </div>
                    </div>
                  )}
                  {message.mode === "retrieval_only" && !message.error && (
                    <p className="mt-2 text-[11px] text-slate-400">Retrieved portfolio excerpts. For conversational answers, start Ollama and check that the selected model is installed.</p>
                  )}
                </div>
              </div>
            ))}
            {loading && <p className="text-sm text-cyan-200" role="status">Searching portfolio information…</p>}
            <div ref={scrollRef} />
          </div>

          {messages.length === 1 && (
            <div className="flex flex-wrap gap-2 border-t border-slate-800 px-3 py-3">
              {starterQuestions.map((question) => (
                <button
                  key={question}
                  type="button"
                  onClick={() => sendMessage(question)}
                  className="rounded-full border border-cyan-700/80 px-3 py-1.5 text-left text-xs text-cyan-100 transition-colors hover:border-cyan-400 hover:bg-cyan-950"
                >
                  {question}
                </button>
              ))}
            </div>
          )}

          <form onSubmit={onSubmit} className="flex items-center gap-2 border-t border-slate-700 bg-slate-900 p-3">
            <label htmlFor="portfolio-ai-question" className="sr-only">Ask a question about Gulshan</label>
            <input
              id="portfolio-ai-question"
              ref={inputRef}
              type="text"
              value={draft}
              maxLength={500}
              onChange={(event) => setDraft(event.target.value)}
              placeholder="Ask about projects, skills…"
              disabled={loading}
              className="min-w-0 flex-1 rounded-lg border border-slate-600 bg-slate-800 px-3 py-2.5 text-sm text-white placeholder:text-slate-400 focus:border-cyan-400 focus:outline-none disabled:opacity-60"
            />
            <button
              type="submit"
              disabled={!draft.trim() || loading}
              aria-label="Send message"
              className="rounded-lg bg-cyan-700 p-3 text-white transition-colors hover:bg-cyan-600 focus-visible:outline focus-visible:outline-2 focus-visible:outline-cyan-300 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <FiSend aria-hidden="true" />
            </button>
          </form>
          <p className="bg-slate-900 pb-2 text-center text-[10px] text-slate-400">
            Portfolio information may be incomplete. Verify important details.
          </p>
        </section>
      )}

      <button
        type="button"
        aria-label={open ? "Close Ask Gulshan AI" : "Open Ask Gulshan AI"}
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
        className="ml-auto flex items-center gap-2 rounded-full border border-cyan-400/60 bg-gradient-to-r from-cyan-800 to-slate-800 px-4 py-3 font-semibold text-white shadow-lg shadow-cyan-900/60 transition-all duration-300 hover:-translate-y-1 hover:scale-105 hover:shadow-cyan-600/40 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-cyan-300"
      >
        {open ? <FiX size={20} aria-hidden="true" /> : <FiMessageCircle size={20} aria-hidden="true" />}
        <span>{open ? "Close" : "Ask Gulshan AI"}</span>
      </button>
    </div>
  );
};

export default AIChatbot;
