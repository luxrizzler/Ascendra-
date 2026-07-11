import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "@/lib/api";
import { Flame, Clock, ChevronRight, X } from "lucide-react";
import { toast } from "sonner";

/**
 * DrillWidget — shows spaced-repetition practice drills due for retry.
 * Renders on the dashboard. Empty state hides itself.
 */
export function DrillWidget() {
  const [data, setData] = useState(null);

  const load = () => api.get("/practice/drills/today").then(setData).catch(() => setData({ drills: [], due_count: 0 }));
  useEffect(() => { load(); }, []);

  const snooze = async (drillId, e) => {
    e?.preventDefault?.();
    e?.stopPropagation?.();
    try {
      await api.post(`/practice/drills/${drillId}/snooze?days=3`);
      toast.success("Snoozed 3 days");
      load();
    } catch (e) { toast.error(e.message); }
  };

  if (!data || data.due_count === 0) return null;

  return (
    <div className="asc-card p-6" data-testid="drill-widget">
      <div className="flex items-center justify-between gap-3 mb-4">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-full grid place-items-center" style={{ background: "rgba(255,107,53,0.18)" }}>
            <Flame size={16} color="#FF6B35" />
          </div>
          <div>
            <div className="asc-label" style={{ color: "#FF6B35" }}>Practice Drills</div>
            <div className="text-white font-bold text-lg">{data.due_count} due today</div>
          </div>
        </div>
        {data.upcoming_count > 0 && (
          <div className="text-xs text-[var(--asc-text-muted)]">
            +{data.upcoming_count} upcoming
          </div>
        )}
      </div>

      <div className="space-y-2">
        {data.drills.slice(0, 3).map((d) => (
          <Link
            key={d.drill_id}
            to={d.lesson_id ? `/lessons/${d.lesson_id}` : "/paths"}
            className="flex items-center justify-between gap-3 p-3 rounded-lg hover:bg-[rgba(255,255,255,0.03)] transition"
            data-testid={`drill-item-${d.drill_id}`}
          >
            <div className="flex items-center gap-3 flex-1 min-w-0">
              <Clock size={14} color="#FF6B35" className="flex-shrink-0" />
              <div className="flex-1 min-w-0">
                <div className="text-white text-sm font-bold truncate">{d.challenge_title}</div>
                <div className="text-xs text-[var(--asc-text-muted)]">
                  Last attempt scored {d.last_score} — sharpen it now
                </div>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button onClick={(e) => snooze(d.drill_id, e)} className="p-1.5 rounded-full hover:bg-[rgba(255,255,255,0.06)]" title="Snooze 3 days" data-testid={`drill-snooze-${d.drill_id}`}>
                <X size={12} color="#94a3b8" />
              </button>
              <ChevronRight size={14} color="#BFB4FF" />
            </div>
          </Link>
        ))}
      </div>

      {data.drills.length > 3 && (
        <div className="text-center mt-3">
          <span className="text-xs text-[var(--asc-text-muted)]">+{data.drills.length - 3} more due</span>
        </div>
      )}
    </div>
  );
}
