import { Lightbulb } from "lucide-react";
import { CardPlayButton } from "./CardPlayButton";

export function TextCard({ card, idx, total, lessonTitle, onAdvance, autoplay }) {
  return (
    <div className="asc-card lesson-card p-8 sm:p-10 min-h-[340px] flex flex-col" data-testid="card-text">
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-2">
          <div className="w-9 h-9 rounded-full grid place-items-center" style={{ background: "rgba(255,176,0,0.15)" }}>
            <Lightbulb size={16} color="#FFB000" />
          </div>
          <div className="text-xs text-[var(--asc-text-muted)] tracking-wider">CARD {idx + 1} / {total}</div>
        </div>
        <CardPlayButton
          text={`${card.title}. ${card.body}`}
          title={card.title}
          lessonTitle={lessonTitle}
          onEnd={autoplay ? onAdvance : undefined}
        />
      </div>
      <h3 className="asc-h2 text-2xl sm:text-3xl">{card.title}</h3>
      <p className="text-[var(--asc-text-dim)] text-lg mt-4 leading-relaxed flex-1">{card.body}</p>
      <div className="text-xs text-[var(--asc-text-muted)] mt-6 text-center">Swipe, tap ▶ to listen, or use the arrows</div>
    </div>
  );
}
