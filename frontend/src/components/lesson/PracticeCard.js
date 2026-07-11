import { useEffect, useMemo, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  ArrowRight,
  Send,
  Sparkles,
  RotateCw,
  CheckCircle2,
  Zap,
  Trophy,
  Lightbulb,
  Target,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { CardPlayButton } from "./CardPlayButton";
import { celebrateLessonComplete } from "@/lib/celebrations";

/**
 * PracticeCard — "Try It Live" applied-practice card.
 *
 * Rubric-graded practice powered by Claude. When a user's score >= 80 they
 * hit "Mastery" and the attempt auto-saves to their private portfolio.
 *
 * Card shape (embedded in a lesson's cards[] array):
 *   {
 *     kind: "try_it_live",
 *     title: "Design an encouraging fitness coach",
 *     instruction: "Write a system prompt that ...",
 *     task_type: "prompt",             // or "artifact"
 *     success_criteria: ["...", "..."],
 *     rubric: [{criterion, description}, ...],
 *     seed_prompt: "You are ..."         // optional starter
 *   }
 */
export function PracticeCard({ card, idx, total, lessonTitle, lessonId, pathId, onAdvance }) {
  const [attempt, setAttempt] = useState(card.seed_prompt || "");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [attemptCount, setAttemptCount] = useState(0);
  const [showMasterExample, setShowMasterExample] = useState(false);
  const [showRubric, setShowRubric] = useState(false);

  // Reset when the card changes (navigating between cards)
  useEffect(() => {
    setAttempt(card.seed_prompt || "");
    setResult(null);
    setAttemptCount(0);
    setShowMasterExample(false);
  }, [card?.title, card?.seed_prompt]);

  const submit = async () => {
    if (!attempt.trim()) {
      toast.error("Write your attempt first.");
      return;
    }
    setLoading(true);
    setResult(null);
    setShowMasterExample(false);
    try {
      const r = await api.post("/practice/attempt", {
        attempt,
        title: card.title,
        instruction: card.instruction,
        task_type: card.task_type || "prompt",
        rubric: card.rubric || [],
        lesson_id: lessonId,
        path_id: pathId,
      });
      setResult(r);
      setAttemptCount((n) => n + 1);
      if (r.mastered && r.mastered_first_time) {
        celebrateLessonComplete();
        toast.success("🏆 Mastered! Saved to your portfolio.", { duration: 5000 });
      } else if (r.mastered) {
        toast.success(`Mastery again — score ${r.score}. Portfolio updated.`);
      } else {
        toast.message(`Score: ${r.score}/100 — try again!`);
      }
    } catch (e) {
      toast.error(e.message || "The AI is busy — try again in a moment.");
    } finally {
      setLoading(false);
    }
  };

  const reset = () => {
    setAttempt(card.seed_prompt || "");
    setResult(null);
    setShowMasterExample(false);
  };

  const canAdvance = !!(result && result.mastered) || attemptCount >= 3;
  const scoreColor = useMemo(() => {
    if (!result) return "#BFB4FF";
    if (result.score >= 80) return "#22c55e";
    if (result.score >= 60) return "#FFB000";
    return "#ef4444";
  }, [result]);

  return (
    <div className="asc-card p-8 sm:p-10 min-h-[420px]" data-testid="card-try-it-live">
      {/* Header */}
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-2">
          <div
            className="w-9 h-9 rounded-full grid place-items-center"
            style={{ background: "rgba(255,176,0,0.18)" }}
          >
            <Target size={16} color="#FFB000" />
          </div>
          <div className="text-xs text-[var(--asc-text-muted)] tracking-wider">
            TRY IT LIVE · PRACTICE · CARD {idx + 1} / {total}
          </div>
        </div>
        <CardPlayButton
          text={`${card.title}. ${card.instruction}`}
          title={card.title}
          lessonTitle={lessonTitle}
        />
      </div>

      <h3 className="asc-h2 text-2xl sm:text-3xl" data-testid="practice-title">
        {card.title}
      </h3>
      <p className="text-[var(--asc-text-dim)] mt-3 leading-relaxed" data-testid="practice-instruction">
        {card.instruction}
      </p>

      {/* Success criteria (visible before submit) */}
      {card.success_criteria && card.success_criteria.length > 0 && (
        <div
          className="mt-5 p-4 rounded-xl border"
          style={{ background: "rgba(191,180,255,0.05)", borderColor: "rgba(191,180,255,0.18)" }}
          data-testid="practice-criteria"
        >
          <div className="asc-label mb-2">Success criteria</div>
          <ul className="space-y-1.5 text-sm text-[var(--asc-text-dim)]">
            {card.success_criteria.map((c, i) => (
              <li key={i} className="flex items-start gap-2">
                <span className="mt-1 w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: "#BFB4FF" }} />
                <span>{c}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Rubric collapsible */}
      {card.rubric && card.rubric.length > 0 && (
        <button
          type="button"
          onClick={() => setShowRubric((v) => !v)}
          className="mt-4 flex items-center gap-1.5 text-xs text-[var(--asc-text-muted)] hover:text-white transition"
          data-testid="practice-rubric-toggle"
        >
          {showRubric ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
          {showRubric ? "Hide" : "Show"} how you&apos;ll be graded
        </button>
      )}
      <AnimatePresence>
        {showRubric && card.rubric && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="mt-3 overflow-hidden"
          >
            <div className="p-3 rounded-lg text-xs text-[var(--asc-text-dim)] space-y-1.5" style={{ background: "rgba(191,180,255,0.04)" }}>
              {card.rubric.map((r, i) => (
                <div key={i}>
                  <b className="text-white">{r.criterion}</b> — {r.description}
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Attempt input */}
      <div className="mt-6">
        <label className="block text-xs text-[var(--asc-text-muted)] tracking-wider mb-2">
          YOUR ATTEMPT
          {attemptCount > 0 && !result?.mastered && (
            <span className="ml-2 text-[var(--asc-brand)]">· attempt {attemptCount + 1}</span>
          )}
        </label>
        <textarea
          value={attempt}
          onChange={(e) => setAttempt(e.target.value)}
          rows={5}
          placeholder={
            card.task_type === "artifact"
              ? "Write your answer here..."
              : "Write your prompt here…"
          }
          data-testid="practice-input"
          className="w-full p-4 rounded-xl border outline-none resize-y focus:border-[#FFB000] transition"
          style={{ background: "#1F183A", borderColor: "rgba(191,180,255,0.12)", color: "#fff" }}
        />
        <div className="flex items-center justify-between mt-3 gap-3 flex-wrap">
          <div className="text-xs text-[var(--asc-text-muted)]">
            {attempt.length}/4000 · AI grades against a rubric · Mastery = 80+
          </div>
          <div className="flex items-center gap-2">
            {result && (
              <button
                onClick={reset}
                className="text-xs text-[var(--asc-text-muted)] hover:text-white flex items-center gap-1 px-3 py-1.5 rounded-full border border-[var(--asc-border)]"
                data-testid="practice-reset-btn"
              >
                <RotateCw size={12} /> Start over
              </button>
            )}
            <button
              onClick={submit}
              disabled={loading || !attempt.trim()}
              data-testid="practice-submit-btn"
              className="asc-btn-primary disabled:opacity-50"
            >
              {loading ? (
                <>Grading… <Sparkles size={14} className="animate-pulse" /></>
              ) : result ? (
                <>Retry <Send size={14} /></>
              ) : (
                <>Submit for grading <Send size={14} /></>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Feedback / grading result */}
      <AnimatePresence>
        {result && (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            className="mt-6 space-y-4"
            data-testid="practice-feedback"
          >
            {/* Score banner */}
            <div
              className="p-5 rounded-2xl border-2 flex items-center gap-4"
              style={{
                background: result.mastered
                  ? "linear-gradient(135deg, rgba(34,197,94,0.10), rgba(255,176,0,0.06))"
                  : "rgba(255,176,0,0.04)",
                borderColor: result.mastered ? "rgba(34,197,94,0.4)" : "rgba(255,176,0,0.3)",
              }}
            >
              <div
                className="w-20 h-20 rounded-full grid place-items-center flex-shrink-0"
                style={{
                  background: `conic-gradient(${scoreColor} ${result.score * 3.6}deg, rgba(255,255,255,0.06) 0deg)`,
                }}
              >
                <div className="w-16 h-16 rounded-full grid place-items-center" style={{ background: "#0A0413" }}>
                  <div className="text-center">
                    <div className="text-2xl font-black" style={{ color: scoreColor }} data-testid="practice-score">
                      {result.score}
                    </div>
                    <div className="text-[9px] text-[var(--asc-text-muted)] uppercase tracking-widest">score</div>
                  </div>
                </div>
              </div>
              <div className="flex-1 min-w-0">
                {result.mastered ? (
                  <div>
                    <div className="flex items-center gap-2">
                      <Trophy size={18} color="#22c55e" />
                      <div className="font-bold text-white" data-testid="practice-mastered">Mastered!</div>
                    </div>
                    <div className="text-sm text-[var(--asc-text-dim)] mt-0.5">
                      Saved to your portfolio (private). Feel free to keep refining or continue.
                    </div>
                  </div>
                ) : (
                  <div>
                    <div className="font-bold text-white">
                      {result.score >= 60 ? "Close! One more push." : "Good effort — let's sharpen it."}
                    </div>
                    <div className="text-sm text-[var(--asc-text-dim)] mt-0.5">
                      Mastery unlocks at 80. Follow the next step below and try again.
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Strengths */}
            {result.strengths?.length > 0 && (
              <div className="p-4 rounded-xl" style={{ background: "rgba(34,197,94,0.06)", border: "1px solid rgba(34,197,94,0.25)" }}>
                <div className="flex items-center gap-2 mb-2">
                  <CheckCircle2 size={15} color="#22c55e" />
                  <div className="asc-label" style={{ color: "#22c55e" }}>What&apos;s working</div>
                </div>
                <ul className="space-y-1.5 text-sm text-[var(--asc-text-dim)]">
                  {result.strengths.map((s, i) => (
                    <li key={i} className="flex items-start gap-2">
                      <span className="mt-1 w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: "#22c55e" }} />
                      <span>{s}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Improvements */}
            {result.improvements?.length > 0 && (
              <div className="p-4 rounded-xl" style={{ background: "rgba(255,176,0,0.05)", border: "1px solid rgba(255,176,0,0.25)" }}>
                <div className="flex items-center gap-2 mb-2">
                  <Lightbulb size={15} color="#FFB000" />
                  <div className="asc-label" style={{ color: "#FFB000" }}>Grow here</div>
                </div>
                <ul className="space-y-1.5 text-sm text-[var(--asc-text-dim)]">
                  {result.improvements.map((s, i) => (
                    <li key={i} className="flex items-start gap-2">
                      <span className="mt-1 w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: "#FFB000" }} />
                      <span>{s}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Next step (single high-leverage action) */}
            {result.next_step && (
              <div className="p-4 rounded-xl" style={{ background: "rgba(191,180,255,0.06)", border: "1px solid rgba(191,180,255,0.3)" }} data-testid="practice-next-step">
                <div className="flex items-center gap-2 mb-1.5">
                  <Zap size={15} color="#BFB4FF" />
                  <div className="asc-label" style={{ color: "#BFB4FF" }}>Your next move</div>
                </div>
                <p className="text-sm text-white leading-relaxed">{result.next_step}</p>
              </div>
            )}

            {/* AI actual response (for prompt-type challenges) */}
            {result.ai_response && (
              <div className="p-4 rounded-xl" style={{ background: "rgba(255,176,0,0.04)", border: "1px solid rgba(255,176,0,0.20)" }} data-testid="practice-ai-response">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <Sparkles size={14} color="#FFB000" />
                    <div className="asc-label" style={{ color: "#FFB000" }}>What your prompt actually produced</div>
                  </div>
                  <CardPlayButton text={result.ai_response} title="AI Response" lessonTitle={lessonTitle} size="sm" />
                </div>
                <div className="text-sm text-[var(--asc-text-dim)] whitespace-pre-wrap leading-relaxed">
                  {result.ai_response}
                </div>
              </div>
            )}

            {/* Master example — hidden until user requests it (or mastery) */}
            {result.master_example && (
              <div>
                <button
                  type="button"
                  onClick={() => setShowMasterExample((v) => !v)}
                  className="text-xs text-[var(--asc-text-muted)] hover:text-white flex items-center gap-1.5 transition"
                  data-testid="practice-master-toggle"
                >
                  {showMasterExample ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
                  {showMasterExample ? "Hide" : "See"} a strong reference answer
                </button>
                <AnimatePresence>
                  {showMasterExample && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      className="mt-3 overflow-hidden"
                    >
                      <div className="p-4 rounded-xl text-sm text-[var(--asc-text-dim)] whitespace-pre-wrap leading-relaxed" style={{ background: "rgba(191,180,255,0.05)", border: "1px dashed rgba(191,180,255,0.25)" }}>
                        {result.master_example}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Continue button */}
      <div className="mt-8 flex items-center justify-between gap-3">
        <div className="text-xs text-[var(--asc-text-muted)]">
          {result?.mastered ? (
            <span className="text-[#22c55e]">✓ Mastery achieved — carry on</span>
          ) : (
            <span>You can continue any time. Mastery is optional but earns portfolio credit.</span>
          )}
        </div>
        <button
          onClick={onAdvance}
          data-testid="practice-continue-btn"
          className={
            canAdvance || result
              ? "asc-btn-primary"
              : "asc-btn-secondary"
          }
        >
          Continue <ArrowRight size={14} />
        </button>
      </div>
    </div>
  );
}
