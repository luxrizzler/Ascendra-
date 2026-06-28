import { useEffect, useState } from "react";
import { Flame, Target, Trophy } from "lucide-react";
import { api } from "@/lib/api";

// Compact calendar showing the last 30 days as dots: filled if completed, empty if missed.
// Today's dot has a bright outline.
function MiniCalendar({ activity, today }) {
  const set = new Set(activity || []);
  // Build last 30 days
  const days = [];
  const t = new Date(today + "T00:00:00Z");
  for (let i = 29; i >= 0; i--) {
    const d = new Date(t.getTime() - i * 86400000);
    days.push(d.toISOString().slice(0, 10));
  }
  return (
    <div className="flex flex-wrap gap-1.5" data-testid="streak-calendar">
      {days.map((iso) => {
        const done = set.has(iso);
        const isToday = iso === today;
        return (
          <div
            key={iso}
            title={iso}
            data-testid={`streak-day-${iso}`}
            className="w-3.5 h-3.5 rounded-sm transition-all"
            style={{
              background: done ? "#FF6B35" : "rgba(255,255,255,0.06)",
              boxShadow: isToday ? "0 0 0 1.5px rgba(255,176,0,0.85)" : "none",
            }}
          />
        );
      })}
    </div>
  );
}

export function StreakCard() {
  const [s, setS] = useState(null);
  useEffect(() => { api.get("/streak/me").then(setS).catch(() => {}); }, []);
  if (!s) return null;
  const pct = s.next_milestone
    ? Math.min(100, Math.round((s.current_streak / s.next_milestone) * 100))
    : 100;
  return (
    <div className="asc-card p-6" data-testid="streak-card">
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2">
            <div className="w-10 h-10 rounded-full grid place-items-center" style={{ background: "rgba(255,107,53,0.18)" }}>
              <Flame size={20} color="#FF6B35" />
            </div>
            <div>
              <div className="text-xs text-[var(--asc-text-muted)] tracking-wider">DAILY STREAK</div>
              <div className="text-3xl font-black leading-none mt-1">
                <span data-testid="streak-count">{s.current_streak}</span>
                <span className="text-base font-bold ml-1 text-[var(--asc-text-dim)]">days</span>
              </div>
            </div>
          </div>
        </div>
        <div className="text-right text-xs text-[var(--asc-text-muted)]">
          <div className="flex items-center gap-1 justify-end"><Trophy size={11} /> Best</div>
          <div className="text-lg font-black text-white mt-1" data-testid="streak-longest">{s.longest_streak}</div>
        </div>
      </div>

      {/* Today goal */}
      <div className="mt-5 p-3 rounded-xl flex items-center justify-between" style={{ background: s.daily_goal_complete ? "rgba(52,211,153,0.08)" : "rgba(255,176,0,0.06)", border: `1px solid ${s.daily_goal_complete ? "#34D399" : "rgba(255,176,0,0.25)"}` }} data-testid="daily-goal">
        <div className="flex items-center gap-2">
          <Target size={14} color={s.daily_goal_complete ? "#34D399" : "#FFB000"} />
          <span className="text-sm font-bold">Today's goal</span>
        </div>
        <span className="text-xs font-black" style={{ color: s.daily_goal_complete ? "#34D399" : "#FFB000" }} data-testid="daily-goal-status">
          {s.daily_goal_done}/{s.daily_goal_target} {s.daily_goal_complete ? "✓" : "— 1 lesson"}
        </span>
      </div>

      {/* Calendar */}
      <div className="mt-5">
        <div className="text-[10px] text-[var(--asc-text-muted)] tracking-wider mb-2">LAST 30 DAYS</div>
        <MiniCalendar activity={s.activity_calendar} today={s.today} />
      </div>

      {/* Next milestone */}
      {s.next_milestone && (
        <div className="mt-5">
          <div className="flex items-center justify-between text-xs text-[var(--asc-text-muted)] mb-1.5">
            <span>Next milestone</span>
            <span><span className="text-white font-bold">{s.next_milestone}</span> days · <span className="text-white font-bold">{s.days_to_next_milestone}</span> to go</span>
          </div>
          <div className="h-2 rounded-full overflow-hidden" style={{ background: "rgba(191,180,255,0.08)" }}>
            <div className="h-full transition-all" style={{ width: `${pct}%`, background: "linear-gradient(90deg,#FF6B35,#FFB000)" }} />
          </div>
        </div>
      )}
    </div>
  );
}
