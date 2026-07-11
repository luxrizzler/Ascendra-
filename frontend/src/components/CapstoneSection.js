import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "@/lib/api";
import { Trophy, Lock, CheckCircle2, ArrowRight, Flame } from "lucide-react";
import { toast } from "sonner";

/**
 * CapstoneSection — renders the module capstone summary on a path detail page.
 * Shows: X of Y capstones passed + "Start capstone" CTA per module.
 * Certificates are gated behind capstone completion (backend enforces).
 */
export function CapstoneSection({ pathId }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!pathId) return;
    api.get(`/capstones/path/${pathId}`)
      .then(setData)
      .catch(() => setData({ capstones: [], total: 0, passed: 0 }))
      .finally(() => setLoading(false));
  }, [pathId]);

  if (loading || !data || data.total === 0) return null;

  const pct = Math.round((data.passed / data.total) * 100);

  return (
    <section className="asc-card p-6 mt-8" data-testid="capstones-section">
      <div className="flex flex-wrap items-center justify-between gap-4 mb-5">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full mb-2" style={{ background: "rgba(255,176,0,0.12)", border: "1px solid rgba(255,176,0,0.4)" }}>
            <Trophy size={12} color="#FFB000" />
            <span className="asc-label" style={{ color: "#FFB000", fontSize: 10 }}>Certification gate</span>
          </div>
          <h2 className="asc-h2 text-2xl">Module Capstones</h2>
          <p className="text-[var(--asc-text-dim)] text-sm mt-1 max-w-xl">
            Pass every capstone to earn this path’s certificate. Each capstone is a
            real applied project graded by AI against a rubric.
          </p>
        </div>
        <div className="text-right">
          <div className="text-3xl font-black" style={{ color: data.passed === data.total ? "#22c55e" : "#FFB000" }} data-testid="capstones-progress">
            {data.passed} / {data.total}
          </div>
          <div className="text-xs text-[var(--asc-text-muted)]">{pct}% complete</div>
        </div>
      </div>

      <div className="h-1.5 rounded-full overflow-hidden mb-5" style={{ background: "rgba(255,255,255,0.06)" }}>
        <div className="h-full transition-all" style={{ width: `${pct}%`, background: "linear-gradient(90deg, #FFB000, #FF6B35)" }} />
      </div>

      <div className="space-y-2">
        {data.capstones.map((c) => (
          <CapstoneRow key={c.id} capstone={c} />
        ))}
      </div>
    </section>
  );
}

function CapstoneRow({ capstone }) {
  return (
    <div className="p-4 rounded-xl flex flex-wrap items-center justify-between gap-3" style={{ background: capstone.mastered ? "rgba(34,197,94,0.06)" : "rgba(191,180,255,0.04)", border: `1px solid ${capstone.mastered ? "rgba(34,197,94,0.25)" : "var(--asc-border)"}` }} data-testid={`capstone-row-${capstone.id}`}>
      <div className="flex items-start gap-3 flex-1 min-w-0">
        <div className="w-9 h-9 rounded-full grid place-items-center flex-shrink-0" style={{ background: capstone.mastered ? "rgba(34,197,94,0.2)" : "rgba(255,176,0,0.15)" }}>
          {capstone.mastered ? <CheckCircle2 size={16} color="#22c55e" /> : <Lock size={14} color="#FFB000" />}
        </div>
        <div className="flex-1 min-w-0">
          <div className="font-bold text-white text-sm truncate">{capstone.title}</div>
          {capstone.best_score > 0 && (
            <div className="text-xs text-[var(--asc-text-muted)] mt-0.5">
              Best score: <b style={{ color: capstone.mastered ? "#22c55e" : "#FFB000" }}>{capstone.best_score}</b>{!capstone.mastered && " - try again to hit 80+"}
            </div>
          )}
        </div>
      </div>
      <Link
        to={`/capstone/${capstone.path_id}/${capstone.module_id}`}
        className={capstone.mastered ? "asc-btn-secondary text-sm" : "asc-btn-primary text-sm"}
        data-testid={`capstone-cta-${capstone.id}`}
      >
        {capstone.mastered ? "Review" : "Start capstone"} <ArrowRight size={12} />
      </Link>
    </div>
  );
}
