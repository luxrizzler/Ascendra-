import { useMemo, useState } from "react";
import { ArrowRight, CheckCircle2, Edit3, XCircle } from "lucide-react";
import { CardPlayButton } from "./CardPlayButton";

function _normalize(s) {
  return (s || "").toLowerCase().trim().replace(/[\.,!?;:"'`]/g, "").replace(/\s+/g, " ");
}

export function FillBlankCard({ card, idx, total, lessonTitle, onAdvance }) {
  const [val, setVal] = useState("");
  const [tries, setTries] = useState(0);
  const [status, setStatus] = useState("idle"); // idle | wrong | correct | revealed
  const accepted = useMemo(() => {
    const all = [card.answer, ...(card.aliases || [])];
    return new Set(all.map(_normalize));
  }, [card]);
  const submit = () => {
    if (!val.trim()) return;
    const ok = accepted.has(_normalize(val));
    if (ok) setStatus("correct");
    else { setStatus("wrong"); setTries((t) => t + 1); }
  };
  const reveal = () => { setStatus("revealed"); setVal(card.answer); };
  const parts = (card.prompt || "").split("___");
  return (
    <div className="asc-card p-8 sm:p-10 min-h-[340px]" data-testid="card-fill-blank">
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-2">
          <div className="w-9 h-9 rounded-full grid place-items-center" style={{ background: "rgba(56,189,248,0.15)" }}>
            <Edit3 size={16} color="#38BDF8" />
          </div>
          <div className="text-xs text-[var(--asc-text-muted)] tracking-wider">FILL THE BLANK · CARD {idx + 1} / {total}</div>
        </div>
        <CardPlayButton text={`${card.title}. ${card.prompt.replace('___', 'blank')}`} title={card.title} lessonTitle={lessonTitle} />
      </div>
      <h3 className="asc-h2 text-2xl sm:text-3xl">{card.title}</h3>
      <div className="text-[var(--asc-text-dim)] text-lg mt-4 leading-relaxed">
        <span>{parts[0]}</span>
        <span className="inline-block align-middle mx-1 px-3 py-1 rounded-md font-black" style={{ background: status === "correct" || status === "revealed" ? "rgba(52,211,153,0.15)" : "rgba(255,176,0,0.12)", color: status === "correct" || status === "revealed" ? "#34D399" : "#FFB000", border: `1px dashed ${status === "correct" || status === "revealed" ? "#34D399" : "#FFB000"}`, minWidth: 80, textAlign: "center" }}>
          {status === "correct" || status === "revealed" ? card.answer : "___"}
        </span>
        <span>{parts[1] || ""}</span>
      </div>
      {status !== "correct" && status !== "revealed" && (
        <div className="mt-5">
          <input
            type="text"
            value={val}
            onChange={(e) => { setVal(e.target.value); if (status !== "idle") setStatus("idle"); }}
            onKeyDown={(e) => { if (e.key === "Enter") submit(); }}
            placeholder="Type your answer here…"
            data-testid="blank-input"
            className="w-full p-4 rounded-xl border outline-none focus:border-[#FFB000]"
            style={{ background: "#1F183A", borderColor: status === "wrong" ? "#FB7185" : "rgba(191,180,255,0.12)", color: "#fff" }}
          />
          {status === "wrong" && (
            <div className="text-sm mt-2 flex items-center gap-2" style={{ color: "#FB7185" }}>
              <XCircle size={14} /> Not quite — try again. {tries >= 2 && (<button type="button" onClick={reveal} className="underline ml-2" data-testid="blank-reveal-btn">Reveal answer</button>)}
            </div>
          )}
        </div>
      )}
      {(status === "correct" || status === "revealed") && card.explanation && (
        <div className="mt-5 p-4 rounded-xl text-sm flex gap-3" style={{ background: "rgba(52,211,153,0.06)", border: "1px solid #34D399" }}>
          <CheckCircle2 size={20} color="#34D399" className="shrink-0 mt-0.5" />
          <div className="text-[var(--asc-text-dim)] leading-relaxed">{card.explanation}</div>
        </div>
      )}
      <div className="mt-6 flex justify-end">
        {status === "correct" || status === "revealed" ? (
          <button onClick={onAdvance} data-testid="blank-continue-btn" className="asc-btn-primary">Continue <ArrowRight size={14} /></button>
        ) : (
          <button onClick={submit} disabled={!val.trim()} data-testid="blank-submit-btn" className="asc-btn-primary disabled:opacity-50">Submit <ArrowRight size={14} /></button>
        )}
      </div>
    </div>
  );
}
