import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import Loader from "@/components/Loader";
import { ArrowLeft, Shield, ClipboardList, ScrollText, Users, Zap, AlertTriangle, CheckCircle2, XCircle, Download, RefreshCcw, DollarSign } from "lucide-react";
import { toast } from "sonner";

const TABS = [
  { id: "overview", label: "Overview", icon: Shield },
  { id: "approvals", label: "Approval Queue", icon: ClipboardList },
  { id: "audit", label: "Audit Log", icon: ScrollText },
  { id: "budget", label: "Operating Budget", icon: DollarSign },
  { id: "integrations", label: "Integrations", icon: Zap },
];

export default function AdminRevenue() {
  const nav = useNavigate();
  const [tab, setTab] = useState("overview");
  const [loading, setLoading] = useState(true);
  const [state, setState] = useState(null);
  const [summary, setSummary] = useState(null);
  const [approvals, setApprovals] = useState([]);
  const [audit, setAudit] = useState([]);
  const [integrations, setIntegrations] = useState([]);
  const [budget, setBudget] = useState(null);
  const [busy, setBusy] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const [s, sm, ap, au, itg, bg] = await Promise.all([
        api.get("/admin/revenue/system/state"),
        api.get("/admin/revenue/summary"),
        api.get("/admin/revenue/approvals?limit=100").catch(() => ({ approvals: [] })),
        api.get("/admin/revenue/audit?limit=100").catch(() => ({ entries: [] })),
        api.get("/admin/revenue/integrations").catch(() => ({ integrations: [] })),
        api.get("/admin/revenue/budget").catch(() => null),
      ]);
      setState(s); setSummary(sm);
      setApprovals(ap.approvals || []);
      setAudit(au.entries || []);
      setIntegrations(itg.integrations || []);
      setBudget(bg);
    } catch (e) { toast.error(e.message || "Load failed"); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  const decide = async (id, decision) => {
    setBusy(true);
    try {
      await api.post(`/admin/revenue/approvals/${id}/decision`, { decision });
      toast.success(`Approval ${decision}`);
      load();
    } catch (e) { toast.error(e.message); }
    finally { setBusy(false); }
  };

  const exportAudit = async () => {
    try {
      const r = await api.get("/admin/revenue/audit/export?limit=1000");
      const blob = new Blob([JSON.stringify(r, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = `ascendra-audit-${new Date().toISOString()}.json`;
      a.click(); URL.revokeObjectURL(url);
    } catch (e) { toast.error(e.message); }
  };

  const setNewBudget = async () => {
    const v = prompt("Approved monthly operating budget (USD, decimal, e.g. 8500.00):");
    if (!v) return;
    const notes = prompt("Notes / justification for this budget:") || "";
    try {
      await api.post("/admin/revenue/budget", { monthly_budget_usd: v, effective_date: new Date().toISOString(), notes });
      toast.success("Budget recorded (audit entry created)");
      load();
    } catch (e) { toast.error(e.message); }
  };

  if (loading) return <div className="max-w-7xl mx-auto px-5 py-10"><Loader /></div>;

  const live = state?.live_actions_enabled;

  return (
    <div className="max-w-7xl mx-auto px-5 sm:px-8 py-10" data-testid="admin-revenue-page">
      <button onClick={() => nav("/admin")} className="flex items-center gap-1 text-sm text-[var(--asc-text-dim)] hover:text-white mb-3"><ArrowLeft size={14} /> Admin</button>
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="asc-kicker">Phase 1 · Revenue Control Center</div>
          <h1 className="asc-h2 text-4xl mt-1 flex items-center gap-3"><Shield size={28} className="text-[var(--asc-brand)]" /> Revenue Control Center</h1>
          <p className="text-[var(--asc-text-dim)] text-sm mt-2 max-w-3xl">Contacts, events, approvals, and audit log. All external actions remain <strong>simulated or gated</strong> while <code className="asc-mono text-[var(--asc-brand)]">AUTOMATION_LIVE_ACTIONS_ENABLED=false</code>. Phase 3 will wire the financial ledger.</p>
        </div>
        <button onClick={load} className="asc-btn-secondary text-sm" data-testid="revenue-refresh"><RefreshCcw size={13} /> Refresh</button>
      </div>

      {/* Safety banner */}
      <div className="asc-card p-4 mt-6 flex items-start gap-3" style={{ background: live ? "rgba(251,113,133,0.08)" : "rgba(74,222,128,0.06)", borderColor: live ? "rgba(251,113,133,0.35)" : "rgba(74,222,128,0.30)" }} data-testid="revenue-safety-banner">
        {live ? <AlertTriangle size={18} className="text-[#FB7185] mt-0.5 shrink-0" /> : <CheckCircle2 size={18} className="text-[#4ADE80] mt-0.5 shrink-0" />}
        <div className="text-sm text-[var(--asc-text-dim)]">
          <strong className="text-white">Live actions are {live ? "ENABLED" : "DISABLED"}.</strong> {live ? "External integrations will execute real actions. Approvals still gate irreversible operations." : "All external side effects are simulated. Actions requiring authorization queue in the Approval Queue."} Toggle via <code className="asc-mono">AUTOMATION_LIVE_ACTIONS_ENABLED</code> in backend .env, then restart backend.
        </div>
      </div>

      {/* Tabs */}
      <div className="flex flex-wrap gap-2 mt-6" data-testid="revenue-tabs">
        {TABS.map((t) => (
          <button key={t.id} onClick={() => setTab(t.id)} className={`asc-btn-secondary text-xs ${tab === t.id ? "!bg-[var(--asc-brand)] !text-black" : ""}`} data-testid={`revenue-tab-${t.id}`}>
            <t.icon size={13} /> {t.label}
          </button>
        ))}
      </div>

      {/* Overview */}
      {tab === "overview" && summary && (
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-3 mt-5" data-testid="revenue-overview">
          <Stat label="Contacts" value={summary.counts.contacts} sub={`${summary.counts.contacts_simulated} simulated`} />
          <Stat label="Events" value={summary.counts.events} sub={`${summary.counts.events_pending} pending`} />
          <Stat label="Pending Approvals" value={summary.counts.approvals_pending} sub={`${summary.counts.approvals_approved} approved`} tone={summary.counts.approvals_pending > 0 ? "warn" : "ok"} />
          <Stat label="Audit Entries" value={summary.counts.audit_entries} sub="append-only" />
          <div className="asc-card p-5 md:col-span-2 lg:col-span-4">
            <div className="asc-kicker mb-2">Phase 1 scope</div>
            <p className="text-sm text-[var(--asc-text-dim)] leading-relaxed">This is the foundation layer. Contacts, internal events, approval queue, audit log, integration status, and operating-budget history are wired. <strong className="text-white">No revenue data is shown yet</strong> — Phase 3 builds the financial ledger, allocation policy, and owner-draw reconciliation. Any records tagged <code className="asc-mono text-[var(--asc-brand)]">simulated=true</code> are for testing only and must not be interpreted as real revenue.</p>
          </div>
        </div>
      )}

      {/* Approvals */}
      {tab === "approvals" && (
        <div className="asc-card p-4 mt-5" data-testid="revenue-approvals">
          <div className="asc-kicker mb-3">Approval Queue · {approvals.length} entries</div>
          {approvals.length === 0 ? <div className="text-sm text-[var(--asc-text-muted)] py-6 text-center">No pending or historical approvals yet.</div> : (
            <div className="space-y-2">
              {approvals.map((a) => (
                <div key={a.id} className="p-3 rounded-lg border border-[var(--asc-border)] flex flex-wrap items-center gap-3" data-testid={`approval-${a.id}`}>
                  <div className="flex-1 min-w-[240px]">
                    <div className="text-sm font-bold">{a.requested_action}</div>
                    <div className="text-[10px] text-[var(--asc-text-muted)] uppercase tracking-wider">
                      {a.request_type} · risk={a.risk_level} · {a.simulated ? "SIMULATED" : "LIVE"}
                    </div>
                    <div className="text-xs text-[var(--asc-text-dim)] mt-1">{a.reason}</div>
                    {a.financial_amount_usd != null && <div className="text-xs text-[var(--asc-brand)] asc-mono">${a.financial_amount_usd.toFixed(2)}</div>}
                  </div>
                  <StatusPill status={a.status} />
                  {a.status === "pending" && (
                    <div className="flex gap-1">
                      <button onClick={() => decide(a.id, "approved")} disabled={busy} className="asc-btn-primary text-xs" data-testid={`approve-${a.id}`}>Approve</button>
                      <button onClick={() => decide(a.id, "rejected")} disabled={busy} className="asc-btn-secondary text-xs" data-testid={`reject-${a.id}`}>Reject</button>
                    </div>
                  )}
                  {a.status === "approved" && (
                    <button onClick={() => decide(a.id, "completed")} disabled={busy} className="asc-btn-secondary text-xs" data-testid={`complete-${a.id}`}>Mark Completed</button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Audit Log */}
      {tab === "audit" && (
        <div className="asc-card p-4 mt-5" data-testid="revenue-audit">
          <div className="flex items-center justify-between mb-3">
            <div className="asc-kicker">Audit Log · {audit.length} entries (append-only)</div>
            <button onClick={exportAudit} className="asc-btn-secondary text-xs" data-testid="audit-export"><Download size={12} /> Export JSON</button>
          </div>
          {audit.length === 0 ? <div className="text-sm text-[var(--asc-text-muted)] py-6 text-center">Audit log is empty.</div> : (
            <div className="space-y-1 max-h-[600px] overflow-y-auto">
              {audit.map((e) => (
                <div key={e.id} className="text-xs asc-mono p-2 rounded border border-[var(--asc-border)] flex flex-wrap gap-2 items-center" data-testid={`audit-entry-${e.id}`}>
                  <span className="text-[var(--asc-text-muted)]">{new Date(e.created_at).toLocaleString()}</span>
                  <span className="text-[var(--asc-brand)] font-bold">{e.action}</span>
                  <span className="text-[var(--asc-text-dim)]">{e.actor}</span>
                  <span className="text-[var(--asc-text-muted)]">→ {e.target_type}/{e.target_id?.slice(0, 8)}</span>
                  {e.simulated && <span className="text-[9px] px-1.5 py-0.5 rounded font-bold" style={{ background: "rgba(255,176,0,0.15)", color: "#FFB000" }}>SIM</span>}
                  {e.approval_required && <span className="text-[9px] px-1.5 py-0.5 rounded font-bold" style={{ background: "rgba(124,58,237,0.18)", color: "#BFB4FF" }}>APPROVAL</span>}
                  {e.reason && <span className="text-[var(--asc-text-dim)] font-sans normal-case">— {e.reason}</span>}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Budget */}
      {tab === "budget" && (
        <div className="asc-card p-4 mt-5" data-testid="revenue-budget">
          <div className="flex items-center justify-between mb-3">
            <div className="asc-kicker">Approved Monthly Operating Budget · versioned history</div>
            <button onClick={setNewBudget} className="asc-btn-primary text-xs" data-testid="budget-new"><DollarSign size={12} /> Set new value</button>
          </div>
          <p className="text-xs text-[var(--asc-text-dim)] mb-3">Placeholder for Phase 3 reserve-target calculation. Prior values are preserved and never overwritten. Each change writes an audit entry.</p>
          {budget?.current ? (
            <div className="rounded-lg p-4 mb-3" style={{ background: "rgba(255,176,0,0.06)", border: "1px solid rgba(255,176,0,0.25)" }} data-testid="budget-current">
              <div className="text-[10px] uppercase tracking-wider text-[var(--asc-brand)]">Current</div>
              <div className="text-3xl font-black asc-mono mt-1">${budget.current.monthly_budget_usd}</div>
              <div className="text-xs text-[var(--asc-text-muted)] mt-1">Effective: {new Date(budget.current.effective_date).toLocaleDateString()} · Set by {budget.current.updated_by}</div>
              {budget.current.notes && <div className="text-xs text-[var(--asc-text-dim)] mt-2 italic">&ldquo;{budget.current.notes}&rdquo;</div>}
            </div>
          ) : (
            <div className="text-sm text-[var(--asc-text-muted)] py-6 text-center">No budget set yet. Click &ldquo;Set new value&rdquo; to record the first approved monthly operating budget.</div>
          )}
          {budget?.history?.length > 1 && (
            <div>
              <div className="asc-kicker mb-2">History ({budget.history.length} entries)</div>
              <div className="space-y-1">
                {budget.history.slice(1).map((h) => (
                  <div key={h.id} className="text-xs asc-mono p-2 rounded border border-[var(--asc-border)] flex flex-wrap gap-2" data-testid={`budget-history-${h.id}`}>
                    <span className="text-[var(--asc-text-muted)]">{new Date(h.effective_date).toLocaleDateString()}</span>
                    <span className="text-[var(--asc-brand)] font-bold">${h.monthly_budget_usd}</span>
                    <span className="text-[var(--asc-text-dim)]">by {h.updated_by}</span>
                    {h.notes && <span className="text-[var(--asc-text-muted)] font-sans normal-case">— {h.notes}</span>}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Integrations */}
      {tab === "integrations" && (
        <div className="asc-card p-4 mt-5" data-testid="revenue-integrations">
          <div className="asc-kicker mb-3">Integration Status · env-driven, no live calls made</div>
          <div className="grid md:grid-cols-2 gap-2">
            {integrations.map((i) => (
              <div key={i.provider} className="p-3 rounded-lg border border-[var(--asc-border)] flex items-center gap-3" data-testid={`integration-${i.provider}`}>
                <div className="flex-1">
                  <div className="text-sm font-bold uppercase">{i.provider}</div>
                  <div className="text-[10px] text-[var(--asc-text-muted)] asc-mono">{i.env_keys_expected.join(", ")}</div>
                </div>
                <span className="text-[9px] px-1.5 py-0.5 rounded font-bold uppercase tracking-wider" style={{
                  background: i.state === "live" ? "rgba(74,222,128,0.18)" : i.state === "simulated" ? "rgba(255,176,0,0.18)" : "rgba(138,131,184,0.15)",
                  color: i.state === "live" ? "#4ADE80" : i.state === "simulated" ? "#FFB000" : "#8A83B8",
                }}>{i.state}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function Stat({ label, value, sub, tone = "ok" }) {
  const color = tone === "warn" ? "#FFB000" : "#4ADE80";
  return (
    <div className="asc-card p-4" data-testid={`stat-${label.toLowerCase().replace(/[^a-z]/g, "-")}`}>
      <div className="text-[10px] uppercase tracking-wider text-[var(--asc-text-muted)]">{label}</div>
      <div className="text-3xl font-black asc-mono mt-1" style={{ color }}>{value}</div>
      {sub && <div className="text-[10px] text-[var(--asc-text-dim)] mt-1">{sub}</div>}
    </div>
  );
}

function StatusPill({ status }) {
  const map = {
    pending:   { bg: "rgba(255,176,0,0.18)",  fg: "#FFB000" },
    approved:  { bg: "rgba(74,222,128,0.18)", fg: "#4ADE80" },
    rejected:  { bg: "rgba(251,113,133,0.18)",fg: "#FB7185" },
    completed: { bg: "rgba(124,58,237,0.18)", fg: "#BFB4FF" },
    cancelled: { bg: "rgba(138,131,184,0.15)",fg: "#8A83B8" },
    expired:   { bg: "rgba(138,131,184,0.15)",fg: "#8A83B8" },
  };
  const c = map[status] || map.cancelled;
  return <span className="text-[9px] px-2 py-0.5 rounded-full font-bold uppercase tracking-wider" style={{ background: c.bg, color: c.fg }}>{status}</span>;
}
