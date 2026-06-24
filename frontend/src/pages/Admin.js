import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import Loader from "@/components/Loader";
import TierBadge from "@/components/TierBadge";
import { formatDate } from "@/lib/utils";
import { Users, DollarSign, Activity, TrendingUp, Search, Shield } from "lucide-react";
import { toast } from "sonner";

export default function Admin() {
  const [stats, setStats] = useState(null);
  const [users, setUsers] = useState([]);
  const [sales, setSales] = useState([]);
  const [traffic, setTraffic] = useState(null);
  const [tab, setTab] = useState("stats");
  const [q, setQ] = useState("");
  const [loading, setLoading] = useState(true);

  const loadAll = async () => {
    setLoading(true);
    try {
      const [s, u, sl, tr] = await Promise.all([
        api.get("/admin/stats"),
        api.get("/admin/users"),
        api.get("/admin/sales"),
        api.get("/admin/traffic"),
      ]);
      setStats(s); setUsers(u.users); setSales(sl.sales); setTraffic(tr);
    } catch (e) {
      toast.error(e.message || "Could not load admin data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadAll(); }, []);

  const searchUsers = async () => {
    try {
      const r = await api.get(`/admin/users${q ? `?q=${encodeURIComponent(q)}` : ""}`);
      setUsers(r.users);
    } catch (e) { toast.error(e.message); }
  };

  const patchUser = async (uid, patch) => {
    try {
      const r = await api.patch(`/admin/users/${uid}`, patch);
      setUsers((arr) => arr.map((u) => u.id === uid ? { ...u, ...r.user } : u));
      toast.success("User updated");
    } catch (e) { toast.error(e.message || "Update failed"); }
  };

  if (loading) return <Loader />;

  return (
    <div className="max-w-7xl mx-auto px-5 sm:px-8 py-10" data-testid="admin-page">
      <div className="flex items-center gap-2 mb-4"><Shield size={18} className="text-[var(--asc-coral)]" /><div className="asc-kicker">Admin</div></div>
      <h1 className="asc-h2 text-4xl">Operations console</h1>

      <div className="flex gap-2 mt-6">
        {["stats", "users", "sales", "traffic"].map((t) => (
          <button key={t} onClick={() => setTab(t)} data-testid={`admin-tab-${t}`} className="px-4 py-2 rounded-full text-sm font-bold transition"
            style={tab === t ? { background: "#FFB000", color: "#000" } : { background: "#1F183A", color: "#C8C5E6", border: "1px solid rgba(191,180,255,0.15)" }}>{t.toUpperCase()}</button>
        ))}
      </div>

      {tab === "stats" && stats && (
        <div className="mt-6 space-y-6">
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <StatBox icon={Users} label="Total users" value={stats.users.total} sub={`${stats.users.signups_30d} in 30d`} color="#FFB000" />
            <StatBox icon={DollarSign} label="Revenue MTD" value={`$${stats.revenue.mtd_usd}`} sub={`$${stats.revenue.total_usd} all-time`} color="#34D399" />
            <StatBox icon={Activity} label="DAU" value={stats.engagement.dau} sub={`WAU ${stats.engagement.wau}`} color="#7C3AED" />
            <StatBox icon={TrendingUp} label="Conversion" value={`${stats.users.conversion_pct}%`} sub={`${stats.users.paid} paid`} color="#FF6B35" />
          </div>

          <div className="grid md:grid-cols-2 gap-4">
            <div className="asc-card p-6">
              <div className="asc-label mb-3">Users by tier</div>
              {Object.entries(stats.users.by_tier).map(([k, v]) => (
                <div key={k} className="flex items-center justify-between py-2 border-b border-[var(--asc-border)] last:border-0">
                  <TierBadge tier={k} />
                  <span className="font-bold">{v}</span>
                </div>
              ))}
            </div>
            <div className="asc-card p-6">
              <div className="asc-label mb-3">Engagement</div>
              <Row label="Lessons completed" value={stats.engagement.lessons_completed} />
              <Row label="Certificates issued" value={stats.engagement.certificates_issued} />
              <Row label="Pageviews 24h" value={stats.traffic.pageviews_24h} />
              <Row label="Unique visitors 7d" value={stats.traffic.unique_visitors_7d} />
            </div>
          </div>
        </div>
      )}

      {tab === "users" && (
        <div className="mt-6">
          <div className="flex gap-2 mb-4">
            <input className="asc-input flex-1 max-w-md" placeholder="Search by email or name…" value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => e.key === "Enter" && searchUsers()} data-testid="admin-user-search" />
            <button onClick={searchUsers} className="asc-btn-secondary"><Search size={14} /></button>
          </div>
          <div className="asc-card overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr style={{ background: "#1F183A" }} className="text-left text-[var(--asc-text-dim)] text-xs uppercase tracking-wider">
                  <th className="p-3">User</th>
                  <th className="p-3">Tier</th>
                  <th className="p-3">XP</th>
                  <th className="p-3">Joined</th>
                  <th className="p-3">Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id} className="border-t border-[var(--asc-border)]">
                    <td className="p-3">
                      <div className="font-bold">{u.name || u.email.split("@")[0]}</div>
                      <div className="text-xs text-[var(--asc-text-muted)]">{u.email}</div>
                    </td>
                    <td className="p-3"><TierBadge tier={u.tier} /></td>
                    <td className="p-3 asc-mono">{u.total_xp}</td>
                    <td className="p-3 text-xs text-[var(--asc-text-dim)]">{formatDate(u.created_at)}</td>
                    <td className="p-3">
                      <select defaultValue={u.tier} onChange={(e) => patchUser(u.id, { tier: e.target.value })} className="px-2 py-1 rounded-lg text-xs" style={{ background: "#15102B", border: "1px solid rgba(191,180,255,0.15)" }} data-testid={`admin-tier-select-${u.id}`}>
                        {["free", "ascender", "pathfinder", "sage"].map((t) => <option key={t} value={t}>{t}</option>)}
                      </select>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {tab === "sales" && (
        <div className="asc-card mt-6 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr style={{ background: "#1F183A" }} className="text-left text-[var(--asc-text-dim)] text-xs uppercase tracking-wider">
                <th className="p-3">User</th>
                <th className="p-3">Tier</th>
                <th className="p-3">Interval</th>
                <th className="p-3">Amount</th>
                <th className="p-3">Paid at</th>
              </tr>
            </thead>
            <tbody>
              {sales.length === 0 && <tr><td colSpan="5" className="p-6 text-center text-[var(--asc-text-muted)]">No sales yet.</td></tr>}
              {sales.map((s) => (
                <tr key={s.session_id} className="border-t border-[var(--asc-border)]">
                  <td className="p-3">{s.user_name || s.user_email}</td>
                  <td className="p-3"><TierBadge tier={s.tier} /></td>
                  <td className="p-3 text-xs uppercase">{s.interval}</td>
                  <td className="p-3 font-bold text-[var(--asc-success)]">${s.amount_usd?.toFixed(2)}</td>
                  <td className="p-3 text-xs text-[var(--asc-text-dim)]">{formatDate(s.paid_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === "traffic" && traffic && (
        <div className="mt-6 grid md:grid-cols-2 gap-4">
          <div className="asc-card p-6">
            <div className="asc-label mb-3">Daily pageviews ({traffic.days}d)</div>
            <div className="flex items-end gap-1 h-32">
              {traffic.daily.map((d) => {
                const max = Math.max(...traffic.daily.map((x) => x.views), 1);
                return <div key={d.date} title={`${d.date}: ${d.views} views`} className="flex-1 rounded-t" style={{ height: `${(d.views / max) * 100}%`, background: "linear-gradient(to top, #7C3AED, #FFB000)", minHeight: 2 }} />;
              })}
            </div>
            {traffic.daily.length === 0 && <div className="text-center text-[var(--asc-text-muted)] text-sm py-6">No pageviews yet.</div>}
          </div>
          <div className="asc-card p-6">
            <div className="asc-label mb-3">Top paths</div>
            {traffic.top_paths.length === 0 ? (
              <div className="text-[var(--asc-text-muted)] text-sm">No data yet.</div>
            ) : (
              <ul className="space-y-1">
                {traffic.top_paths.map((tp) => (
                  <li key={tp.path} className="flex justify-between py-1 text-sm border-b border-[var(--asc-border)] last:border-0">
                    <span className="text-[var(--asc-text-dim)] truncate">{tp.path}</span>
                    <span className="font-bold">{tp.views}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function StatBox({ icon: Icon, label, value, sub, color }) {
  return (
    <div className="asc-card p-5">
      <div className="flex items-start gap-3">
        <div className="w-10 h-10 rounded-xl grid place-items-center" style={{ background: `${color}22`, border: `1px solid ${color}55` }}><Icon size={18} color={color} /></div>
        <div className="flex-1">
          <div className="asc-label">{label}</div>
          <div className="asc-h2 text-2xl mt-1">{value}</div>
          <div className="text-xs text-[var(--asc-text-muted)] mt-0.5">{sub}</div>
        </div>
      </div>
    </div>
  );
}

function Row({ label, value }) {
  return <div className="flex justify-between py-2 border-b border-[var(--asc-border)] last:border-0"><span className="text-[var(--asc-text-dim)]">{label}</span><span className="font-bold">{value}</span></div>;
}
