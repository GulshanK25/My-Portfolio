import React, { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import { FiArrowUp, FiChevronDown, FiExternalLink, FiMessageCircle, FiPlus, FiSquare, FiX } from "react-icons/fi";

// Conversation history stays in this browser tab. Nothing is persisted on our server.
const STORAGE_KEY = "gulshan-ai-v2-session";
const API_BASE = (process.env.REACT_APP_AI_API_URL ||
  (process.env.NODE_ENV === "development" ? "http://localhost:8000" : "")
).replace(/\/$/, "");

const suggestions = [
  "What are you working on right now?",
  "Tell me about your AI projects",
  "What are you studying at BTH?",
  "What did you work on at Dun & Bradstreet?",
];

const greeting = {
  id: "welcome",
  role: "assistant",
  content: "Hey! 👋 I'm **Gulshan AI**, an AI version of Gulshan's professional portfolio. I'm here to chat about what he's built, what he's learning, and what he's working on. What's on your mind?",
  sources: [],
};

const getSavedMessages = () => {
  try {
    const saved = JSON.parse(window.sessionStorage.getItem(STORAGE_KEY) || "null");
    if (!Array.isArray(saved)) return [greeting];
    const valid = saved.filter((item) =>
      item && ["user", "assistant"].includes(item.role) && typeof item.content === "string" && item.content
    ).slice(-24);
    return valid.length ? [greeting, ...valid.filter((item) => item.id !== "welcome")] : [greeting];
  } catch {
    return [greeting];
  }
};

const AIChatbot = () => {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState(getSavedMessages);
  const [draft, setDraft] = useState("");
  const [loading, setLoading] = useState(false);
  const inputRef = useRef(null);
  const scrollRef = useRef(null);
  const abortRef = useRef(null);
  const requestIdRef = useRef(0);
  const loadingRef = useRef(false);

  useEffect(() => {
    try {
      window.sessionStorage.setItem(
        STORAGE_KEY,
        JSON.stringify(messages.filter((message) =>
          message.id !== "welcome" && message.content && !message.pending && !message.error
        ).slice(-24))
      );
    } catch {
      // Browsers with storage disabled can still use the assistant normally.
    }
  }, [messages]);

  useEffect(() => {
    if (open) inputRef.current?.focus();
  }, [open]);

  useEffect(() => {
    if (open) scrollRef.current?.scrollIntoView({ behavior: loading ? "auto" : "smooth" });
  }, [open, messages, loading]);

  useEffect(() => () => abortRef.current?.abort(), []);

  const stopResponse = () => {
    requestIdRef.current += 1;
    abortRef.current?.abort();
    abortRef.current = null;
    loadingRef.current = false;
    setLoading(false);
    setMessages((current) => current.map((message) => ({ ...message, pending: false })));
  };

  const startNewChat = () => {
    stopResponse();
    setMessages([greeting]);
    setDraft("");
    try { window.sessionStorage.removeItem(STORAGE_KEY); } catch { /* optional storage */ }
    inputRef.current?.focus();
  };

  const updateReply = (id, patch) => {
    setMessages((current) => current.map((message) =>
      message.id === id ? { ...message, ...patch } : message
    ));
  };

  const appendReply = (id, text) => {
    setMessages((current) => current.map((message) =>
      message.id === id ? { ...message, content: message.content + text } : message
    ));
  };

  const sendMessage = async (input) => {
    const question = input.trim();
    if (!question || loadingRef.current) return;
    loadingRef.current = true;
    setLoading(true);
    setDraft("");
    const requestId = ++requestIdRef.current;
    const id = `reply-${requestId}-${Date.now()}`;
    const history = messages.filter((message) =>
      message.id !== "welcome" && !message.error && !message.pending && message.content
    ).slice(-12).map(({ role, content }) => ({ role, content: content.slice(0, 1200) }));

    setMessages((current) => [...current,
      { id: `user-${id}`, role: "user", content: question },
      { id, role: "assistant", content: "", sources: [], pending: true },
    ]);

    const controller = new AbortController();
    abortRef.current = controller;
    let completed = false;
    try {
      const response = await fetch(`${API_BASE}/api/chat/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
        body: JSON.stringify({ question, history }),
        signal: controller.signal,
      });
      if (!response.ok) throw new Error(`Backend returned HTTP ${response.status}`);
      if (!response.body) throw new Error("Streaming not supported by this browser");

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      const processEvent = (eventText) => {
        if (requestIdRef.current !== requestId) return;
        const lines = eventText.split("\n");
        const name = lines.find((line) => line.startsWith("event:"))?.slice(6).trim();
        const data = lines.filter((line) => line.startsWith("data:")).map((line) => line.slice(5)).join("\n");
        if (!name || !data) return;
        let event;
        try { event = JSON.parse(data); } catch { return; }
        if (name === "meta") {
          updateReply(id, { sources: Array.isArray(event.sources) ? event.sources : [], mode: event.mode });
        } else if (name === "delta" && typeof event.text === "string") {
          appendReply(id, event.text);
        } else if (name === "done") {
          completed = true;
        }
      };
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, "\n");
        let splitAt;
        while ((splitAt = buffer.indexOf("\n\n")) >= 0) {
          processEvent(buffer.slice(0, splitAt));
          buffer = buffer.slice(splitAt + 2);
        }
      }
      if (buffer.trim()) processEvent(buffer);
      if (!completed) throw new Error("Stream ended unexpectedly");
    } catch (error) {
      if (controller.signal.aborted || requestIdRef.current !== requestId) return;
      updateReply(id, {
        content: "Sorry, I'm having trouble connecting right now. Please try asking me again in a moment.",
        sources: [],
        error: true,
      });
    } finally {
      if (requestIdRef.current === requestId) {
        updateReply(id, { pending: false });
        loadingRef.current = false;
        setLoading(false);
        abortRef.current = null;
      }
    }
  };

  const handleSubmit = (event) => {
    event.preventDefault();
    sendMessage(draft);
  };

  return (
    <div className="fixed bottom-4 right-3 z-[70] sm:bottom-6 sm:right-6">
      {open && (
        <section
          role="dialog"
          aria-label="Conversation with Gulshan AI"
          className="mb-3 flex h-[min(82vh,670px)] w-[calc(100vw-1.5rem)] max-w-[455px] flex-col overflow-hidden rounded-3xl border border-cyan-600/40 bg-[#0b1426] text-slate-100 shadow-2xl shadow-slate-950/80"
        >
          <header className="flex items-center gap-3 border-b border-slate-700/80 bg-gradient-to-r from-[#12263f] via-[#102337] to-[#07364b] px-4 py-3.5">
            <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-cyan-400 to-blue-600 font-bold tracking-tight text-white shadow-lg shadow-cyan-950/70" aria-hidden="true">GA</span>
            <div className="min-w-0 flex-1">
              <h2 className="text-base font-semibold leading-5">Gulshan AI</h2>
              <p className="mt-0.5 text-xs text-cyan-100/80">Gulshan's AI portfolio representative</p>
            </div>
            <button type="button" onClick={startNewChat} title="Start a new chat" aria-label="Start a new chat"
              className="rounded-lg p-2 text-slate-300 transition hover:bg-white/10 hover:text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-cyan-300">
              <FiPlus size={19} aria-hidden="true" />
            </button>
            <button type="button" onClick={() => setOpen(false)} title="Close chat" aria-label="Close Gulshan AI"
              className="rounded-lg p-2 text-slate-300 transition hover:bg-white/10 hover:text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-cyan-300">
              <FiX size={19} aria-hidden="true" />
            </button>
          </header>

          <div className="flex-1 space-y-5 overflow-y-auto px-3.5 py-5 sm:px-4" aria-live="polite" aria-relevant="additions text">
            {messages.map((message) => {
              const mine = message.role === "user";
              const content = message.content.replace(/\[\s*SOURCE\s*\d+\s*\]|【\s*SOURCE\s*\d+\s*】/gi, "").trim();
              return (
                <div key={message.id} className={`flex items-start gap-2 ${mine ? "justify-end" : "justify-start"}`}>
                  {!mine && <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-cyan-900/70 text-[10px] font-bold text-cyan-200" aria-hidden="true">GA</span>}
                  <div className={`min-w-0 max-w-[90%] ${mine ? "rounded-2xl rounded-br-md bg-cyan-700 px-3.5 py-2.5 text-white" : "text-slate-100"}`}>
                    {mine ? <p className="whitespace-pre-wrap break-words text-sm leading-6">{content}</p> : (
                      <div className="break-words text-sm leading-6 text-slate-100 [&_a]:text-cyan-300 [&_a]:underline [&_li]:my-1 [&_ol]:my-2 [&_ol]:list-decimal [&_ol]:pl-5 [&_p]:my-2 [&_p:first-child]:mt-0 [&_p:last-child]:mb-0 [&_strong]:font-semibold [&_ul]:my-2 [&_ul]:list-disc [&_ul]:pl-5">
                        {content ? <ReactMarkdown components={{
                          a: ({ node, ...props }) => <a {...props} target="_blank" rel="noopener noreferrer" />,
                        }}>{content}</ReactMarkdown> : (
                          <div className="flex items-center gap-1 py-2" role="status" aria-label="Gulshan AI is responding">
                            {[0, 1, 2].map((dot) => <span key={dot} className="h-1.5 w-1.5 animate-pulse rounded-full bg-cyan-300" style={{ animationDelay: `${dot * 180}ms` }} />)}
                          </div>
                        )}
                      </div>
                    )}
                    {!mine && !message.pending && message.sources?.length > 0 && (
                      <details className="group mt-2 rounded-lg border border-slate-700/70 bg-slate-900/60 px-2.5 py-1.5 text-xs">
                        <summary className="flex cursor-pointer list-none items-center gap-1.5 text-slate-300 hover:text-cyan-200 [&::-webkit-details-marker]:hidden">
                          <FiExternalLink aria-hidden="true" />
                          View {message.sources.length} source{message.sources.length > 1 ? "s" : ""}
                          <FiChevronDown className="ml-auto transition-transform group-open:rotate-180" aria-hidden="true" />
                        </summary>
                        <div className="mt-2 space-y-1.5 border-t border-slate-700 pt-2">
                          {message.sources.map((source, index) => (
                            <a key={`${source.id}-${index}`} href={source.url} target="_blank" rel="noopener noreferrer"
                              className="block break-words rounded-md px-1 py-1 text-cyan-200 underline-offset-2 hover:bg-slate-800 hover:underline">
                              {source.title}
                            </a>
                          ))}
                        </div>
                      </details>
                    )}
                  </div>
                </div>
              );
            })}
            <div ref={scrollRef} />
          </div>

          {messages.length === 1 && (
            <div className="flex flex-wrap gap-2 border-t border-slate-800/80 px-3.5 py-3">
              {suggestions.map((suggestion) => (
                <button key={suggestion} type="button" onClick={() => sendMessage(suggestion)}
                  className="rounded-full border border-cyan-700/60 bg-cyan-950/30 px-3 py-1.5 text-left text-xs leading-5 text-cyan-100 transition hover:border-cyan-400 hover:bg-cyan-900/40">
                  {suggestion}
                </button>
              ))}
            </div>
          )}

          <form onSubmit={handleSubmit} className="border-t border-slate-700/80 bg-[#0c192b] p-3">
            <div className="flex items-center gap-2 rounded-2xl border border-slate-600/90 bg-slate-800/80 p-1.5 focus-within:border-cyan-400">
              <label htmlFor="gulshan-ai-message" className="sr-only">Your message</label>
              <input
                ref={inputRef} id="gulshan-ai-message" type="text" value={draft} maxLength={500}
                onChange={(event) => setDraft(event.target.value)}
                placeholder="Message Gulshan AI..." autoComplete="off"
                className="min-w-0 flex-1 bg-transparent px-2 py-2 text-sm text-white outline-none placeholder:text-slate-400"
              />
              {loading ? (
                <button type="button" onClick={stopResponse} title="Stop generating" aria-label="Stop generating"
                  className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-slate-500 text-white hover:bg-slate-400">
                  <FiSquare size={14} fill="currentColor" aria-hidden="true" />
                </button>
              ) : (
                <button type="submit" disabled={!draft.trim()} title="Send message" aria-label="Send message"
                  className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-cyan-600 text-white transition hover:bg-cyan-500 disabled:cursor-not-allowed disabled:bg-slate-600 disabled:text-slate-400">
                  <FiArrowUp size={19} aria-hidden="true" />
                </button>
              )}
            </div>
          </form>
          <p className="bg-[#0c192b] px-3 pb-2 text-center text-[10px] leading-4 text-slate-400">
            AI representative, not Gulshan personally. Answers are based on approved public information.
          </p>
        </section>
      )}

      <button type="button" aria-label={open ? "Close Gulshan AI" : "Chat with Gulshan AI"} aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
        className="ml-auto flex items-center gap-2 rounded-full border border-cyan-400/60 bg-gradient-to-r from-cyan-700 via-sky-800 to-slate-800 px-4 py-3 text-sm font-semibold text-white shadow-lg shadow-cyan-950/60 transition hover:-translate-y-0.5 hover:shadow-cyan-600/30 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-cyan-300">
        {open ? <FiX size={19} aria-hidden="true" /> : <FiMessageCircle size={19} aria-hidden="true" />}
        <span>{open ? "Close chat" : "Chat with Gulshan AI"}</span>
      </button>
    </div>
  );
};

export default AIChatbot;
