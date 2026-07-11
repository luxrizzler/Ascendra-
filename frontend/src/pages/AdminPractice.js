import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { Target, Trophy, Users, TrendingUp, ExternalLink } from "lucide-react";

export default function AdminPractice() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const s = await api.get("/admin/practice/stats");
      setStats(s);
    } catch (e) { toast.error(e.message); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  if (loading) return <div className="min-h-screen grid place-items-center">Loading…</div>;
  if (!stats) return null;

  const total = Math.max(1, stats.total_attempts);
  const dist = stats.score_distribution || {};
  const buckets = [
    { key: "0-39", label: "0-39", color: "#EF4444" },
    { key: "40-59", label: "40-59", color: "#FFB000" },
    { key: "60-79", label: "60-79", color: "#38BDF8" },
    { key: "80-100", label: "80-100 (mastered)", color: "#22c55e" },
  ];

  return (
    <div className="min-h-screen px-6 py-8" data-testid="admin-practice-page">
      <div className="max-w-7xl mx-auto">
        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-[var(--asc-border-strong)] mb-3" style={{ background: "rgba(34,197,94,0.10)" }}>
          <Target size={13} color="#22c55e" />
          <span className="asc-label" style={{ color: "#22c55e" }}>Practice Lab</span>
        </div>
        <h1 className="asc-h1 text-3xl sm:text-4xl" data-testid="admin-practice-heading">Try It Live — Admin</h1>
        <p className="text-[var(--asc-text-dim)] mt-2 text-sm max-w-2xl">
          Track applied-practice engagement across the platform. Attempts, mastery rate, and score distribution live-update as users practice.
        </p>

        {/* Stats */}
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 mt-6">
          <StatCard icon={Target} label="Challenges" value={stats.total_challenges} sub="active challenges" color="#22c55e" />
          <StatCard icon={TrendingUp} label="Attempts" value={stats.total_attempts} sub="across all users" color="#FFB000" />
          <StatCard icon={Trophy} label="Masteries" value={stats.mastered_attempts} sub={`${Math.round((stats.mastered_attempts/total)*100)}% mastery rate`} color="#BFB4FF" />
          <StatCard icon={Users} label="Users practicing" value={stats.unique_users_practicing} sub="unique learners" color="#38BDF8" />
        </div>

        {/* Score distribution */}
        <div className="asc-card p-6 mt-6">
          <div className="asc-label mb-4">Score Distribution</div>
          <div className="space-y-3">
            {buckets.map((b) => {
              const count = dist[b.key] || 0;
              const pct = total > 0 ? Math.round((count/total)*100) : 0;
              return (
                <div key={b.key} data-testid={`bucket-${b.key}`}>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-[var(--asc-text-dim)]">{b.label}</span>
                    <span className="text-white font-bold">{count} <span className="text-[var(--asc-text-muted)]">({pct}%)</span></span>
                  </div>
                  <div className="h-2 rounded-full overflow-hidden" style={{ background: "rgba(255,255,255,0.06)" }}>
                    <div className="h-full transition-all" style={{ width: `${pct}%`, background: b.color }} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Recent attempts */}
        <div className="asc-card p-6 mt-6">
          <div className="asc-label mb-4">Recent Attempts</div>
          {stats.recent_attempts?.length === 0 ? (
            <div className="text-sm text-[var(--asc-text-muted)]">No practice attempts yet.</div>
          ) : (
            <div className="space-y-2">
              {stats.recent_attempts?.map((a) => (
                <div key={a.attempt_id} className="flex flex-wrap items-center justify-between gap-3 p-3 rounded-lg" style={{ background: "rgba(255,255,255,0.02)" }} data-testid={`attempt-${a.attempt_id}`}>
                  <div className="flex-1 min-w-0">
                    <div className="font-bold text-white text-sm">{a.challenge_title}</div>
                    <div className="text-xs text-[var(--asc-text-muted)]">{a.user_email} · {new Date(a.created_at).toLocaleString()}</div>
                  </div>
                  <div className="flex items-center gap-2">
                    {a.mastered && <Trophy size={12} color="#22c55e" />}
                    <span className="font-black text-lg" style={{ color: a.score >= 80 ? "#22c55e" : a.score >= 60 ? "#FFB000" : "#EF4444" }}>{a.score}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="mt-6 asc-card p-6">
          <div className="asc-label mb-2">Layer 2 &amp; 3 Coming Next</div>
          <p className="text-sm text-[var(--asc-text-dim)]">Module Capstones (mandatory for certificates) and Spaced Practice Drills are queued for the next build phase.</p>
        </div>
      </div>
    </div>
  );
}

function StatCard({ icon: Icon, label, value, sub, color }) {
  return (
    <div className="asc-card p-5">
      <div className="flex items-center gap-2 mb-2">
        <Icon size={16} color={color} />
        <div className="asc-label" style={{ color }}>{label}</div>
      </div>
      <div className="text-3xl font-black text-white">{value}</div>
      <div className="text-xs text-[var(--asc-text-muted)] mt-1">{sub}</div>
    </div>
  );
}
