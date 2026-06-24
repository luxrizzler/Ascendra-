import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import Loader from "@/components/Loader";
import TierBadge from "@/components/TierBadge";
import { Flame, Sparkles, ArrowRight, Trophy, Layers, MessageSquare } from "lucide-react";

export default function Dashboard() {
  const { user } = useAuth();
  const [progress, setProgress] = useState(null);
  const [paths, setPaths] = useState([]);
  const [certs, setCerts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.get("/progress"),
      api.get("/paths"),
      api.get("/certificates"),
    ]).then(([p, ps, c]) => {
      setProgress(p);
      setPaths(ps.paths);
      setCerts(c.certificates);
    }).finally(() => setLoading(false));
  }, []);

  if (loading) return <Loader />;

  const recId = user?.recommended_path_id;
  const recommended = paths.find((p) => p.id === recId) || paths[0];
  const inProgress = paths.filter((p) => {
    const pr = progress?.path_progress?.[p.id];
    return pr && pr.completed > 0 && pr.pct < 100;
  });

  return (
    <div className="max-w-7xl mx-auto px-5 sm:px-8 py-10" data-testid="dashboard-page">
      {/* Hero */}
      <div className="flex flex-wrap items-end justify-between gap-4 mb-8">
        <div>
          <div className="asc-kicker">Your Ascent</div>
          <h1 className="asc-h2 text-4xl sm:text-5xl mt-2">
            Hey {user?.name?.split(" ")[0] || "there"}.
          </h1>
          <p className="text-[var(--asc-text-dim)] mt-2">Pick up where you left off.</p>
        </div>
        {user && <TierBadge tier={user.tier} />}
      </div>

      {/* Stats */}
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard icon={Flame} label="Streak" value={`${progress.streak_days} d`} hint="Show up daily." color="#FF6B35" />
        <StatCard icon={Sparkles} label="Total XP" value={progress.total_xp.toLocaleString()} hint={`Level ${progress.level}`} color="#FFB000" />
        <StatCard icon={Trophy} label="Certificates" value={certs.length} hint="Completed paths." color="#7C3AED" />
        <StatCard icon={Layers} label="Lessons done" value={progress.completed_lesson_ids.length} hint="Keep climbing." color="#34D399" />
      </div>

      {/* Level progress */}
      <div className="asc-card p-6 mt-6" data-testid="dashboard-level-card">
        <div className="flex items-end justify-between flex-wrap gap-2">
          <div>
            <div className="asc-label">Level {progress.level}</div>
            <div className="asc-h2 text-2xl mt-1">Onward.</div>
          </div>
          <div className="text-sm text-[var(--asc-text-dim)]">
            {progress.xp_to_next_level} XP to level {progress.level + 1}
          </div>
        </div>
        <div className="h-2 mt-4 rounded-full overflow-hidden" style={{ background: "rgba(191,180,255,0.1)" }}>
          <div className="h-full" style={{ width: `${progress.level_progress_pct}%`, background: "linear-gradient(90deg, #E8C572, #FFB000, #FF6B35)" }} />
        </div>
      </div>

      {/* Continue learning */}
      {inProgress.length > 0 && (
        <section className="mt-10">
          <div className="flex items-end justify-between mb-4">
            <h2 className="asc-h2 text-2xl">Continue learning</h2>
            <Link to="/paths" className="text-sm text-[var(--asc-brand)] hover:underline">All paths →</Link>
          </div>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {inProgress.map((p) => (
              <PathRowCard key={p.id} path={p} progress={progress.path_progress[p.id]} />
            ))}
          </div>
        </section>
      )}

      {/* Recommended */}
      {recommended && (
        <section className="mt-10">
          <div className="asc-kicker mb-3">Recommended for you</div>
          <Link to={`/paths/${recommended.id}`} className="asc-card p-8 grid md:grid-cols-2 gap-6 overflow-hidden" data-testid="dashboard-recommended-card">
            <div className="relative h-48 md:h-full rounded-2xl overflow-hidden">
              <img src={recommended.image} alt={recommended.title} className="absolute inset-0 w-full h-full object-cover" />
              <div className="absolute inset-0" style={{ background: `linear-gradient(135deg, ${recommended.color}66, transparent)` }} />
              <div className="absolute top-3 left-3 px-2 py-1 rounded-full text-[10px] font-black tracking-wider" style={{ background: recommended.color, color: "#000" }}>{recommended.level}</div>
            </div>
            <div className="flex flex-col justify-center">
              <div className="asc-label">{recommended.subtitle}</div>
              <h3 className="asc-h2 text-3xl mt-2">{recommended.title}</h3>
              <p className="text-[var(--asc-text-dim)] mt-3">{recommended.tagline}</p>
              <div className="flex gap-3 mt-5 text-sm text-[var(--asc-text-muted)]">
                <span>{recommended.total_lessons} lessons</span>
                <span>·</span>
                <span>{recommended.duration}</span>
                <span>·</span>
                <span>{recommended.total_xp} XP</span>
              </div>
              <div className="mt-6"><span className="asc-btn-primary text-sm">Open path <ArrowRight size={14} /></span></div>
            </div>
          </Link>
        </section>
      )}

      {/* Tutor + cert teasers */}
      <section className="mt-10 grid md:grid-cols-2 gap-4">
        <Link to="/tutor" className="asc-card p-6 flex items-center gap-4" data-testid="dashboard-tutor-card">
          <div className="w-14 h-14 rounded-2xl grid place-items-center" style={{ background: "rgba(124,58,237,0.18)" }}>
            <MessageSquare size={26} color="#BFB4FF" />
          </div>
          <div className="flex-1">
            <div className="asc-h2 text-lg">Ask the AI Tutor</div>
            <div className="text-[var(--asc-text-dim)] text-sm">Claude Sonnet 4.5 · 24/7 personal coach.</div>
          </div>
          <ArrowRight size={18} />
        </Link>
        {certs.length > 0 ? (
          <Link to={`/certificate/${certs[0].id}`} className="asc-card p-6 flex items-center gap-4">
            <div className="w-14 h-14 rounded-2xl grid place-items-center" style={{ background: "rgba(255,176,0,0.18)" }}>
              <Trophy size={26} color="#FFB000" />
            </div>
            <div className="flex-1">
              <div className="asc-h2 text-lg">Your latest certificate</div>
              <div className="text-[var(--asc-text-dim)] text-sm">{certs[0].path_title}</div>
            </div>
            <ArrowRight size={18} />
          </Link>
        ) : (
          <div className="asc-card p-6 flex items-center gap-4 opacity-80">
            <div className="w-14 h-14 rounded-2xl grid place-items-center" style={{ background: "rgba(255,176,0,0.18)" }}>
              <Trophy size={26} color="#FFB000" />
            </div>
            <div className="flex-1">
              <div className="asc-h2 text-lg">No certificates yet</div>
              <div className="text-[var(--asc-text-dim)] text-sm">Complete a path to earn your first certificate.</div>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}

function StatCard({ icon: Icon, label, value, hint, color }) {
  return (
    <div className="asc-card p-5">
      <div className="flex items-start gap-3">
        <div className="w-10 h-10 rounded-xl grid place-items-center" style={{ background: `${color}22`, border: `1px solid ${color}55` }}>
          <Icon size={18} color={color} />
        </div>
        <div className="flex-1">
          <div className="asc-label">{label}</div>
          <div className="asc-h2 text-2xl mt-1">{value}</div>
          <div className="text-xs text-[var(--asc-text-muted)] mt-1">{hint}</div>
        </div>
      </div>
    </div>
  );
}

function PathRowCard({ path, progress }) {
  return (
    <Link to={`/paths/${path.id}`} className="asc-card overflow-hidden">
      <div className="relative h-36">
        <img src={path.image} alt={path.title} className="absolute inset-0 w-full h-full object-cover" />
        <div className="absolute inset-0" style={{ background: `linear-gradient(135deg, ${path.color}55, rgba(10,4,19,0.7))` }} />
      </div>
      <div className="p-5">
        <div className="asc-label" style={{ color: path.color }}>{path.subtitle}</div>
        <div className="asc-h2 text-lg mt-1">{path.title}</div>
        <div className="h-1.5 mt-4 rounded-full overflow-hidden" style={{ background: "rgba(191,180,255,0.1)" }}>
          <div className="h-full" style={{ width: `${progress.pct}%`, background: path.color }} />
        </div>
        <div className="text-xs text-[var(--asc-text-dim)] mt-2">{progress.completed} / {progress.total} lessons done</div>
      </div>
    </Link>
  );
}
