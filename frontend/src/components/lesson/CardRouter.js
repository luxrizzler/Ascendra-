import { TextCard } from "./TextCard";
import { KnowledgeCheckCard } from "./KnowledgeCheckCard";
import { FillBlankCard } from "./FillBlankCard";
import { PlaygroundCard } from "./PlaygroundCard";
import { PracticeCard } from "./PracticeCard";

export function CardRouter({ card, idx, total, lessonTitle, lessonId, pathId, onAdvance, autoplay }) {
  const kind = card?.kind || "text";
  switch (kind) {
    case "knowledge_check":
      return <KnowledgeCheckCard card={card} idx={idx} total={total} lessonTitle={lessonTitle} onAdvance={onAdvance} autoplay={autoplay} />;
    case "fill_blank":
      return <FillBlankCard card={card} idx={idx} total={total} lessonTitle={lessonTitle} onAdvance={onAdvance} />;
    case "playground":
      return <PlaygroundCard card={card} idx={idx} total={total} lessonTitle={lessonTitle} lessonId={lessonId} onAdvance={onAdvance} />;
    case "try_it_live":
      return <PracticeCard card={card} idx={idx} total={total} lessonTitle={lessonTitle} lessonId={lessonId} pathId={pathId} onAdvance={onAdvance} />;
    case "text":
    default:
      return <TextCard card={card} idx={idx} total={total} lessonTitle={lessonTitle} onAdvance={onAdvance} autoplay={autoplay} />;
  }
}

export function isInteractive(card) {
  const k = card?.kind || "text";
  return k === "knowledge_check" || k === "fill_blank" || k === "playground" || k === "try_it_live";
}
