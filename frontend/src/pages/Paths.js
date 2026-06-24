import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import Loader from "@/components/Loader";
import TierBadge from "@/components/TierBadge";
import { Lock, ArrowRight, BookOpen, Clock, Zap } from "lucide-react";
import { canAccess } from "@/lib/utils";

export default function Paths() {
  const { user } = useAuth();
  const [paths, setPaths] = useState([]);
  const [progress, setProgress] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([api.get("/paths"), api.get("/progress")]).then(([ps, pr]) => {
      setPaths(ps.paths);
      setProgress(pr);
    }).finally(() => setLoading(false));
  }, []);

  if (loading) return <Loader />;

  return (
    <div className="max-w-7xl mx-auto px-5 sm:px-8 py-10" data-testid="paths-page">
      <div className="asc-kicker">All paths</div>
      <h1 className="asc-h2 text-4xl sm:text-5xl mt-2">Choose your ascent.</h1>
      <p className="text-[var(--asc-text-dim)] mt-2 max-w-2xl">
        Ten learning paths covering every facet of AI in 2026. From beginner fundamentals to enterprise strategy.
      </p>

      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-5 mt-8">
        {paths.map((p) => {
          const pr = progress.path_progress[p.id] || { completed: 0, total: p.total_lessons, pct: 0 };
          const locked = !canAccess(user.tier, p.tier);
          return (
            <Link
              key={p.id}
              to={`/paths/${p.id}`}
              data-testid={`path-card-${p.id}`}
              className="asc-card overflow-hidden relative"
            >
              <div className="relative h-40">
                <img src={p.image} alt={p.title} className="absolute inset-0 w-full h-full object-cover" />
                <div className="absolute inset-0" style={{ background: `linear-gradient(135deg, ${p.color}55, rgba(10,4,19,0.85))` }} />
                <div className="absolute top-3 left-3 flex gap-2">
                  <span className="px-2 py-1 rounded-full text-[10px] font-black tracking-wider" style={{ background: p.color, color: "#000" }}>{p.level}</span>
                  {p.tier !== "free" && <TierBadge tier={p.tier} />}
                </div>
                {locked && (
                  <div className="absolute inset-0 grid place-items-center backdrop-blur-sm" style={{ background: "rgba(10,4,19,0.55)" }}>
                    <Lock size={28} className="text-white" />
                  </div>
                )}
              </div>
              <div className="p-5">
                <div className="asc-label" style={{ color: p.color }}>{p.subtitle}</div>
                <h3 className="asc-h2 text-xl mt-2">{p.title}</h3>
                <p className="text-[var(--asc-text-dim)] text-sm mt-2 line-clamp-2">{p.tagline}</p>

                <div className="flex gap-3 mt-4 text-xs text-[var(--asc-text-muted)]">
                  <span className="flex items-center gap-1"><BookOpen size={12} /> {p.total_lessons}</span>
                  <span className="flex items-center gap-1"><Clock size={12} /> {p.duration}</span>
                  <span className="flex items-center gap-1"><Zap size={12} /> {p.total_xp} XP</span>
                </div>

                <div className="h-1.5 mt-4 rounded-full overflow-hidden" style={{ background: "rgba(191,180,255,0.1)" }}>
                  <div className="h-full" style={{ width: `${pr.pct}%`, background: p.color }} />
                </div>
                <div className="flex items-center justify-between mt-3">
                  <span className="text-xs text-[var(--asc-text-dim)]">{pr.completed} / {pr.total}</span>
                  <span className="flex items-center gap-1 text-sm text-[var(--asc-brand)] font-bold">{locked ? "Upgrade" : pr.completed === 0 ? "Start" : pr.pct === 100 ? "Review" : "Continue"} <ArrowRight size={14} /></span>
                </div>
              </div>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
