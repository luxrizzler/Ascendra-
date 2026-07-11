import { useEffect, useState } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { Trophy, ArrowLeft, ArrowRight, Sparkles, CheckCircle2, Lightbulb, Zap, Target } from "lucide-react";
import Loader from "@/components/Loader";
import SEO from "@/components/SEO";
import { celebrateLessonComplete } from "@/lib/celebrations";

export default function CapstonePlayer() {
  const { pathId, moduleId } = useParams();
  const nav = useNavigate();
  const [loading, setLoading] = useState(true);
  const [capstone, setCapstone] = useState(null);
  const [best, setBest] = useState(0);
  const [mastered, setMastered] = useState(false);
  const [attempt, setAttempt] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);

  useEffect(() => {
    (async () => {
      try {
        const r = await api.get(`/capstones/module/${pathId}/${moduleId}`);
        if (!r.capstone) { toast.error("No capstone for this module yet"); nav(-1); return; }
        setCapstone(r.capstone);
        setBest(r.best_score || 0);
        setMastered(r.mastered);
      } catch (e) { toast.error(e.message); }
      finally { setLoading(false); }
    })();
  }, [pathId, moduleId, nav]);

  const submit = async () => {
    if (attempt.trim().length < 30) { toast.error("Capstones need at least 30 characters — give it your all!"); return; }
    setSubmitting(true);
    setResult(null);
    try {
      const r = await api.post("/practice/attempt", {
        attempt,
        title: capstone.title,
        instruction: capstone.instruction,
        task_type: "capstone",
        rubric: capstone.rubric || [],
        path_id: pathId,
        lesson_id: null,
      });
      setResult(r);
      if (r.mastered) {
        celebrateLessonComplete();
        toast.success("🏆 Capstone passed! Certificate progress updated.", { duration: 6000 });
        setMastered(true);
        setBest(Math.max(best, r.score));
      } else {
        toast.message(`Score ${r.score}/100 — need 80+ to pass. Iterate and try again.`);
      }
    } catch (e) { toast.error(e.message); }
    finally { setSubmitting(false); }
  };

  if (loading) return <div className="min-h-screen grid place-items-center"><Loader /></div>;
  if (!capstone) return null;

  return (
    <div className="min-h-screen px-6 py-8" data-testid="capstone-player">
      <SEO title={`Capstone: ${capstone.title}`} description="Complete this capstone to earn your certificate." path={`/capstone/${pathId}/${moduleId}`} noindex />
      <div className="max-w-3xl mx-auto">
        <button onClick={() => nav(-1)} className="text-xs text-[var(--asc-text-muted)] hover:text-white flex items-center gap-1 mb-4" data-testid="capstone-back">
          <ArrowLeft size={12} /> Back to path
        </button>

        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full mb-4" style={{ background: mastered ? "rgba(34,197,94,0.12)" : "rgba(255,176,0,0.12)", border: `1px solid ${mastered ? "rgba(34,197,94,0.4)" : "rgba(255,176,0,0.4)"}` }}>
          <Trophy size={12} color={mastered ? "#22c55e" : "#FFB000"} />
          <span className="asc-label" style={{ color: mastered ? "#22c55e" : "#FFB000" }}>
            {mastered ? "Passed" : "Module Capstone"}
          </span>
        </div>

        <h1 className="asc-h1 text-3xl sm:text-4xl" data-testid="capstone-title">{capstone.title}</h1>
        <p className="text-[var(--asc-text-dim)] mt-3 leading-relaxed" data-testid="capstone-instruction">{capstone.instruction}</p>

        {capstone.success_criteria?.length > 0 && (
          <div className="mt-5 p-4 rounded-xl" style={{ background: "rgba(191,180,255,0.05)", border: "1px solid rgba(191,180,255,0.18)" }}>
            <div className="asc-label mb-2">Success criteria</div>
            <ul className="space-y-1.5 text-sm text-[var(--asc-text-dim)]">
              {capstone.success_criteria.map((c, i) => <li key={i} className="flex items-start gap-2"><Target size={12} color="#BFB4FF" className="flex-shrink-0 mt-1" />{c}</li>)}
            </ul>
          </div>
        )}

        {best > 0 && (
          <div className="mt-4 text-sm text-[var(--asc-text-muted)]">
            Best score so far: <b style={{ color: mastered ? "#22c55e" : "#FFB000" }}>{best}</b>{!mastered && " — need 80+ to pass"}
          </div>
        )}

        <div className="mt-6">
          <label className="asc-label mb-2 block">YOUR CAPSTONE SUBMISSION</label>
          <textarea
            value={attempt}
            onChange={(e) => setAttempt(e.target.value)}
            rows={10}
            placeholder="Take your time. This is your chance to show real applied understanding of the whole module..."
            className="w-full p-4 rounded-xl border outline-none resize-y focus:border-[#FFB000]"
            style={{ background: "#1F183A", borderColor: "rgba(191,180,255,0.12)", color: "#fff" }}
            data-testid="capstone-textarea"
          />
          <div className="flex items-center justify-between mt-3 gap-3 flex-wrap">
            <div className="text-xs text-[var(--asc-text-muted)]">{attempt.length}/6000 · Graded by Claude against a rubric · Pass = 80+</div>
            <button onClick={submit} disabled={submitting || !attempt.trim()} className="asc-btn-primary" data-testid="capstone-submit">
              {submitting ? (<>Grading… <Sparkles size={14} className="animate-pulse" /></>) : (<>Submit capstone <ArrowRight size={14} /></>)}
            </button>
          </div>
        </div>

        {result && (
          <div className="mt-8 space-y-4" data-testid="capstone-result">
            <div className="p-5 rounded-2xl border-2" style={{ background: result.mastered ? "linear-gradient(135deg, rgba(34,197,94,0.12), rgba(255,176,0,0.08))" : "rgba(255,176,0,0.05)", borderColor: result.mastered ? "rgba(34,197,94,0.4)" : "rgba(255,176,0,0.3)" }}>
              <div className="text-xs asc-label">Score</div>
              <div className="text-5xl font-black" style={{ color: result.mastered ? "#22c55e" : "#FFB000" }} data-testid="capstone-score">{result.score}<span className="text-2xl text-[var(--asc-text-muted)]">/100</span></div>
              <div className="text-white font-bold mt-2">{result.mastered ? "🏆 You passed the capstone!" : "Not quite — iterate and resubmit."}</div>
            </div>
            {result.strengths?.length > 0 && (
              <div className="p-4 rounded-xl" style={{ background: "rgba(34,197,94,0.06)", border: "1px solid rgba(34,197,94,0.25)" }}>
                <div className="asc-label mb-2" style={{ color: "#22c55e" }}>Strengths</div>
                <ul className="space-y-1.5 text-sm text-[var(--asc-text-dim)]">{result.strengths.map((s, i) => <li key={i} className="flex gap-2"><CheckCircle2 size={13} color="#22c55e" className="mt-0.5 flex-shrink-0" />{s}</li>)}</ul>
              </div>
            )}
            {result.improvements?.length > 0 && (
              <div className="p-4 rounded-xl" style={{ background: "rgba(255,176,0,0.05)", border: "1px solid rgba(255,176,0,0.25)" }}>
                <div className="asc-label mb-2" style={{ color: "#FFB000" }}>Grow here</div>
                <ul className="space-y-1.5 text-sm text-[var(--asc-text-dim)]">{result.improvements.map((s, i) => <li key={i} className="flex gap-2"><Lightbulb size={13} color="#FFB000" className="mt-0.5 flex-shrink-0" />{s}</li>)}</ul>
              </div>
            )}
            {result.next_step && (
              <div className="p-4 rounded-xl" style={{ background: "rgba(191,180,255,0.06)", border: "1px solid rgba(191,180,255,0.3)" }}>
                <div className="asc-label mb-1.5" style={{ color: "#BFB4FF" }}>Your next move</div>
                <p className="text-sm text-white leading-relaxed flex items-start gap-2"><Zap size={14} color="#BFB4FF" className="mt-0.5 flex-shrink-0" />{result.next_step}</p>
              </div>
            )}
            {mastered && (
              <Link to={`/paths`} className="asc-btn-primary" data-testid="capstone-back-to-path">Back to path <ArrowRight size={14} /></Link>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
