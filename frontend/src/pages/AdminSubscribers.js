import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import Loader from "@/components/Loader";
import TierBadge from "@/components/TierBadge";
import { ArrowLeft, Users, DollarSign, RefreshCw, AlertCircle, BellRing, Download } from "lucide-react";
import { toast } from "sonner";
import { formatDate } from "@/lib/utils";

export default function AdminSubscribers() {
  const nav = useNavigate();
  const [data, setData] = useState({ subscribers: [], count: 0, by_tier: {}, mrr_usd: 0, arr_usd: 0 });
  const [loading, setLoading] = useState(true);
  const [includeCanceled, setIncludeCanceled] = useState(false);
  const [sendingFor, setSendingFor] = useState(null);

  const load = async () => {
    setLoading(true);
    try {
      const r = await api.get(`/admin/subscribers?include_canceled=${includeCanceled}`);
      setData(r);
    } catch (e) {
      toast.error(e.message || "Could not load subscribers");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); /* eslint-disable-next-line */ }, [includeCanceled]);

  const sendRenewalReminder = async (uid, email) => {
    setSendingFor(uid);
    try {
      const r = await api.post("/admin/billing/renewal-reminders/send", { user_id: uid, force: true });
      if (r.skipped) {
        toast.success(`Already sent recently to ${email}`);
      } else {
        toast.success(`Renewal reminder sent to ${email}`);
      }
    } catch (e) {
      toast.error(e.message || "Send failed");
    } finally {
      setSendingFor(null);
    }
  };

  const exportCsv = () => {
    const rows = data.subscribers || [];
    if (!rows.length) { toast.error("Nothing to export"); return; }
    const headers = ["email", "name", "tier", "interval", "status", "renews_at", "cancel_at_period_end", "stripe_customer_id", "created_at"];
    const csv = [headers.join(",")].concat(
      rows.map((r) => headers.map((h) => {
        const v = r[h];
        if (v == null) return "";
        const s = typeof v === "string" ? v : String(v);
        return s.includes(",") || s.includes("\"") ? `"${s.replace(/"/g, '""')}"` : s;
      }).join(","))
    ).join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = `ascendra-subscribers-${new Date().toISOString().slice(0, 10)}.csv`;
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
    URL.revokeObjectURL(url);
    toast.success(`Exported ${rows.length} subscribers`);
  };

  return (
    <div className="max-w-7xl mx-auto px-5 sm:px-8 py-10" data-testid="admin-subscribers-page">
      <button onClick={() => nav("/admin")} className="flex items-center gap-1 text-sm text-[var(--asc-text-dim)] hover:text-white mb-3" data-testid="subscribers-back-btn"><ArrowLeft size={14} /> Admin</button>
      <div className="asc-kicker">Billing</div>
      <h1 className="asc-h2 text-4xl mt-1 flex items-center gap-3"><Users size={28} className="text-[var(--asc-brand)]" /> Subscribers</h1>
      <p className="text-[var(--asc-text-dim)] text-sm mt-2">Everyone with a paid plan, with current status from Stripe webhooks.</p>

      {/* Summary */}
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 mt-6">
        <SumCard icon={Users} label="Total subscribers" value={data.count} hint={`${data.by_tier?.ascender || 0} A · ${data.by_tier?.pathfinder || 0} P · ${data.by_tier?.sage || 0} S`} color="#FFB000" />
        <SumCard icon={DollarSign} label="MRR (est.)" value={`$${data.mrr_usd?.toFixed(2)}`} hint="Annual plans normalized to monthly" color="#34D399" />
        <SumCard icon={DollarSign} label="ARR (est.)" value={`$${data.arr_usd?.toFixed(2)}`} hint="MRR × 12" color="#7C3AED" />
        <div className="asc-card p-5 flex flex-col gap-3">
          <div className="asc-label">Filters</div>
          <label className="flex items-center gap-2 text-sm" data-testid="subscribers-include-canceled">
            <input type="checkbox" checked={includeCanceled} onChange={(e) => setIncludeCanceled(e.target.checked)} />
            <span>Include canceled / past_due</span>
          </label>
          <div className="flex gap-2">
            <button onClick={load} className="asc-btn-secondary text-xs flex-1" data-testid="subscribers-refresh-btn"><RefreshCw size={12} /> Refresh</button>
            <button onClick={exportCsv} className="asc-btn-secondary text-xs flex-1" data-testid="subscribers-export-btn"><Download size={12} /> CSV</button>
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="asc-card mt-6 overflow-hidden">
        {loading ? (
          <div className="p-10"><Loader /></div>
        ) : data.subscribers.length === 0 ? (
          <div className="p-10 text-center" data-testid="subscribers-empty">
            <div className="w-12 h-12 mx-auto rounded-2xl grid place-items-center mb-3" style={{ background: "rgba(255,176,0,0.10)" }}><AlertCircle size={20} color="#FFB000" /></div>
            <div className="asc-h2 text-lg">No paid subscribers yet</div>
            <p className="text-[var(--asc-text-dim)] text-sm mt-2">Once someone pays through Stripe checkout they’ll appear here.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm" data-testid="subscribers-table">
              <thead>
                <tr style={{ background: "#1F183A" }} className="text-left text-[var(--asc-text-dim)] text-xs uppercase tracking-wider">
                  <th className="p-3">User</th>
                  <th className="p-3">Plan</th>
                  <th className="p-3">Interval</th>
                  <th className="p-3">Status</th>
                  <th className="p-3">Renews / expires</th>
                  <th className="p-3">Joined</th>
                  <th className="p-3">Actions</th>
                </tr>
              </thead>
              <tbody>
                {data.subscribers.map((s) => (
                  <tr key={s.user_id} className="border-t border-[var(--asc-border)]" data-testid={`subscriber-row-${s.user_id}`}>
                    <td className="p-3">
                      <div className="font-bold">{s.name || s.email.split("@")[0]}</div>
                      <div className="text-xs text-[var(--asc-text-muted)]">{s.email}</div>
                    </td>
                    <td className="p-3"><TierBadge tier={s.tier} /></td>
                    <td className="p-3 text-xs uppercase">{s.interval || "—"}</td>
                    <td className="p-3">
                      <StatusBadge status={s.status} cancelAtPeriodEnd={s.cancel_at_period_end} />
                    </td>
                    <td className="p-3 text-xs text-[var(--asc-text-dim)]">{formatDate(s.renews_at) || "—"}</td>
                    <td className="p-3 text-xs text-[var(--asc-text-dim)]">{formatDate(s.created_at)}</td>
                    <td className="p-3">
                      <button
                        onClick={() => sendRenewalReminder(s.user_id, s.email)}
                        disabled={sendingFor === s.user_id}
                        className="asc-btn-secondary text-xs"
                        data-testid={`subscriber-send-renewal-${s.user_id}`}
                        title="Send a renewal reminder email now (idempotency bypassed)"
                      >
                        <BellRing size={12} /> {sendingFor === s.user_id ? "Sending…" : "Renewal email"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

function SumCard({ icon: Icon, label, value, hint, color }) {
  return (
    <div className="asc-card p-5">
      <div className="flex items-start gap-3">
        <div className="w-10 h-10 rounded-xl grid place-items-center" style={{ background: `${color}22`, border: `1px solid ${color}55` }}><Icon size={18} color={color} /></div>
        <div className="flex-1">
          <div className="asc-label">{label}</div>
          <div className="asc-h2 text-2xl mt-1" data-testid={`subscribers-summary-${label.toLowerCase().replace(/\s/g, '-')}`}>{value}</div>
          <div className="text-xs text-[var(--asc-text-muted)] mt-0.5">{hint}</div>
        </div>
      </div>
    </div>
  );
}

function StatusBadge({ status, cancelAtPeriodEnd }) {
  const palette = {
    active: { bg: "rgba(52,211,153,0.15)", color: "#34D399", label: cancelAtPeriodEnd ? "ACTIVE · CANCELS" : "ACTIVE" },
    trialing: { bg: "rgba(255,176,0,0.15)", color: "#FFB000", label: "TRIAL" },
    past_due: { bg: "rgba(255,107,53,0.15)", color: "#FF6B35", label: "PAST DUE" },
    canceled: { bg: "rgba(255,255,255,0.05)", color: "#C8C5E6", label: "CANCELED" },
    unknown: { bg: "rgba(124,58,237,0.15)", color: "#BFB4FF", label: "UNKNOWN" },
  };
  const p = palette[status] || palette.unknown;
  return (
    <span className="px-2 py-0.5 rounded-full text-[10px] font-black tracking-wider" style={{ background: p.bg, color: p.color }}>
      {p.label}
    </span>
  );
}
