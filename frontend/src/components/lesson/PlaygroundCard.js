import { useState } from "react";
import { ArrowRight, Send, Sparkles, RotateCw } from "lucide-react";
import { api } from "@/lib/api";
import { CardPlayButton } from "./CardPlayButton";
import { toast } from "sonner";

export function PlaygroundCard({ card, idx, total, lessonTitle, lessonId, onAdvance }) {
  const [prompt, setPrompt] = useState(card.seed_prompt || "");
  const [reply, setReply] = useState("");
  const [loading, setLoading] = useState(false);
  const run = async () => {
    if (!prompt.trim()) return;
    setLoading(true); setReply("");
    try {
      const r = await api.post("/playground/run", {
        prompt,
        instruction: card.system || undefined,
        lesson_id: lessonId,
      });
      setReply(r.response || "");
    } catch (e) {
      toast.error(e.message || "AI is busy — try again in a moment.");
    } finally { setLoading(false); }
  };
  const reset = () => { setReply(""); setPrompt(card.seed_prompt || ""); };
  return (
    <div className="asc-card p-8 sm:p-10 min-h-[340px]" data-testid="card-playground">
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-2">
          <div className="w-9 h-9 rounded-full grid place-items-center" style={{ background: "rgba(255,176,0,0.18)" }}>
            <Sparkles size={16} color="#FFB000" />
          </div>
          <div className="text-xs text-[var(--asc-text-muted)] tracking-wider">TRY IT YOURSELF · CARD {idx + 1} / {total}</div>
        </div>
        <CardPlayButton text={`${card.title}. ${card.instruction}`} title={card.title} lessonTitle={lessonTitle} />
      </div>
      <h3 className="asc-h2 text-2xl sm:text-3xl">{card.title}</h3>
      <p className="text-[var(--asc-text-dim)] mt-3 leading-relaxed">{card.instruction}</p>

      <div className="mt-5">
        <label className="block text-xs text-[var(--asc-text-muted)] tracking-wider mb-2">YOUR PROMPT</label>
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          rows={4}
          placeholder="Type your prompt here…"
          data-testid="playground-input"
          className="w-full p-4 rounded-xl border outline-none resize-y focus:border-[#FFB000]"
          style={{ background: "#1F183A", borderColor: "rgba(191,180,255,0.12)", color: "#fff" }}
        />
        <div className="flex items-center justify-between mt-3">
          <div className="text-xs text-[var(--asc-text-muted)]">Powered by Claude · stateless · 220-word cap</div>
          <button onClick={run} disabled={loading || !prompt.trim()} data-testid="playground-run-btn" className="asc-btn-primary disabled:opacity-50">
            {loading ? "Thinking…" : (<>Run <Send size={14} /></>)}
          </button>
        </div>
      </div>

      {reply && (
        <div className="mt-6 p-5 rounded-xl text-sm leading-relaxed whitespace-pre-wrap" style={{ background: "rgba(255,176,0,0.04)", border: "1px solid rgba(255,176,0,0.25)" }} data-testid="playground-output">
          <div className="flex items-center justify-between mb-2">
            <div className="text-xs font-bold" style={{ color: "#FFB000" }}>AI RESPONSE</div>
            <CardPlayButton text={reply} title={`${card.title} — AI reply`} lessonTitle={lessonTitle} size="sm" />
          </div>
          <div className="text-[var(--asc-text-dim)]">{reply}</div>
        </div>
      )}

      <div className="mt-6 flex items-center justify-between">
        <button type="button" onClick={reset} className="text-xs text-[var(--asc-text-muted)] hover:text-white flex items-center gap-1" data-testid="playground-reset-btn">
          <RotateCw size={12} /> Reset
        </button>
        <button onClick={onAdvance} data-testid="playground-continue-btn" className="asc-btn-primary">Continue <ArrowRight size={14} /></button>
      </div>
    </div>
  );
}
