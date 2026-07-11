import { useEffect, useState } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { api } from "@/lib/api";
import Loader from "@/components/Loader";
import { ArrowLeft, ArrowRight, CheckCircle2, X, Zap, Trophy, Sparkles } from "lucide-react";
import { toast } from "sonner";
import { CardRouter, isInteractive } from "@/components/lesson/CardRouter";
import { LessonAudioBar } from "@/components/lesson/LessonAudioBar";
import { StreakMilestoneModal } from "@/components/streak/StreakMilestoneModal";
import { celebrateLessonComplete, celebrateStreakMilestone } from "@/lib/celebrations";
import { tts } from "@/lib/tts";

export default function LessonPlayer() {
  const { lessonId } = useParams();
  const nav = useNavigate();
  const [lesson, setLesson] = useState(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState(null);

  // idx: 0..cards.length-1 -> cards; cards.length -> quiz; cards.length+1 -> result
  const [idx, setIdx] = useState(0);
  const [pick, setPick] = useState(null);
  const [showResult, setShowResult] = useState(false);
  const [completion, setCompletion] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [milestoneDays, setMilestoneDays] = useState(null);

  // Play-all mode: when ON, finishing TTS of a text card auto-advances to next card.
  const [playAll, setPlayAll] = useState(false);

  useEffect(() => {
    setLoading(true);
    api.get(`/lessons/${lessonId}`)
      .then((l) => {
        setLesson(l); setIdx(0); setPick(null);
        setShowResult(false); setCompletion(null);
      })
      .catch((e) => {
        if (/(403|requires)/i.test(e.message || "")) {
          toast.error("This lesson requires an upgrade.");
          nav("/pricing");
        } else {
          setErr(e.message || "Could not load lesson");
        }
      })
      .finally(() => setLoading(false));
  }, [lessonId, nav]);

  // Stop any ongoing speech when the lesson page unmounts or the user navigates cards.
  useEffect(() => () => tts.stop(), []);
  useEffect(() => { tts.stop(); }, [idx]);

  const total = lesson ? lesson.cards.length : 0;
  const onQuiz = lesson && idx === total;
  const onDone = lesson && idx > total;

  const next = () => setIdx((i) => Math.min(i + 1, total));
  const prev = () => setIdx((i) => Math.max(i - 1, 0));

  const submitQuiz = async () => {
    if (pick === null) return;
    setShowResult(true);
    setSubmitting(true);
    try {
      const r = await api.post("/progress/complete", { lesson_id: lessonId });
      setCompletion(r);
      setIdx(total + 1);
      celebrateLessonComplete();
      if (r.streak_milestone) {
        setMilestoneDays(r.streak_milestone);
        setTimeout(celebrateStreakMilestone, 600);
      }
    } catch (e) {
      toast.error(e.message || "Could not save progress");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <Loader label="Loading lesson…" />;
  if (err) {
    return (
      <div className="min-h-[60vh] grid place-items-center p-6">
        <div className="asc-card p-6 max-w-md text-center">
          <div className="text-[var(--asc-danger)]">{err}</div>
          <Link to="/paths" className="asc-btn-secondary mt-4 inline-flex"><ArrowLeft size={14} />Back to paths</Link>
        </div>
      </div>
    );
  }
  if (!lesson) return null;

  const progressPct = onDone ? 100 : Math.round(((idx + (onQuiz ? 0 : 1)) / (total + 1)) * 100);
  const currentCard = !onQuiz && !onDone ? lesson.cards[idx] : null;
  const lockProgression = currentCard ? isInteractive(currentCard) : false;

  return (
    <div className="min-h-screen" data-testid="lesson-player" style={{ background: "#0A0413" }}>
      {/* Top bar */}
      <div className="sticky top-0 z-30 asc-glass">
        <div className="max-w-3xl mx-auto px-5 py-3 flex items-center gap-4">
          <button onClick={() => { tts.stop(); nav(-1); }} className="shrink-0 p-2 rounded-full hover:bg-white/5" data-testid="lesson-close-btn"><X size={18} /></button>
          <div className="flex-1">
            <div className="text-xs text-[var(--asc-text-muted)] truncate">{lesson.path_title} · {lesson.module_title}</div>
            <div className="h-1.5 rounded-full mt-1.5 overflow-hidden" style={{ background: "rgba(191,180,255,0.1)" }}>
              <div className="h-full transition-all" style={{ width: `${progressPct}%`, background: `linear-gradient(90deg, ${lesson.path_color}, #FFB000)` }} />
            </div>
          </div>
          <div className="shrink-0 px-2 py-1 rounded-full text-[10px] font-black flex items-center gap-1" style={{ background: "rgba(255,176,0,0.15)", color: "#FFB000" }}><Zap size={11} /> {lesson.xp} XP</div>
        </div>
      </div>

      <div className="max-w-3xl mx-auto px-5 py-8">
        {/* Title */}
        <div className="mb-4">
          <div className="asc-label" style={{ color: lesson.path_color }}>{lesson.module_title}</div>
          <h1 className="asc-h2 text-3xl sm:text-4xl mt-2">{lesson.title}</h1>
        </div>

        {/* Audio bar */}
        {!onQuiz && !onDone && (
          <LessonAudioBar
            playAll={playAll}
            onTogglePlayAll={() => {
              const nextOn = !playAll;
              setPlayAll(nextOn);
              if (nextOn && currentCard && currentCard.kind !== "playground" && currentCard.kind !== "fill_blank") {
                // Kick off the current card immediately
                const text = currentCard.kind === "knowledge_check"
                  ? `${currentCard.title}. ${currentCard.question}`
                  : `${currentCard.title}. ${currentCard.body}`;
                tts.speak(text, {
                  title: currentCard.title,
                  artist: "Ascendra Academy",
                  album: lesson.title,
                  onEnd: () => { if (idx < total - 1) next(); },
                });
              } else if (!nextOn) {
                tts.stop();
              }
            }}
            lessonTitle={lesson.title}
          />
        )}

        {/* Card / Quiz / Result */}
        <AnimatePresence mode="wait">
          {!onQuiz && !onDone && (
            <motion.div
              key={`card-${idx}-${currentCard?.kind || "text"}`}
              initial={{ opacity: 0, x: 40 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -40 }}
              transition={{ duration: 0.25 }}
              drag={lockProgression ? false : "x"}
              dragConstraints={{ left: 0, right: 0 }}
              dragElastic={0.3}
              onDragEnd={(e, info) => {
                if (lockProgression) return;
                if (info.offset.x < -80) next();
                else if (info.offset.x > 80) prev();
              }}
            >
              <CardRouter
                card={currentCard}
                idx={idx}
                total={total}
                lessonTitle={lesson.title}
                lessonId={lessonId}
                pathId={lesson.path_id}
                onAdvance={next}
                autoplay={playAll}
              />
            </motion.div>
          )}

          {onQuiz && !showResult && (
            <motion.div key="quiz" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="asc-card p-8 sm:p-10">
              <div className="flex items-center gap-2 mb-5">
                <div className="w-9 h-9 rounded-full grid place-items-center" style={{ background: "rgba(124,58,237,0.18)" }}><Sparkles size={16} color="#BFB4FF" /></div>
                <div className="text-xs text-[var(--asc-text-muted)] tracking-wider">FINAL CHECK FOR UNDERSTANDING</div>
              </div>
              <h3 className="asc-h2 text-2xl sm:text-3xl">{lesson.quiz.question}</h3>
              <div className="space-y-3 mt-5">
                {lesson.quiz.options.map((o, i) => (
                  <button
                    key={i}
                    type="button"
                    onClick={() => setPick(i)}
                    data-testid={`quiz-option-${i}`}
                    className="w-full text-left p-4 rounded-xl border transition-all"
                    style={{
                      background: pick === i ? "rgba(255,176,0,0.06)" : "#1F183A",
                      borderColor: pick === i ? "#FFB000" : "rgba(191,180,255,0.12)",
                    }}
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-7 h-7 rounded-full grid place-items-center font-black text-sm" style={{ background: pick === i ? "#FFB000" : "#15102B", color: pick === i ? "#000" : "#fff" }}>{String.fromCharCode(65 + i)}</div>
                      <span className="font-bold text-base">{o}</span>
                    </div>
                  </button>
                ))}
              </div>
              <button
                onClick={submitQuiz}
                disabled={pick === null || submitting}
                data-testid="quiz-submit-btn"
                className="asc-btn-primary mt-6 w-full justify-center disabled:opacity-50"
              >
                {submitting ? "Saving…" : "Submit answer"} <ArrowRight size={16} />
              </button>
            </motion.div>
          )}

          {onDone && completion && (
            <motion.div key="done" initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} className="asc-card p-8 sm:p-10 text-center">
              <div className="w-20 h-20 rounded-full grid place-items-center mx-auto mb-4" style={{ background: pick === lesson.quiz.answer_index ? "rgba(52,211,153,0.18)" : "rgba(255,176,0,0.18)" }}>
                {pick === lesson.quiz.answer_index ? <CheckCircle2 size={42} color="#34D399" /> : <Sparkles size={36} color="#FFB000" />}
              </div>
              <div className="asc-kicker">{pick === lesson.quiz.answer_index ? "Correct!" : "Good try!"}</div>
              <h3 className="asc-h2 text-3xl mt-2">+{completion.awarded_xp} XP</h3>
              {pick !== lesson.quiz.answer_index && (
                <div className="mt-4 p-4 rounded-xl text-left" style={{ background: "#1F183A" }}>
                  <div className="text-xs text-[var(--asc-brand)] font-bold mb-1">CORRECT ANSWER</div>
                  <div className="font-bold">{String.fromCharCode(65 + lesson.quiz.answer_index)}. {lesson.quiz.options[lesson.quiz.answer_index]}</div>
                </div>
              )}
              {lesson.quiz.explanation && (
                <p className="text-[var(--asc-text-dim)] mt-4 leading-relaxed">{lesson.quiz.explanation}</p>
              )}
              {completion.newly_completed_paths.length > 0 && (
                <div className="mt-5 p-4 rounded-xl border" style={{ background: "rgba(255,176,0,0.06)", borderColor: "#FFB000" }}>
                  <div className="flex items-center gap-2 justify-center"><Trophy size={20} color="#FFB000" /><span className="font-black text-lg">Path complete!</span></div>
                  <div className="text-[var(--asc-text-dim)] text-sm mt-2">A certificate has been issued to your profile.</div>
                  {completion.certificates_issued[0] && (
                    <Link to={`/certificate/${completion.certificates_issued[0]}`} className="asc-btn-primary mt-3 inline-flex">View certificate <ArrowRight size={14} /></Link>
                  )}
                </div>
              )}
              <div className="flex gap-3 mt-6 justify-center flex-wrap">
                <Link to={`/paths/${lesson.path_id}`} className="asc-btn-secondary">Back to path</Link>
                <button onClick={() => nav(`/paths/${lesson.path_id}`)} className="asc-btn-primary">Next lesson <ArrowRight size={14} /></button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Nav controls for cards. Hidden on interactive cards (they have their own Continue). */}
        {!onQuiz && !onDone && !lockProgression && (
          <div className="flex items-center justify-between mt-6">
            <button onClick={prev} disabled={idx === 0} data-testid="lesson-prev-btn" className={`asc-btn-secondary text-sm ${idx === 0 ? "opacity-40 cursor-not-allowed" : ""}`}><ArrowLeft size={14} /> Prev</button>
            <div className="text-xs text-[var(--asc-text-muted)]">Card {idx + 1} of {total}</div>
            <button onClick={next} data-testid="lesson-next-btn" className="asc-btn-primary text-sm">
              {idx === total - 1 ? "To quiz" : "Next"} <ArrowRight size={14} />
            </button>
          </div>
        )}

        {/* For interactive cards, give a discreet Back button so they can re-listen to prior cards */}
        {!onQuiz && !onDone && lockProgression && idx > 0 && (
          <div className="flex items-center justify-start mt-6">
            <button onClick={prev} data-testid="lesson-prev-btn" className="asc-btn-secondary text-sm"><ArrowLeft size={14} /> Prev</button>
          </div>
        )}
      </div>

      {/* Streak milestone modal — pops when user crosses 3/7/14/30/60/100-day */}
      <StreakMilestoneModal open={!!milestoneDays} days={milestoneDays || 0} onClose={() => setMilestoneDays(null)} />
    </div>
  );
}
