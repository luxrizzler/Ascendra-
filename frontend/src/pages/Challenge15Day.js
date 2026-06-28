import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowLeft, ArrowRight, CheckCircle2, Flame, Lock, Play, Trophy, Zap } from "lucide-react";
import { api } from "@/lib/api";
import Loader from "@/components/Loader";

export default function Challenge15Day() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get("/challenge/15day")
      .then(setData)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Loader label="Loading your challenge…" />;
  if (!data) return null;

  const pct = Math.round((data.completed_count / data.total_days) * 100);

  return (
    <div className="min-h-screen" style={{ background: "#0A0413" }}>
      <div className="max-w-3xl mx-auto px-6 py-10">
        <Link to="/dashboard" className="text-xs text-[var(--asc-text-muted)] hover:text-white flex items-center gap-1.5"><ArrowLeft size={12} /> Back to dashboard</Link>
        {/* Header */}
        <div className="mt-4 relative overflow-hidden rounded-2xl p-7 sm:p-9" style={{ background: "linear-gradient(135deg, rgba(255,107,53,0.18), rgba(255,176,0,0.08))", border: "1px solid rgba(255,176,0,0.35)" }} data-testid="challenge-hero">
          <div className="flex items-center gap-2"><Flame size={16} color="#FF6B35" /><div className="text-[10px] tracking-widest font-black" style={{ color: "#FF6B35" }}>{data.is_complete ? "CHALLENGE COMPLETE" : "FLAGSHIP CHALLENGE"}</div></div>
          <h1 className="asc-h2 text-4xl sm:text-5xl mt-2">{data.name}</h1>
          <p className="text-[var(--asc-text-dim)] mt-3 leading-relaxed max-w-2xl">
            One short lesson per day. 15 days to go from curious to capable.
            {data.is_complete ? " You did it. Take a bow. 🏆" : ` You're on Day ${data.current_day} of ${data.total_days}.`}
          </p>
          <div className="flex items-center gap-4 mt-5 flex-wrap">
            <div className="text-xs text-[var(--asc-text-muted)]">
              <span className="text-white font-black text-base">{data.completed_count}</span> / {data.total_days} days complete
            </div>
            <div className="h-2 flex-1 min-w-[160px] max-w-[300px] rounded-full overflow-hidden" style={{ background: "rgba(191,180,255,0.1)" }}>
              <motion.div initial={{ width: 0 }} animate={{ width: `${pct}%` }} transition={{ duration: 0.6 }} className="h-full" style={{ background: "linear-gradient(90deg,#FF6B35,#FFB000)" }} data-testid="challenge-progress-bar" />
            </div>
            <div className="text-xs font-black" style={{ color: "#FFB000" }}>{pct}%</div>
          </div>
        </div>

        {/* Roadmap */}
        <div className="mt-8 space-y-3" data-testid="challenge-roadmap">
          {data.days.map((d, i) => (
            <DayCard key={d.day} day={d} highlight={d.day === data.current_day && !data.is_complete} />
          ))}
        </div>

        {data.is_complete && (
          <div className="asc-card p-6 mt-8 text-center" data-testid="challenge-complete-banner">
            <div className="w-16 h-16 rounded-full grid place-items-center mx-auto mb-3" style={{ background: "radial-gradient(circle, rgba(255,176,0,0.45), rgba(255,176,0,0.08))" }}>
              <Trophy size={32} color="#FFB000" />
            </div>
            <h2 className="asc-h2 text-2xl">Challenge complete!</h2>
            <p className="text-[var(--asc-text-dim)] mt-2">You committed and you finished. Most never do.</p>
            <div className="flex gap-3 mt-5 justify-center">
              <Link to="/paths" className="asc-btn-primary">Pick your next path <ArrowRight size={14} /></Link>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function DayCard({ day, highlight }) {
  const locked = day.status === "locked";
  const done = day.status === "completed";
  const Icon = done ? CheckCircle2 : (locked ? Lock : Play);
  const accent = done ? "#34D399" : (locked ? "#7a7a85" : "#FFB000");
  const bg = highlight
    ? "linear-gradient(90deg, rgba(255,176,0,0.10), rgba(124,58,237,0.04))"
    : undefined;
  const border = highlight ? "#FFB000" : (done ? "rgba(52,211,153,0.30)" : (locked ? "rgba(191,180,255,0.10)" : "rgba(191,180,255,0.18)"));

  const inner = (
    <div className="flex items-center gap-4">
      <div className="shrink-0 w-12 h-12 rounded-2xl grid place-items-center font-black" style={{ background: done ? "rgba(52,211,153,0.18)" : (locked ? "rgba(191,180,255,0.06)" : "rgba(255,176,0,0.18)"), color: accent }}>
        {locked ? <Lock size={18} /> : (done ? <CheckCircle2 size={20} fill="rgba(52,211,153,0.25)" /> : <span>{day.day}</span>)}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <div className="text-[10px] tracking-widest font-black" style={{ color: accent }}>DAY {day.day}{done ? " · DONE" : (locked ? " · LOCKED" : "")}</div>
          {day.xp && !locked && <span className="text-[10px] font-black px-1.5 py-0.5 rounded-full" style={{ background: "rgba(255,176,0,0.12)", color: "#FFB000" }}><Zap size={9} className="inline -mt-px" /> {day.xp} XP</span>}
        </div>
        <div className="font-bold text-base mt-0.5 truncate" data-testid={`day-${day.day}-title`}>{day.title || day.theme}</div>
        <div className="text-xs text-[var(--asc-text-muted)] truncate">{day.theme}{day.duration_min ? ` · ${day.duration_min} min` : ""}</div>
      </div>
      {!locked && (
        <div className="shrink-0">
          {done ? (
            <span className="text-xs font-bold" style={{ color: "#34D399" }}>Replay →</span>
          ) : (
            <Icon size={16} color={accent} />
          )}
        </div>
      )}
    </div>
  );

  if (locked) {
    return (
      <div className="asc-card p-4 opacity-60" style={{ borderColor: border, background: bg }} data-testid={`day-${day.day}-card`} aria-disabled>
        {inner}
      </div>
    );
  }
  return (
    <Link to={`/lessons/${day.lesson_id}`} className="asc-card p-4 block hover:scale-[1.005] transition-transform" style={{ borderColor: border, background: bg }} data-testid={`day-${day.day}-card`}>
      {inner}
    </Link>
  );
}
