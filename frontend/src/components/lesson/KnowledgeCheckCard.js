import { useState } from "react";
import { ArrowRight, CheckCircle2, Sparkles, XCircle } from "lucide-react";
import { CardPlayButton } from "./CardPlayButton";
import { celebrateCorrect, celebrateWrong } from "@/lib/celebrations";

export function KnowledgeCheckCard({ card, idx, total, lessonTitle, onAdvance, autoplay }) {
  const [pick, setPick] = useState(null);
  const [revealed, setRevealed] = useState(false);
  const isCorrect = pick === card.answer_index;
  const submit = () => {
    if (pick === null) return;
    setRevealed(true);
    if (pick === card.answer_index) celebrateCorrect(); else celebrateWrong();
  };
  return (
    <div className="asc-card p-8 sm:p-10 min-h-[340px]" data-testid="card-knowledge-check">
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-2">
          <div className="w-9 h-9 rounded-full grid place-items-center" style={{ background: "rgba(124,58,237,0.18)" }}>
            <Sparkles size={16} color="#BFB4FF" />
          </div>
          <div className="text-xs text-[var(--asc-text-muted)] tracking-wider">CHECK · CARD {idx + 1} / {total}</div>
        </div>
        <CardPlayButton text={`${card.title}. ${card.question}`} title={card.title} lessonTitle={lessonTitle} />
      </div>
      <h3 className="asc-h2 text-2xl sm:text-3xl">{card.question}</h3>
      <div className="space-y-3 mt-5">
        {card.options.map((o, i) => {
          const chosen = pick === i;
          const correctOption = revealed && i === card.answer_index;
          const wrongChosen = revealed && chosen && i !== card.answer_index;
          let bg = "#1F183A";
          let border = "rgba(191,180,255,0.12)";
          if (correctOption) { bg = "rgba(52,211,153,0.10)"; border = "#34D399"; }
          else if (wrongChosen) { bg = "rgba(251,113,133,0.10)"; border = "#FB7185"; }
          else if (chosen) { bg = "rgba(255,176,0,0.06)"; border = "#FFB000"; }
          return (
            <button
              key={i}
              type="button"
              onClick={() => !revealed && setPick(i)}
              disabled={revealed}
              data-testid={`check-option-${i}`}
              className="w-full text-left p-4 rounded-xl border transition-all disabled:cursor-default"
              style={{ background: bg, borderColor: border }}
            >
              <div className="flex items-center gap-3">
                <div className="w-7 h-7 rounded-full grid place-items-center font-black text-sm" style={{ background: correctOption ? "#34D399" : chosen ? "#FFB000" : "#15102B", color: (correctOption || chosen) ? "#000" : "#fff" }}>
                  {String.fromCharCode(65 + i)}
                </div>
                <span className="font-bold text-base flex-1">{o}</span>
                {correctOption && <CheckCircle2 size={18} color="#34D399" />}
                {wrongChosen && <XCircle size={18} color="#FB7185" />}
              </div>
            </button>
          );
        })}
      </div>
      {revealed && (
        <div className="mt-5 p-4 rounded-xl text-sm" style={{ background: isCorrect ? "rgba(52,211,153,0.06)" : "rgba(255,176,0,0.06)", border: `1px solid ${isCorrect ? "#34D399" : "#FFB000"}` }}>
          <div className="font-bold mb-1" style={{ color: isCorrect ? "#34D399" : "#FFB000" }}>
            {isCorrect ? "Nice — you got it." : "Not quite — but worth knowing."}
          </div>
          {card.explanation && <div className="text-[var(--asc-text-dim)] leading-relaxed">{card.explanation}</div>}
        </div>
      )}
      <div className="mt-6 flex justify-end">
        {!revealed ? (
          <button onClick={submit} disabled={pick === null} data-testid="check-submit-btn" className="asc-btn-primary disabled:opacity-50">
            Check answer <ArrowRight size={14} />
          </button>
        ) : (
          <button onClick={onAdvance} data-testid="check-continue-btn" className="asc-btn-primary">
            Continue <ArrowRight size={14} />
          </button>
        )}
      </div>
    </div>
  );
}
