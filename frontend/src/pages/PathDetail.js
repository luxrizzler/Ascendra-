import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import Loader from "@/components/Loader";
import TierBadge from "@/components/TierBadge";
import { canAccess } from "@/lib/utils";
import { ArrowLeft, Lock, Play, CheckCircle2, ArrowRight, BookOpen, Clock, Zap } from "lucide-react";
import { toast } from "sonner";
import { CapstoneSection } from "@/components/CapstoneSection";

export default function PathDetail() {
  const { pathId } = useParams();
  const nav = useNavigate();
  const { user } = useAuth();
  const [path, setPath] = useState(null);
  const [progress, setProgress] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([api.get(`/paths/${pathId}`), api.get("/progress")])
      .then(([p, pr]) => { setPath(p); setProgress(pr); })
      .catch((e) => toast.error(e.message || "Could not load path"))
      .finally(() => setLoading(false));
  }, [pathId]);

  if (loading) return <Loader />;
  if (!path) return null;

  const locked = !canAccess(user, path.tier);
  const completedSet = new Set(progress.completed_lesson_ids);
  const allLessons = path.modules.flatMap((m) => m.lessons);
  const firstUncompleted = allLessons.find((l) => !completedSet.has(l.id));
  const pr = progress.path_progress[pathId] || { completed: 0, total: allLessons.length, pct: 0 };

  return (
    <div className="max-w-5xl mx-auto px-5 sm:px-8 py-8" data-testid="path-detail-page">
      <button onClick={() => nav("/paths")} className="flex items-center gap-2 text-sm text-[var(--asc-text-dim)] hover:text-white" data-testid="path-back-btn"><ArrowLeft size={16} /> All paths</button>

      {/* HERO */}
      <div className="asc-card overflow-hidden mt-4">
        <div className="relative h-56 sm:h-72">
          <img src={path.image} alt={path.title} className="absolute inset-0 w-full h-full object-cover" />
          <div className="absolute inset-0" style={{ background: `linear-gradient(135deg, ${path.color}88, rgba(10,4,19,0.85))` }} />
          <div className="absolute bottom-5 left-5 right-5">
            <div className="flex gap-2 mb-3">
              <span className="px-2 py-1 rounded-full text-[10px] font-black tracking-wider" style={{ background: path.color, color: "#000" }}>{path.level}</span>
              {path.tier !== "free" && <TierBadge tier={path.tier} />}
            </div>
            <div className="asc-label" style={{ color: path.color }}>{path.subtitle}</div>
            <h1 className="asc-h1 text-3xl sm:text-5xl mt-1">{path.title}</h1>
            <p className="text-[var(--asc-text-dim)] mt-3 max-w-2xl">{path.tagline}</p>
          </div>
        </div>

        <div className="p-6 flex flex-wrap items-center justify-between gap-4">
          <div className="flex gap-5 text-sm text-[var(--asc-text-dim)]">
            <span className="flex items-center gap-1"><BookOpen size={14} /> {allLessons.length} lessons</span>
            <span className="flex items-center gap-1"><Clock size={14} /> {path.duration}</span>
            <span className="flex items-center gap-1"><Zap size={14} /> {allLessons.reduce((s, l) => s + l.xp, 0)} XP</span>
          </div>
          <div className="text-sm text-[var(--asc-text-dim)]">{pr.completed}/{pr.total} done · {pr.pct}%</div>
        </div>
        <div className="h-1.5 -mt-3 rounded-full overflow-hidden mx-6 mb-6" style={{ background: "rgba(191,180,255,0.1)" }}>
          <div className="h-full" style={{ width: `${pr.pct}%`, background: path.color }} />
        </div>
      </div>

      {/* CTA */}
      {locked ? (
        <div className="asc-card p-6 mt-5 flex flex-wrap items-center justify-between gap-4" style={{ borderColor: "#FFB000" }}>
          <div>
            <div className="flex items-center gap-2"><Lock size={16} className="text-[var(--asc-brand)]" /><span className="font-bold">Requires {path.tier.toUpperCase()} tier</span></div>
            <p className="text-sm text-[var(--asc-text-dim)] mt-1">Upgrade to unlock all lessons in this path.</p>
          </div>
          <button className="asc-btn-primary" onClick={() => nav("/pricing")} data-testid="path-upgrade-btn">Upgrade <ArrowRight size={16} /></button>
        </div>
      ) : firstUncompleted ? (
        <div className="asc-card p-6 mt-5 flex flex-wrap items-center justify-between gap-4">
          <div>
            <div className="asc-label">Up next</div>
            <div className="asc-h2 text-xl mt-1">{firstUncompleted.title}</div>
          </div>
          <button className="asc-btn-primary" onClick={() => nav(`/lessons/${firstUncompleted.id}`)} data-testid="path-continue-btn">
            <Play size={14} /> {pr.completed === 0 ? "Start path" : "Continue"}
          </button>
        </div>
      ) : (
        <div className="asc-card p-6 mt-5 flex flex-wrap items-center justify-between gap-4" style={{ borderColor: "#34D399" }}>
          <div>
            <div className="flex items-center gap-2"><CheckCircle2 size={16} className="text-[var(--asc-success)]" /><span className="font-bold">Path complete</span></div>
            <p className="text-sm text-[var(--asc-text-dim)] mt-1">Your certificate has been issued. Profile → Certificates.</p>
          </div>
          <Link className="asc-btn-secondary" to="/profile">View certificate</Link>
        </div>
      )}

      {/* Modules */}
      <div className="mt-8 space-y-6">
        {path.modules.map((m, mi) => (
          <div key={m.id}>
            <div className="flex items-center gap-3 mb-3">
              <div className="w-8 h-8 rounded-full grid place-items-center font-black text-sm" style={{ background: path.color, color: "#000" }}>{mi + 1}</div>
              <h3 className="asc-h2 text-xl">{m.title}</h3>
            </div>
            <div className="space-y-2">
              {m.lessons.map((l) => {
                const done = completedSet.has(l.id);
                const disabled = locked;
                return (
                  <button
                    key={l.id}
                    disabled={disabled}
                    onClick={() => nav(`/lessons/${l.id}`)}
                    data-testid={`lesson-item-${l.id}`}
                    className={`w-full text-left asc-card p-4 flex items-center gap-4 ${disabled ? "opacity-60 cursor-not-allowed" : ""}`}
                  >
                    <div className="w-10 h-10 rounded-xl grid place-items-center shrink-0" style={{ background: done ? "#34D39922" : "#1F183A", border: `1px solid ${done ? "#34D39988" : "rgba(191,180,255,0.15)"}` }}>
                      {disabled ? <Lock size={16} color="#7E84A3" /> : done ? <CheckCircle2 size={18} color="#34D399" /> : <Play size={14} color="#FFB000" />}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="font-bold truncate">{l.title}</div>
                      <div className="text-xs text-[var(--asc-text-muted)] mt-0.5">{l.card_count} cards · {l.duration_min} min</div>
                    </div>
                    <div className="flex items-center gap-1.5 text-[var(--asc-brand)] text-sm font-bold shrink-0"><Zap size={14} /> {l.xp}</div>
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </div>
      <CapstoneSection pathId={pathId} />
    </div>
  );
}
