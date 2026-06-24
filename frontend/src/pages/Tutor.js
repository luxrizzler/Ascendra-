import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import Loader from "@/components/Loader";
import { Send, Sparkles, MessageSquare, RotateCcw } from "lucide-react";
import { toast } from "sonner";

const SUGGESTIONS = [
  "What's the best AI model for writing in 2026?",
  "Help me write a system prompt for a marketing copywriter.",
  "How do I get started with AI agents and MCP?",
  "Build me a study plan for AI fundamentals in 7 days.",
];

const SESSION_KEY = "ascendra_tutor_session_id";

export default function Tutor() {
  const [messages, setMessages] = useState([]);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [sessionId, setSessionId] = useState(() => {
    try { return localStorage.getItem(SESSION_KEY) || ""; } catch { return ""; }
  });
  const [loading, setLoading] = useState(true);
  const listRef = useRef(null);

  useEffect(() => {
    if (!sessionId) { setLoading(false); return; }
    api.get(`/tutor/history/${sessionId}`)
      .then((r) => setMessages(r.messages))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [sessionId]);

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, busy]);

  const send = async (text) => {
    const msg = (text ?? draft).trim();
    if (!msg || busy) return;
    setDraft("");
    setMessages((m) => [...m, { role: "user", content: msg }]);
    setBusy(true);
    try {
      const r = await api.post("/tutor/chat", { message: msg, session_id: sessionId || undefined });
      setMessages((m) => [...m, { role: "assistant", content: r.reply }]);
      if (!sessionId) {
        setSessionId(r.session_id);
        try { localStorage.setItem(SESSION_KEY, r.session_id); } catch {}
      }
    } catch (e) {
      toast.error(e.message || "AI Tutor unavailable");
      setMessages((m) => m.slice(0, -1));
    } finally {
      setBusy(false);
    }
  };

  const reset = () => {
    try { localStorage.removeItem(SESSION_KEY); } catch {}
    setSessionId("");
    setMessages([]);
    toast.success("Started a new conversation");
  };

  if (loading) return <Loader />;

  return (
    <div className="max-w-4xl mx-auto px-5 sm:px-8 py-8 flex flex-col" style={{ minHeight: "calc(100vh - 80px)" }} data-testid="tutor-page">
      <div className="flex items-center justify-between mb-5">
        <div>
          <div className="asc-kicker">AI Tutor</div>
          <h1 className="asc-h2 text-3xl mt-1 flex items-center gap-2"><Sparkles size={26} className="text-[var(--asc-brand)]" /> Ask Ascendra</h1>
          <p className="text-[var(--asc-text-dim)] text-sm mt-1">Powered by Claude Sonnet 4.5 · Multi-turn memory</p>
        </div>
        <button onClick={reset} className="asc-btn-secondary text-sm" data-testid="tutor-new-btn"><RotateCcw size={14} /> New chat</button>
      </div>

      <div ref={listRef} className="flex-1 asc-card p-5 overflow-y-auto no-scrollbar mb-4" style={{ minHeight: 360 }} data-testid="tutor-messages">
        {messages.length === 0 && (
          <div className="h-full grid place-items-center text-center">
            <div>
              <div className="w-16 h-16 rounded-full grid place-items-center mx-auto mb-4" style={{ background: "rgba(124,58,237,0.18)" }}>
                <MessageSquare size={26} color="#BFB4FF" />
              </div>
              <h3 className="asc-h2 text-xl">Your private AI coach.</h3>
              <p className="text-[var(--asc-text-dim)] text-sm mt-2 max-w-md">Ask anything about AI — from picking the right model to writing a killer system prompt.</p>
              <div className="grid sm:grid-cols-2 gap-2 mt-6">
                {SUGGESTIONS.map((s) => (
                  <button key={s} onClick={() => send(s)} className="text-left text-sm p-3 rounded-xl border hover:border-[var(--asc-brand)] transition" style={{ background: "#1F183A", borderColor: "rgba(191,180,255,0.12)" }} data-testid="tutor-suggestion-btn">
                    {s}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}
        {messages.map((m, i) => (
          <Message key={i} role={m.role} content={m.content} />
        ))}
        {busy && <Message role="assistant" content={"…"} typing />}
      </div>

      <form onSubmit={(e) => { e.preventDefault(); send(); }} className="flex gap-2">
        <input
          className="asc-input flex-1"
          placeholder="Ask the AI Tutor anything…"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          disabled={busy}
          data-testid="tutor-input"
        />
        <button type="submit" disabled={busy || !draft.trim()} className="asc-btn-primary px-5" data-testid="tutor-send-btn"><Send size={16} /></button>
      </form>
    </div>
  );
}

function Message({ role, content, typing }) {
  const isUser = role === "user";
  return (
    <div className={`flex gap-3 mb-5 ${isUser ? "flex-row-reverse" : ""}`} data-testid={`tutor-msg-${role}`}>
      <div className="w-8 h-8 rounded-full grid place-items-center shrink-0" style={{ background: isUser ? "#7C3AED" : "#FFB000" }}>
        {isUser ? <span className="text-xs font-black">YOU</span> : <Sparkles size={14} color="#000" />}
      </div>
      <div className={`max-w-[80%] p-4 rounded-2xl whitespace-pre-wrap leading-relaxed text-[15px] ${isUser ? "text-white" : ""}`} style={{ background: isUser ? "#1F183A" : "#15102B", border: "1px solid rgba(191,180,255,0.12)" }}>
        {typing ? <span className="inline-flex gap-1"><span className="pulse-dot">●</span><span className="pulse-dot" style={{ animationDelay: "0.2s" }}>●</span><span className="pulse-dot" style={{ animationDelay: "0.4s" }}>●</span></span> : content}
      </div>
    </div>
  );
}
