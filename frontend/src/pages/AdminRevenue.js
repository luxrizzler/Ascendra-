import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import Loader from "@/components/Loader";
import {
  ArrowLeft, Shield, ClipboardList, ScrollText, Users, Zap,
  AlertTriangle, CheckCircle2, Download, RefreshCcw, DollarSign,
  Package, Target, GitBranch, Plus, ChevronRight,
  Receipt, Wallet, TrendingUp, Calendar, PiggyBank,
  Workflow, ListTree, FileText, BookOpen, Scale, Webhook,
} from "lucide-react";
import { toast } from "sonner";

const TABS = [
  { id: "overview", label: "Overview", icon: Shield },
  { id: "approvals", label: "Approval Queue", icon: ClipboardList },
  { id: "audit", label: "Audit Log", icon: ScrollText },
  { id: "budget", label: "Operating Budget", icon: DollarSign },
  { id: "integrations", label: "Integrations", icon: Zap },
  // ── Phase 2 tabs ──
  { id: "contacts", label: "Contacts", icon: Users },
  { id: "offers", label: "Offers", icon: Package },
  { id: "scoring", label: "Scoring Rules", icon: Target },
  { id: "attribution", label: "Attribution", icon: GitBranch },
  // ── Phase 3 tabs ──
  { id: "ledger", label: "Financial Ledger", icon: Receipt },
  { id: "expenses", label: "Essential Expenses", icon: Wallet },
  { id: "reserve", label: "Reserve Target", icon: PiggyBank },
  { id: "allocation", label: "Allocation Policy", icon: TrendingUp },
  { id: "recon", label: "Monthly Reconciliation", icon: Calendar },
  { id: "draws", label: "Owner Draws", icon: DollarSign },
  // ── Phase 4 tabs ──
  { id: "workflows", label: "Workflows", icon: Workflow },
  { id: "actions", label: "Action Queue", icon: ListTree },
  { id: "templates", label: "Templates", icon: FileText },
  { id: "knowledge", label: "Knowledge Base", icon: BookOpen },
  { id: "authority", label: "Authority Matrix", icon: Scale },
  { id: "webhooks", label: "Webhook Events", icon: Webhook },
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
  // Phase 2 state
  const [contacts, setContacts] = useState([]);
  const [offers, setOffers] = useState([]);
  const [scoringRules, setScoringRules] = useState({ rule_sets: [], current: null });
  const [selectedContact, setSelectedContact] = useState(null);
  // Phase 3 state
  const [ledger, setLedger] = useState([]);
  const [expenses, setExpenses] = useState([]);
  const [reserve, setReserve] = useState(null);
  const [allocPolicies, setAllocPolicies] = useState({ policies: [], current_phase: "startup" });
  const [taxPolicies, setTaxPolicies] = useState([]);
  const [recons, setRecons] = useState([]);
  const [draws, setDraws] = useState([]);
  const [p3summary, setP3summary] = useState(null);
  // Phase 4 state
  const [workflows, setWorkflows] = useState([]);
  const [actions, setActions] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [knowledge, setKnowledge] = useState([]);
  const [authority, setAuthority] = useState(null);
  const [webhooks, setWebhooks] = useState([]);

  const load = async () => {
    setLoading(true);
    try {
      const [s, sm, ap, au, itg, bg, cts, ofs, srs, scur,
              lg, ex, rs, alp, txp, rc, dr, p3s,
              wf, ac, tp, kb, am, wh] = await Promise.all([
        api.get("/admin/revenue/system/state"),
        api.get("/admin/revenue/summary"),
        api.get("/admin/revenue/approvals?limit=100").catch(() => ({ approvals: [] })),
        api.get("/admin/revenue/audit?limit=100").catch(() => ({ entries: [] })),
        api.get("/admin/revenue/integrations").catch(() => ({ integrations: [] })),
        api.get("/admin/revenue/budget").catch(() => null),
        api.get("/admin/revenue/contacts?limit=200").catch(() => ({ contacts: [] })),
        api.get("/admin/revenue/offers").catch(() => ({ offers: [] })),
        api.get("/admin/revenue/scoring/rules").catch(() => ({ rule_sets: [] })),
        api.get("/admin/revenue/scoring/rules/current").catch(() => ({ rule_set: null })),
        // Phase 3
        api.get("/admin/revenue/ledger/entries?limit=100").catch(() => ({ entries: [] })),
        api.get("/admin/revenue/expenses").catch(() => ({ expenses: [] })),
        api.get("/admin/revenue/reserve/target").catch(() => null),
        api.get("/admin/revenue/allocation-policies").catch(() => ({ policies: [], current_phase: "startup" })),
        api.get("/admin/revenue/tax-policies").catch(() => ({ policies: [] })),
        api.get("/admin/revenue/reconciliations").catch(() => ({ reconciliations: [] })),
        api.get("/admin/revenue/owner-draws").catch(() => ({ owner_draws: [] })),
        api.get("/admin/revenue/phase3/summary").catch(() => null),
        // Phase 4
        api.get("/admin/revenue/workflows").catch(() => ({ workflows: [] })),
        api.get("/admin/revenue/actions").catch(() => ({ actions: [] })),
        api.get("/admin/revenue/templates").catch(() => ({ templates: [] })),
        api.get("/admin/revenue/knowledge").catch(() => ({ knowledge: [] })),
        api.get("/admin/revenue/authority/matrix").catch(() => null),
        api.get("/admin/revenue/webhooks").catch(() => ({ events: [] })),
      ]);
      setState(s); setSummary(sm);
      setApprovals(ap.approvals || []);
      setAudit(au.entries || []);
      setIntegrations(itg.integrations || []);
      setBudget(bg);
      setContacts(cts.contacts || []);
      setOffers(ofs.offers || []);
      setScoringRules({ rule_sets: srs.rule_sets || [], current: scur.rule_set || null });
      setLedger(lg.entries || []);
      setExpenses(ex.expenses || []);
      setReserve(rs);
      setAllocPolicies({ policies: alp.policies || [], current_phase: alp.current_phase || "startup" });
      setTaxPolicies(txp.policies || []);
      setRecons(rc.reconciliations || []);
      setDraws(dr.owner_draws || []);
      setP3summary(p3s);
      setWorkflows(wf.workflows || []);
      setActions(ac.actions || []);
      setTemplates(tp.templates || []);
      setKnowledge(kb.knowledge || []);
      setAuthority(am);
      setWebhooks(wh.events || []);
    } catch (e) { toast.error(e.message || "Load failed"); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, []);

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

  const importExistingOffers = async () => {
    if (!window.confirm("Import Ascendra's four existing tiers into the offer catalog?\n\nSafe: only imports offers that don't already exist. No Stripe products or prices will be created.")) return;
    setBusy(true);
    try {
      const r = await api.post("/admin/revenue/offers/import-existing", {});
      toast.success(`Imported ${r.imported.length} offers (${r.skipped.length} already present)`);
      load();
    } catch (e) { toast.error(e.message); }
    finally { setBusy(false); }
  };

  const activateOffer = async (id) => {
    setBusy(true);
    try { await api.post(`/admin/revenue/offers/${id}/activate`, {}); toast.success("Offer activated"); load(); }
    catch (e) { toast.error(e.message); }
    finally { setBusy(false); }
  };
  const deactivateOffer = async (id) => {
    setBusy(true);
    try { await api.post(`/admin/revenue/offers/${id}/deactivate`, {}); toast.success("Offer deactivated"); load(); }
    catch (e) { toast.error(e.message); }
    finally { setBusy(false); }
  };

  const openContact = async (id) => {
    setBusy(true);
    try {
      const r = await api.get(`/admin/revenue/contacts/${id}`);
      setSelectedContact(r);
    } catch (e) { toast.error(e.message); }
    finally { setBusy(false); }
  };

  const recalcScore = async (contactId) => {
    // Minimal deterministic inputs derived from the current contact record.
    const c = selectedContact?.contact;
    if (!c) return;
    const inputs = {
      assessment_score: 0,
      business_type: c.business_type || "other",
      organization_size: c.organization_size || "solo",
      employee_count: c.employee_count || 0,
      urgency: "explore",
      engagement_recent_events: (selectedContact.internal_events || []).length,
      checkout_started: false,
      existing_customer: c.customer_status === "customer",
      source_quality: (c.attribution?.first_touch_source || "unknown"),
    };
    setBusy(true);
    try {
      await api.post("/admin/revenue/scoring/score", { contact_id: contactId, inputs, notes: "manual recalculation" });
      toast.success("Score recalculated");
      openContact(contactId);
      load();
    } catch (e) { toast.error(e.message); }
    finally { setBusy(false); }
  };

  const changeLifecycle = async (contactId) => {
    const stage = prompt("New lifecycle stage (e.g. new_lead, engaged_lead, qualified_lead, customer):");
    if (!stage) return;
    const reason = prompt("Reason for change (min 8 chars):");
    if (!reason || reason.length < 8) { toast.error("Reason must be at least 8 characters"); return; }
    setBusy(true);
    try {
      await api.post(`/admin/revenue/contacts/${contactId}/lifecycle`, { new_stage: stage, reason });
      toast.success("Lifecycle updated");
      openContact(contactId);
      load();
    } catch (e) { toast.error(e.message); }
    finally { setBusy(false); }
  };

  const recordTouch = async (contactId) => {
    const utm_source = prompt("UTM source (e.g. google, referral, direct):");
    if (!utm_source) return;
    const utm_campaign = prompt("UTM campaign (optional):") || null;
    const source_notes = prompt("Notes (optional):") || null;
    setBusy(true);
    try {
      await api.post(`/admin/revenue/contacts/${contactId}/attribution/touch`, {
        contact_id: contactId,
        utm_source, utm_campaign, source_notes,
      });
      toast.success("Attribution touch recorded");
      openContact(contactId);
    } catch (e) { toast.error(e.message); }
    finally { setBusy(false); }
  };

  if (loading) return <div className="max-w-7xl mx-auto px-5 py-10"><Loader /></div>;

  const live = state?.live_actions_enabled;

  return (
    <div className="max-w-7xl mx-auto px-5 sm:px-8 py-10" data-testid="admin-revenue-page">
      <button onClick={() => nav("/admin")} className="flex items-center gap-1 text-sm text-[var(--asc-text-dim)] hover:text-white mb-3"><ArrowLeft size={14} /> Admin</button>
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="asc-kicker">Phase 1 + 2 + 3 complete · Phase 4 pending approval</div>
          <h1 className="asc-h2 text-4xl mt-1 flex items-center gap-3"><Shield size={28} className="text-[var(--asc-brand)]" /> Revenue Control Center</h1>
          <p className="text-[var(--asc-text-dim)] text-sm mt-2 max-w-3xl">Contacts, offers, deterministic scoring, attribution, approvals, and audit log. All external actions remain <strong>simulated or gated</strong> while <code className="asc-mono text-[var(--asc-brand)]">AUTOMATION_LIVE_ACTIONS_ENABLED=false</code>. Phase 3 will wire the financial ledger.</p>
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
          <button key={t.id} onClick={() => { setTab(t.id); setSelectedContact(null); }} className={`asc-btn-secondary text-xs ${tab === t.id ? "!bg-[var(--asc-brand)] !text-black" : ""}`} data-testid={`revenue-tab-${t.id}`}>
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
            <div className="asc-kicker mb-2">Phase 1 + 2 scope</div>
            <p className="text-sm text-[var(--asc-text-dim)] leading-relaxed">Foundation + CRM layer. Phase 1: contacts, events, approvals, audit log, integration status, operating-budget history. Phase 2: approved offer catalog, deterministic lead scoring (versioned rules + score history), append-only attribution touches (first/last preservation, sanitized), and administrative contact-detail management including a safeguarded merge flow. <strong className="text-white">No revenue data is shown yet</strong> — Phase 3 builds the financial ledger. Records tagged <code className="asc-mono text-[var(--asc-brand)]">simulated=true</code> are for testing only.</p>
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

      {/* ─── PHASE 2 TABS ─── */}

      {/* Contacts */}
      {tab === "contacts" && !selectedContact && (
        <div className="asc-card p-4 mt-5" data-testid="revenue-contacts">
          <div className="asc-kicker mb-3">Contacts · {contacts.length} in view</div>
          {contacts.length === 0 ? <div className="text-sm text-[var(--asc-text-muted)] py-6 text-center">No contacts yet.</div> : (
            <div className="space-y-1 max-h-[600px] overflow-y-auto">
              {contacts.map((c) => (
                <button key={c.id} onClick={() => openContact(c.id)} className="w-full text-left p-3 rounded-lg border border-[var(--asc-border)] hover:border-[var(--asc-brand)] flex flex-wrap items-center gap-3 transition-colors" data-testid={`contact-row-${c.id}`}>
                  <div className="flex-1 min-w-[220px]">
                    <div className="text-sm font-bold">{c.first_name || c.last_name ? `${c.first_name || ""} ${c.last_name || ""}`.trim() : c.email}</div>
                    <div className="text-xs text-[var(--asc-text-dim)] asc-mono">{c.email}</div>
                    <div className="text-[10px] text-[var(--asc-text-muted)] uppercase tracking-wider mt-1">
                      {c.lifecycle_stage || "new_lead"} · {c.customer_status || "prospect"}
                    </div>
                  </div>
                  {c.lead_score != null && <span className="asc-mono text-lg font-bold text-[var(--asc-brand)]">{c.lead_score}</span>}
                  {c.simulated && <span className="text-[9px] px-1.5 py-0.5 rounded font-bold" style={{ background: "rgba(255,176,0,0.15)", color: "#FFB000" }}>SIM</span>}
                  <ChevronRight size={14} className="text-[var(--asc-text-muted)]" />
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Contact Detail */}
      {tab === "contacts" && selectedContact && (
        <div className="mt-5" data-testid="revenue-contact-detail">
          <button onClick={() => setSelectedContact(null)} className="flex items-center gap-1 text-sm text-[var(--asc-text-dim)] hover:text-white mb-3"><ArrowLeft size={14} /> Back to contacts</button>
          <div className="grid lg:grid-cols-3 gap-4">
            <div className="asc-card p-4 lg:col-span-2">
              <div className="asc-kicker mb-2">Contact</div>
              <div className="text-2xl font-bold">{`${selectedContact.contact.first_name || ""} ${selectedContact.contact.last_name || ""}`.trim() || selectedContact.contact.email}</div>
              <div className="text-sm text-[var(--asc-text-dim)] asc-mono">{selectedContact.contact.email}</div>
              <div className="mt-3 grid sm:grid-cols-2 gap-2 text-xs">
                <KV k="Lifecycle" v={selectedContact.contact.lifecycle_stage || "new_lead"} />
                <KV k="Customer Status" v={selectedContact.contact.customer_status || "prospect"} />
                <KV k="Lead Score" v={selectedContact.contact.lead_score ?? "—"} />
                <KV k="Company" v={selectedContact.contact.company_name || "—"} />
                <KV k="Business Type" v={selectedContact.contact.business_type || "—"} />
                <KV k="Organization Size" v={selectedContact.contact.organization_size || "—"} />
                <KV k="First-touch Source" v={selectedContact.contact.attribution?.first_touch_source || "—"} />
                <KV k="Last-touch Source" v={selectedContact.contact.attribution?.last_touch_source || "—"} />
              </div>
              <div className="text-xs text-[var(--asc-text-dim)] mt-3"><strong>Next action:</strong> {selectedContact.next_recommended_action}</div>
              <div className="mt-4 flex flex-wrap gap-2">
                <button onClick={() => recalcScore(selectedContact.contact.id)} disabled={busy} className="asc-btn-primary text-xs" data-testid="btn-recalc-score"><Target size={12} /> Recalculate score</button>
                <button onClick={() => changeLifecycle(selectedContact.contact.id)} disabled={busy} className="asc-btn-secondary text-xs" data-testid="btn-change-lifecycle">Change lifecycle</button>
                <button onClick={() => recordTouch(selectedContact.contact.id)} disabled={busy} className="asc-btn-secondary text-xs" data-testid="btn-record-touch"><GitBranch size={12} /> Record touch</button>
              </div>
            </div>
            <div className="asc-card p-4">
              <div className="asc-kicker mb-2">Recommended offer</div>
              {selectedContact.recommended_offer ? (
                <div>
                  <div className="text-lg font-bold">{selectedContact.recommended_offer.name}</div>
                  <div className="text-2xl font-black asc-mono text-[var(--asc-brand)] mt-1">${selectedContact.recommended_offer.price}<span className="text-xs text-[var(--asc-text-muted)] ml-1">/{selectedContact.recommended_offer.billing_frequency}</span></div>
                  <div className="text-xs text-[var(--asc-text-dim)] mt-2">{selectedContact.recommended_offer.description}</div>
                  <div className="text-[10px] text-[var(--asc-text-muted)] mt-2 uppercase tracking-wider">simulated recommendation</div>
                </div>
              ) : <div className="text-xs text-[var(--asc-text-muted)]">No active offer matches this contact&apos;s band yet.</div>}
            </div>
          </div>

          <div className="grid lg:grid-cols-2 gap-4 mt-4">
            <div className="asc-card p-4" data-testid="score-history">
              <div className="asc-kicker mb-2">Score history ({selectedContact.score_history.length})</div>
              {selectedContact.score_history.length === 0 ? <div className="text-xs text-[var(--asc-text-muted)] py-3">No scores yet.</div> :
                <div className="space-y-1">{selectedContact.score_history.map(s => (
                  <div key={s.id} className="text-xs asc-mono p-2 rounded border border-[var(--asc-border)] flex flex-wrap gap-2">
                    <span className="text-[var(--asc-text-muted)]">{new Date(s.created_at).toLocaleString()}</span>
                    <span className="text-[var(--asc-brand)] font-bold">{s.score}</span>
                    <span>{s.band}</span>
                    <span className="text-[var(--asc-text-dim)]">rs v{s.rule_set_version}</span>
                    {s.delta != null && <span className={`${s.delta >= 0 ? "text-[#4ADE80]" : "text-[#FB7185]"}`}>Δ{s.delta}</span>}
                  </div>
                ))}</div>
              }
            </div>
            <div className="asc-card p-4" data-testid="attribution-touches">
              <div className="asc-kicker mb-2">Attribution touches ({selectedContact.attribution_touches.length})</div>
              {selectedContact.attribution_touches.length === 0 ? <div className="text-xs text-[var(--asc-text-muted)] py-3">No touches recorded.</div> :
                <div className="space-y-1">{selectedContact.attribution_touches.map(t => (
                  <div key={t.id} className="text-xs asc-mono p-2 rounded border border-[var(--asc-border)] flex flex-wrap gap-2">
                    <span className="text-[var(--asc-text-muted)]">{new Date(t.created_at).toLocaleString()}</span>
                    <span className="text-[var(--asc-brand)] font-bold">{t.kind}</span>
                    <span>{t.utm_source || t.lead_source || t.new_source || "—"}</span>
                    {t.utm_campaign && <span className="text-[var(--asc-text-dim)]">/{t.utm_campaign}</span>}
                  </div>
                ))}</div>
              }
            </div>
            <div className="asc-card p-4">
              <div className="asc-kicker mb-2">Recent internal events ({selectedContact.internal_events.length})</div>
              {selectedContact.internal_events.length === 0 ? <div className="text-xs text-[var(--asc-text-muted)] py-3">No events yet.</div> :
                <div className="space-y-1 max-h-[300px] overflow-y-auto">{selectedContact.internal_events.slice(0, 20).map(e => (
                  <div key={e.id} className="text-xs asc-mono p-2 rounded border border-[var(--asc-border)] flex flex-wrap gap-2">
                    <span className="text-[var(--asc-text-muted)]">{new Date(e.created_at).toLocaleString()}</span>
                    <span className="text-[var(--asc-brand)]">{e.event_type}</span>
                    {e.simulated && <span className="text-[9px] px-1 rounded" style={{ background: "rgba(255,176,0,0.15)", color: "#FFB000" }}>SIM</span>}
                  </div>
                ))}</div>
              }
            </div>
            <div className="asc-card p-4">
              <div className="asc-kicker mb-2">Recent audit ({selectedContact.audit_log.length})</div>
              {selectedContact.audit_log.length === 0 ? <div className="text-xs text-[var(--asc-text-muted)] py-3">No audit entries.</div> :
                <div className="space-y-1 max-h-[300px] overflow-y-auto">{selectedContact.audit_log.slice(0, 20).map(a => (
                  <div key={a.id} className="text-xs asc-mono p-2 rounded border border-[var(--asc-border)] flex flex-wrap gap-2">
                    <span className="text-[var(--asc-text-muted)]">{new Date(a.created_at).toLocaleString()}</span>
                    <span className="text-[var(--asc-brand)]">{a.action}</span>
                    <span className="text-[var(--asc-text-dim)]">{a.actor}</span>
                  </div>
                ))}</div>
              }
            </div>
          </div>
        </div>
      )}

      {/* Offers */}
      {tab === "offers" && (
        <div className="asc-card p-4 mt-5" data-testid="revenue-offers">
          <div className="flex items-center justify-between mb-3">
            <div className="asc-kicker">Approved offer catalog · {offers.length}</div>
            <button onClick={importExistingOffers} disabled={busy} className="asc-btn-primary text-xs" data-testid="offers-import"><Plus size={12} /> Import existing tiers</button>
          </div>
          <p className="text-xs text-[var(--asc-text-dim)] mb-3">The Approved Offer Catalog is the source-of-truth for what may be sold. Draft offers are not publicly available; only active offers appear in scoring recommendations. Material changes to active offers require approval-queue authorization.</p>
          {offers.length === 0 ? <div className="text-sm text-[var(--asc-text-muted)] py-6 text-center">No offers in the catalog. Click &ldquo;Import existing tiers&rdquo; to seed Ascender/Pathfinder/Sage/Business from the existing configuration.</div> : (
            <div className="space-y-2">
              {offers.map((o) => (
                <div key={o.id} className="p-3 rounded-lg border border-[var(--asc-border)] flex flex-wrap items-center gap-3" data-testid={`offer-${o.offer_code}`}>
                  <div className="flex-1 min-w-[240px]">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-sm font-bold">{o.name}</span>
                      <span className="text-[10px] asc-mono text-[var(--asc-text-muted)]">{o.offer_code}</span>
                      <StatusPill status={o.active_status ? "active" : (o.draft_status ? "draft" : "inactive")} />
                    </div>
                    <div className="text-xs text-[var(--asc-text-dim)] mt-1">{o.description || o.category}</div>
                    <div className="text-[10px] text-[var(--asc-text-muted)] mt-1 asc-mono">
                      {o.category} · {o.billing_frequency}
                      {o.external_price_id ? ` · stripe:${o.external_price_id.slice(0, 12)}…` : " · no external price ID"}
                    </div>
                  </div>
                  <div className="text-2xl font-black asc-mono text-[var(--asc-brand)]">${o.price}</div>
                  <div className="flex gap-1">
                    {o.active_status
                      ? <button onClick={() => deactivateOffer(o.id)} disabled={busy} className="asc-btn-secondary text-xs" data-testid={`deactivate-${o.offer_code}`}>Deactivate</button>
                      : <button onClick={() => activateOffer(o.id)} disabled={busy} className="asc-btn-primary text-xs" data-testid={`activate-${o.offer_code}`}>Activate</button>}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Scoring Rules */}
      {tab === "scoring" && (
        <div className="asc-card p-4 mt-5" data-testid="revenue-scoring">
          <div className="asc-kicker mb-3">Scoring rule sets · {scoringRules.rule_sets.length}</div>
          {scoringRules.current && (
            <div className="rounded-lg p-4 mb-4" style={{ background: "rgba(74,222,128,0.05)", border: "1px solid rgba(74,222,128,0.25)" }} data-testid="scoring-current">
              <div className="text-[10px] uppercase tracking-wider text-[#4ADE80]">Active rule set · v{scoringRules.current.version}</div>
              <div className="text-lg font-bold">{scoringRules.current.name}</div>
              <div className="text-xs text-[var(--asc-text-dim)] mt-2">Weights (per factor):</div>
              <div className="grid sm:grid-cols-2 md:grid-cols-3 gap-1 text-xs asc-mono mt-1">
                {Object.entries(scoringRules.current.weights || {}).map(([k, v]) => (
                  <div key={k} className="p-2 rounded border border-[var(--asc-border)]">
                    <div className="text-[var(--asc-text-muted)] text-[10px] uppercase tracking-wider">{k}</div>
                    <div className="text-[var(--asc-brand)] font-bold">weight {v.weight} · {v.type}</div>
                  </div>
                ))}
              </div>
              <div className="text-xs text-[var(--asc-text-dim)] mt-3">Band thresholds:</div>
              <div className="flex flex-wrap gap-2 mt-1">
                {Object.entries(scoringRules.current.band_thresholds || {}).map(([b, [lo, hi]]) => (
                  <span key={b} className="text-[10px] px-2 py-0.5 rounded-full asc-mono" style={{ background: "rgba(255,176,0,0.10)", color: "#FFB000" }}>{b}: {lo}–{hi}</span>
                ))}
              </div>
            </div>
          )}
          <p className="text-xs text-[var(--asc-text-dim)]">Deterministic scoring engine. Identical inputs always yield identical outputs — no unstructured AI guess directly determines a score. Rule changes are version-preserved; every score run is written to <code className="asc-mono">contact_scores</code> for full traceability.</p>
        </div>
      )}

      {/* Attribution */}
      {tab === "attribution" && (
        <div className="asc-card p-4 mt-5" data-testid="revenue-attribution">
          <div className="asc-kicker mb-3">Source & campaign attribution</div>
          <p className="text-xs text-[var(--asc-text-dim)] mb-4">Simple, append-only attribution. First-touch source is preserved once established; last-touch updates on every valid touch. All UTM values are normalized and URLs are sanitized. Corrections require a documented reason and are audited. <strong>No referral, affiliate, commission, or payout system is implemented</strong> — a manually entered referrer name / email does not create a contractual relationship.</p>
          <div className="grid md:grid-cols-3 gap-3 text-xs">
            <div className="asc-card p-3">
              <div className="asc-kicker mb-1">Supported UTM keys</div>
              <div className="asc-mono">utm_source · utm_medium · utm_campaign · utm_content · utm_term</div>
            </div>
            <div className="asc-card p-3">
              <div className="asc-kicker mb-1">Source fields</div>
              <div className="asc-mono">lead_source · referral_source · campaign_source · source_url · source_notes · referred_by_name/email</div>
            </div>
            <div className="asc-card p-3">
              <div className="asc-kicker mb-1">Preservation rule</div>
              <div>First-touch = preserved. Last-touch = updated on new valid touch. Corrections = audited, require reason ≥ 8 chars.</div>
            </div>
          </div>
          <div className="text-xs text-[var(--asc-text-dim)] mt-4">Open a contact under the <strong>Contacts</strong> tab to view or record attribution touches.</div>
        </div>
      )}

      {/* ─── PHASE 3 TABS ─── */}

      {/* Financial Ledger */}
      {tab === "ledger" && (
        <div className="asc-card p-4 mt-5" data-testid="revenue-ledger">
          <div className="asc-kicker mb-2">Financial Ledger · {ledger.length} entries (append-only)</div>
          <p className="text-xs text-[var(--asc-text-dim)] mb-3">
            This is an <strong>internal cash-management subledger</strong>. It is NOT
            professional bookkeeping, tax preparation, banking, or a general ledger.
            Calculated tax reserves are internal estimates and are not tax advice.
            Corrections and reversals are posted as new adjustment entries — never
            as mutations of prior entries.
          </p>
          {ledger.length === 0 ? <div className="text-sm text-[var(--asc-text-muted)] py-6 text-center">No ledger entries yet. Manual preview transactions may be recorded via the API.</div> : (
            <div className="space-y-1 max-h-[600px] overflow-y-auto">
              {ledger.map((e) => (
                <div key={e.id} className="text-xs asc-mono p-2 rounded border border-[var(--asc-border)] flex flex-wrap gap-2 items-center" data-testid={`ledger-${e.id}`}>
                  <span className="text-[var(--asc-text-muted)]">{new Date(e.created_at).toLocaleString()}</span>
                  <span className="text-[var(--asc-brand)] font-bold">{e.entry_type}</span>
                  <StatusPill status={e.settlement_status} />
                  <span className="text-white">${e.gross_amount}</span>
                  <span className="text-[var(--asc-text-dim)]">net=${e.net_distributable_amount}</span>
                  {e.allocated && <span className="text-[9px] px-1 rounded" style={{ background: "rgba(74,222,128,0.15)", color: "#4ADE80" }}>ALLOC</span>}
                  {e.simulated && <span className="text-[9px] px-1 rounded" style={{ background: "rgba(255,176,0,0.15)", color: "#FFB000" }}>TEST</span>}
                  <span className="text-[10px] text-[var(--asc-text-muted)]">{e.source}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Essential Expenses */}
      {tab === "expenses" && (
        <div className="asc-card p-4 mt-5" data-testid="revenue-expenses">
          <div className="asc-kicker mb-2">Essential Operating Expenses · {expenses.length}</div>
          <p className="text-xs text-[var(--asc-text-dim)] mb-3">Only expenses explicitly classified as <strong>essential</strong> count toward the three-month reserve target. Corrections use append-only replacement records — prior versions are preserved.</p>
          {expenses.length === 0 ? <div className="text-sm text-[var(--asc-text-muted)] py-6 text-center">No expenses recorded.</div> : (
            <div className="space-y-1">
              {expenses.map((x) => (
                <div key={x.id} className="text-xs p-2 rounded border border-[var(--asc-border)] flex flex-wrap gap-2 items-center" data-testid={`expense-${x.id}`}>
                  <span className="asc-mono text-[var(--asc-text-muted)]">{x.expense_month}</span>
                  <span className="text-[var(--asc-brand)] font-bold uppercase text-[10px]">{x.category}</span>
                  <span>{x.description}</span>
                  <span className="asc-mono text-white ml-auto">${x.amount}</span>
                  {x.essential ? <span className="text-[9px] px-1 rounded" style={{ background: "rgba(74,222,128,0.15)", color: "#4ADE80" }}>ESSENTIAL</span> : <span className="text-[9px] px-1 rounded" style={{ background: "rgba(138,131,184,0.15)", color: "#8A83B8" }}>DISCRETIONARY</span>}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Reserve Target */}
      {tab === "reserve" && (
        <div className="asc-card p-4 mt-5" data-testid="revenue-reserve">
          <div className="asc-kicker mb-3">Three-month Working-capital Reserve Target</div>
          {reserve ? (
            <div className="space-y-4">
              <div className="grid md:grid-cols-3 gap-3">
                <Stat label="Three-month target" value={`$${reserve.three_month_target}`} sub={`method: ${reserve.calculation_method}`} />
                <Stat label="Current WC reserve" value={`$${reserve.current_working_capital_reserve}`} sub="derived from ledger" />
                <Stat label="Amount remaining" value={`$${reserve.amount_remaining}`} sub="until phase transition" tone={Number(reserve.amount_remaining) > 0 ? "warn" : "ok"} />
              </div>
              <div className="text-xs text-[var(--asc-text-dim)] space-y-1">
                {reserve.average_monthly_essential_expenses && <div>Average monthly essential expenses: <span className="asc-mono text-white">${reserve.average_monthly_essential_expenses}</span></div>}
                {reserve.approved_budget_used && <div>Approved budget used (fallback): <span className="asc-mono text-white">${reserve.approved_budget_used}</span></div>}
                <div>Included months: <span className="asc-mono">{(reserve.included_months || []).join(", ") || "—"}</span></div>
                <div>Excluded months: <span className="asc-mono">{(reserve.excluded_months || []).join(", ") || "—"}</span></div>
                <div>Calculated at: <span className="asc-mono">{reserve.calculated_at}</span></div>
              </div>
            </div>
          ) : <div className="text-sm text-[var(--asc-text-muted)] py-6 text-center">Reserve calculation unavailable.</div>}
        </div>
      )}

      {/* Allocation Policy */}
      {tab === "allocation" && (
        <div className="asc-card p-4 mt-5" data-testid="revenue-allocation">
          <div className="asc-kicker mb-3">Cash-allocation Policy · current phase: <span className="text-[var(--asc-brand)]">{allocPolicies.current_phase}</span></div>
          <p className="text-xs text-[var(--asc-text-dim)] mb-3">Startup 25/25/50 → Established 50/25/25. Phase transitions occur <strong>only at month-end reconciliation</strong> and never retroactively. Changes require approval-queue authorization.</p>
          <div className="space-y-2">
            {allocPolicies.policies.map((p) => (
              <div key={p.id} className="p-3 rounded-lg border border-[var(--asc-border)] flex flex-wrap items-center gap-3" data-testid={`policy-${p.phase}-v${p.version}`}>
                <div className="flex-1 min-w-[200px]">
                  <div className="text-sm font-bold uppercase">{p.phase} · v{p.version}</div>
                  <div className="text-xs text-[var(--asc-text-dim)] asc-mono">
                    owner {p.owner_pct}% · growth {p.growth_reserve_pct}% · working-capital {p.working_capital_pct}%
                  </div>
                </div>
                {p.active && <StatusPill status="active" />}
              </div>
            ))}
          </div>
          <div className="asc-kicker mt-4 mb-2">Tax-reserve Policies</div>
          {taxPolicies.length === 0 ? <div className="text-xs text-[var(--asc-text-muted)] p-3 rounded border border-[#FB7185]/30 bg-[#FB7185]/5">⚠ Tax reserve policy incomplete — reconciliations and owner-draw recommendations will be BLOCKED until an admin creates and activates a tax policy.</div> : (
            <div className="space-y-1">
              {taxPolicies.map((tp) => (
                <div key={tp.id} className="p-2 rounded border border-[var(--asc-border)] text-xs asc-mono flex flex-wrap gap-2" data-testid={`tax-policy-v${tp.version}`}>
                  <span>v{tp.version}</span>
                  <span>fed {tp.federal_reserve_pct}%</span>
                  <span>state {tp.state_reserve_pct}%</span>
                  <span>other {tp.other_reserve_pct}%</span>
                  {tp.active && <StatusPill status="active" />}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Monthly Reconciliation */}
      {tab === "recon" && (
        <div className="asc-card p-4 mt-5" data-testid="revenue-recon">
          <div className="asc-kicker mb-3">Monthly Reconciliations · {recons.length}</div>
          <p className="text-xs text-[var(--asc-text-dim)] mb-3">One reconciliation per calendar month. A closed month is immutable — post-close corrections must be recorded as current-period adjustments referencing the prior month.</p>
          {recons.length === 0 ? <div className="text-sm text-[var(--asc-text-muted)] py-6 text-center">No reconciliations yet.</div> : (
            <div className="space-y-1">
              {recons.map((r) => (
                <div key={r.id} className="p-3 rounded-lg border border-[var(--asc-border)] flex flex-wrap items-center gap-3" data-testid={`recon-${r.calendar_month}`}>
                  <div className="flex-1 min-w-[220px]">
                    <div className="text-sm font-bold">{r.calendar_month}</div>
                    <div className="text-[10px] text-[var(--asc-text-muted)] asc-mono">
                      gross ${r.gross_collected} · cleared ${r.cleared_collected} · net ${r.net_distributable}
                    </div>
                  </div>
                  <StatusPill status={r.status} />
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Owner Draws */}
      {tab === "draws" && (
        <div className="asc-card p-4 mt-5" data-testid="revenue-draws">
          <div className="asc-kicker mb-3">Owner-draw Recommendations · {draws.length}</div>
          <p className="text-xs text-[var(--asc-text-dim)] mb-3">Ascendra <strong>never</strong> initiates a transfer or a Stripe payout. Owner draws are internal recommendations only. Recommendation date = first weekday on/after the 5th of the following month. Late refunds or disputes are posted as current-period adjustments.</p>
          {p3summary && (
            <div className="grid md:grid-cols-4 gap-2 mb-4">
              <Stat label="Owner distribution payable" value={`$${p3summary.owner_distribution_payable}`} />
              <Stat label="Growth reserve" value={`$${p3summary.growth_reserve}`} />
              <Stat label="Working-capital reserve" value={`$${p3summary.working_capital_reserve}`} />
              <Stat label="Next draw date" value={p3summary.next_owner_draw_recommendation_date} sub="business tz America/Chicago" />
            </div>
          )}
          {draws.length === 0 ? <div className="text-sm text-[var(--asc-text-muted)] py-6 text-center">No owner-draw recommendations yet. Close a monthly reconciliation to generate one.</div> : (
            <div className="space-y-2">
              {draws.map((d) => (
                <div key={d.id} className="p-3 rounded-lg border border-[var(--asc-border)] flex flex-wrap items-center gap-3" data-testid={`draw-${d.reconciliation_month}`}>
                  <div className="flex-1 min-w-[240px]">
                    <div className="text-sm font-bold">{d.reconciliation_month} → pay {d.recommendation_date}</div>
                    <div className="text-[10px] text-[var(--asc-text-muted)] asc-mono">
                      recommended ${d.recommended_amount} · eligible ${d.eligible_owner_allocation}
                    </div>
                    {d.manually_paid_amount != null && <div className="text-[10px] text-[#4ADE80]">manual paid ${d.manually_paid_amount} · ref {d.manual_payment_reference}</div>}
                  </div>
                  <StatusPill status={d.status} />
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ─── PHASE 4 TABS ─── */}

      {tab === "workflows" && (
        <div className="asc-card p-4 mt-5" data-testid="revenue-workflows">
          <div className="asc-kicker mb-3">Workflow Definitions · {workflows.length}</div>
          <p className="text-xs text-[var(--asc-text-dim)] mb-3">All workflows start as <strong>draft/disabled</strong>. Activation requires an approval-queue authorization matched by request_type, target_id, version, and correlation_id. No workflow may send live communications while the safety gate is off.</p>
          {workflows.length === 0 ? <div className="text-sm text-[var(--asc-text-muted)] py-6 text-center">No workflows defined yet.</div> : (
            <div className="space-y-1 max-h-[600px] overflow-y-auto">
              {workflows.map(w => (
                <div key={w.id} className="p-3 rounded-lg border border-[var(--asc-border)] flex flex-wrap items-center gap-3" data-testid={`workflow-${w.workflow_code}`}>
                  <div className="flex-1 min-w-[220px]">
                    <div className="text-sm font-bold">{w.name}</div>
                    <div className="text-[10px] text-[var(--asc-text-muted)] asc-mono">{w.workflow_code} · trigger: {w.trigger_event} · v{w.version}</div>
                  </div>
                  <StatusPill status={w.active ? "active" : (w.draft ? "draft" : "inactive")} />
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {tab === "actions" && (
        <div className="asc-card p-4 mt-5" data-testid="revenue-actions">
          <div className="asc-kicker mb-3">Action Queue · {actions.length}</div>
          <p className="text-xs text-[var(--asc-text-dim)] mb-3">Every intended action is evaluated by the deterministic authority matrix. While live actions are disabled, actions that would touch a provider resolve to <strong>simulated</strong>, <strong>awaiting_approval</strong>, or <strong>blocked</strong> — never to live executing.</p>
          {actions.length === 0 ? <div className="text-sm text-[var(--asc-text-muted)] py-6 text-center">No actions queued.</div> : (
            <div className="space-y-1 max-h-[600px] overflow-y-auto">
              {actions.map(a => (
                <div key={a.id} className="text-xs p-2 rounded border border-[var(--asc-border)] flex flex-wrap gap-2 items-center" data-testid={`action-${a.id}`}>
                  <span className="asc-mono text-[var(--asc-text-muted)]">{new Date(a.created_at).toLocaleString()}</span>
                  <span className="text-[var(--asc-brand)] font-bold">{a.action_type}</span>
                  <StatusPill status={a.status} />
                  {a.authority_decision && <span className="text-[9px] px-1 rounded" style={{ background: "rgba(138,131,184,0.15)", color: "#8A83B8" }}>{a.authority_decision.decision}</span>}
                  {a.approval_required && <span className="text-[9px] px-1 rounded" style={{ background: "rgba(124,58,237,0.18)", color: "#BFB4FF" }}>APPROVAL</span>}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {tab === "templates" && (
        <div className="asc-card p-4 mt-5" data-testid="revenue-templates">
          <div className="asc-kicker mb-3">Approved Templates · {templates.length}</div>
          <p className="text-xs text-[var(--asc-text-dim)] mb-3">Templates use an <strong>allowlisted variable</strong> mechanism. Bodies with unapproved variables or prohibited claims (e.g. &ldquo;guaranteed income&rdquo;) are rejected at creation time. Contact-provided values are HTML-escaped before rendering.</p>
          {templates.length === 0 ? <div className="text-sm text-[var(--asc-text-muted)] py-6 text-center">No templates yet.</div> : (
            <div className="space-y-1">
              {templates.map(t => (
                <div key={t.id} className="p-3 rounded-lg border border-[var(--asc-border)] flex flex-wrap items-center gap-3" data-testid={`template-${t.template_code}`}>
                  <div className="flex-1 min-w-[220px]">
                    <div className="text-sm font-bold">{t.subject || t.template_code}</div>
                    <div className="text-[10px] text-[var(--asc-text-muted)] asc-mono">{t.template_code} · {t.channel} · v{t.version} · vars: {(t.approved_variables||[]).join(", ") || "none"}</div>
                  </div>
                  <StatusPill status={t.active ? "active" : (t.draft ? "draft" : "inactive")} />
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {tab === "knowledge" && (
        <div className="asc-card p-4 mt-5" data-testid="revenue-knowledge">
          <div className="asc-kicker mb-3">Approved Knowledge Base · {knowledge.length}</div>
          <p className="text-xs text-[var(--asc-text-dim)] mb-3">Automation may only answer using facts in this approved knowledge base. Unknown questions about <strong>pricing, refunds, contracts, legal, tax, security, privacy, guarantees, or product capabilities</strong> escalate to an internal support task — no invented response is ever generated.</p>
          {knowledge.length === 0 ? <div className="text-sm text-[var(--asc-text-muted)] py-6 text-center">Knowledge base is empty. Admins may add approved facts via the API.</div> : (
            <div className="space-y-1">
              {knowledge.map(k => (
                <div key={k.id} className="p-3 rounded-lg border border-[var(--asc-border)]" data-testid={`kb-${k.id}`}>
                  <div className="text-sm font-bold">{k.topic}</div>
                  <div className="text-xs text-[var(--asc-text-dim)] mt-1">{k.approved_answer}</div>
                  <div className="text-[10px] text-[var(--asc-text-muted)] asc-mono mt-1">v{k.version} · {k.source_reference || "no source ref"}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {tab === "authority" && (
        <div className="asc-card p-4 mt-5" data-testid="revenue-authority">
          <div className="asc-kicker mb-3">AI Authority + Risk Matrix · policy v{authority?.policy_version ?? "—"}</div>
          <p className="text-xs text-[var(--asc-text-dim)] mb-3">Deterministic action classification. <strong>Language models cannot override this matrix</strong>. Unknown action types receive the safe default: contain, pause, preserve records, respond neutrally.</p>
          {authority?.entries && (
            <div className="grid md:grid-cols-2 gap-2 max-h-[600px] overflow-y-auto">
              {authority.entries.map(e => (
                <div key={e.action_type} className="p-2 rounded border border-[var(--asc-border)] text-xs" data-testid={`auth-${e.action_type}`}>
                  <div className="asc-mono text-white font-bold">{e.action_type}</div>
                  <div className="flex flex-wrap gap-1 mt-1">
                    <span className="text-[9px] px-1.5 py-0.5 rounded font-bold uppercase tracking-wider" style={{
                      background: e.decision === "prohibited" ? "rgba(251,113,133,0.18)"
                               : e.decision === "requires_approval" ? "rgba(124,58,237,0.18)"
                               : e.decision === "permitted_if_live" ? "rgba(255,176,0,0.18)"
                               : "rgba(74,222,128,0.18)",
                      color: e.decision === "prohibited" ? "#FB7185"
                           : e.decision === "requires_approval" ? "#BFB4FF"
                           : e.decision === "permitted_if_live" ? "#FFB000"
                           : "#4ADE80",
                    }}>{e.decision}</span>
                    <span className="text-[9px] px-1 rounded" style={{ background: "rgba(138,131,184,0.15)", color: "#8A83B8" }}>risk: {e.risk_category}</span>
                  </div>
                  {e.explanation && <div className="text-[10px] text-[var(--asc-text-dim)] mt-1">{e.explanation}</div>}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {tab === "webhooks" && (
        <div className="asc-card p-4 mt-5" data-testid="revenue-webhooks">
          <div className="asc-kicker mb-3">Normalized Webhook Events · {webhooks.length}</div>
          <p className="text-xs text-[var(--asc-text-dim)] mb-3">Phase 4 shadow processor coexists with the existing <code className="asc-mono">/api/billing/webhook</code>. Signature verification uses <code className="asc-mono">STRIPE_WEBHOOK_SECRET_TEST</code> so live secrets are never referenced. Duplicate provider events are rejected via a unique index on <code className="asc-mono">provider_event_id</code>.</p>
          {webhooks.length === 0 ? <div className="text-sm text-[var(--asc-text-muted)] py-6 text-center">No webhook events yet.</div> : (
            <div className="space-y-1 max-h-[600px] overflow-y-auto">
              {webhooks.map(w => (
                <div key={w.id} className="text-xs asc-mono p-2 rounded border border-[var(--asc-border)] flex flex-wrap gap-2" data-testid={`webhook-${w.provider_event_id}`}>
                  <span className="text-[var(--asc-text-muted)]">{new Date(w.created_at).toLocaleString()}</span>
                  <span className="text-[var(--asc-brand)] font-bold">{w.event_type}</span>
                  <span className="text-[var(--asc-text-dim)]">{w.provider_event_id}</span>
                  {w.simulated && <span className="text-[9px] px-1 rounded" style={{ background: "rgba(255,176,0,0.15)", color: "#FFB000" }}>TEST</span>}
                </div>
              ))}
            </div>
          )}
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

function KV({ k, v }) {
  return (
    <div className="flex items-baseline gap-2">
      <span className="text-[10px] uppercase tracking-wider text-[var(--asc-text-muted)]">{k}</span>
      <span className="text-[var(--asc-text)] asc-mono">{String(v)}</span>
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
    active:    { bg: "rgba(74,222,128,0.18)", fg: "#4ADE80" },
    draft:     { bg: "rgba(255,176,0,0.18)",  fg: "#FFB000" },
    inactive:  { bg: "rgba(138,131,184,0.15)",fg: "#8A83B8" },
  };
  const c = map[status] || map.cancelled;
  return <span className="text-[9px] px-2 py-0.5 rounded-full font-bold uppercase tracking-wider" style={{ background: c.bg, color: c.fg }}>{status}</span>;
}
