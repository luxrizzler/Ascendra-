import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { toast } from "sonner";
import Loader from "@/components/Loader";
import {
  ShieldAlert,
  RefreshCw,
  Clock,
  Link2Off,
  RotateCcw,
  Play,
  CheckCircle2,
  AlertTriangle,
  ExternalLink,
} from "lucide-react";

export default function AdminContentHealth() {
  const [scanning, setScanning] = useState(false);
  const [running, setRunning] = useState(false);
  const [report, setReport] = useState(null);
  const [audit, setAudit] = useState([]);
  const [status, setStatus] = useState(null);
  const [reverting, setReverting] = useState(null);
  const [tab, setTab] = useState("scan");

  const loadAudit = async () => {
    try {
      const r = await api.get("/admin/content-health/audit?limit=100");
      setAudit(r.audit || []);
    } catch (e) { toast.error(e.message); }
  };
  const loadStatus = async () => {
    try {
      const s = await api.get("/admin/content-health/status");
      setStatus(s);
    } catch (e) { /* silent */ }
  };

  useEffect(() => { loadAudit(); loadStatus(); }, []);

  const runScan = async () => {
    setScanning(true);
    try {
      const r = await api.get("/admin/content-health/scan?stale_days=120&check_dead_links=true");
      setReport(r);
      toast.success(`Scan complete — ${r.counts.total} lessons flagged`);
    } catch (e) { toast.error(e.message); }
    finally { setScanning(false); }
  };

  const runAutoUpdate = async () => {
    if (!confirm("This will scan all lessons and auto-refresh outdated / stale ones using Claude. Continue?")) return;
    setRunning(true);
    try {
      const r = await api.post("/admin/content-health/run?max_updates=25");
      toast.success(`Auto-update done: ${r.updated} refreshed, ${r.failed} failed`);
      setReport(r.report);
      await loadAudit(); await loadStatus();
    } catch (e) { toast.error(e.message); }
    finally { setRunning(false); }
  };

  const refreshOne = async (f) => {
    if (!confirm(`Force-refresh “${f.lesson_title}”? A backup will be saved so you can revert.`)) return;
    try {
      await api.post(`/admin/content-health/update-lesson/${f.path_id}/${f.module_id}/${f.lesson_id}`);
      toast.success("Lesson refreshed");
      await loadAudit();
    } catch (e) { toast.error(e.message); }
  };

  const revertOne = async (historyId, lessonTitle) => {
    if (!confirm(`Revert “${lessonTitle}” to the pre-update snapshot?`)) return;
    setReverting(historyId);
    try {
      await api.post(`/admin/content-health/revert/${historyId}`);
      toast.success("Reverted to previous version");
      await loadAudit();
    } catch (e) { toast.error(e.message); }
    finally { setReverting(null); }
  };

  return (
    <div className="min-h-screen px-6 py-8" data-testid="admin-content-health-page">
      <div className="max-w-7xl mx-auto">
        <div className="flex flex-wrap items-end justify-between gap-4 mb-6">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-[var(--asc-border-strong)] mb-3" style={{ background: "rgba(239,68,68,0.10)" }}>
              <ShieldAlert size={13} color="#EF4444" />
              <span className="asc-label" style={{ color: "#EF4444" }}>Content Health</span>
            </div>
            <h1 className="asc-h1 text-3xl sm:text-4xl" data-testid="content-health-heading">Autoscan &amp; Auto-Update</h1>
            <p className="text-[var(--asc-text-dim)] mt-2 text-sm max-w-2xl">
              Detects outdated model references, stale content, and dead links. Auto-updates flagged lessons via Claude with full history backup.
              Weekly auto-scan runs every Sunday 03:00 UTC.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button onClick={runScan} disabled={scanning || running} className="asc-btn-secondary" data-testid="content-health-scan-btn">
              {scanning ? "Scanning…" : (<><RefreshCw size={14} /> Scan now</>)}
            </button>
            <button onClick={runAutoUpdate} disabled={scanning || running} className="asc-btn-primary" data-testid="content-health-run-btn">
              {running ? "Updating…" : (<><Play size={14} /> Scan + Auto-Update</>)}
            </button>
          </div>
        </div>

        {/* Last run stats */}
        {status && status.finished_at && (
          <div className="grid sm:grid-cols-4 gap-3 mb-6">
            <StatBox label="Last run" value={new Date(status.finished_at).toLocaleString()} />
            <StatBox label="Lessons scanned" value={status.scanned || 0} />
            <StatBox label="Auto-updated" value={status.updated || 0} color="#22c55e" />
            <StatBox label="Failed" value={status.failed || 0} color={(status.failed||0) > 0 ? "#EF4444" : undefined} />
          </div>
        )}

        {/* Tabs */}
        <div className="flex gap-2 mb-4 border-b border-[var(--asc-border)]">
          <TabBtn active={tab === "scan"} onClick={() => setTab("scan")} testid="tab-scan">Scan Findings</TabBtn>
          <TabBtn active={tab === "audit"} onClick={() => setTab("audit")} testid="tab-audit">Audit Log ({audit.length})</TabBtn>
        </div>

        {tab === "scan" && (
          <ScanFindings report={report} onRefresh={refreshOne} />
        )}
        {tab === "audit" && (
          <AuditLog audit={audit} reverting={reverting} onRevert={revertOne} />
        )}
      </div>
    </div>
  );
}

function StatBox({ label, value, color }) {
  return (
    <div className="asc-card p-4">
      <div className="text-xs text-[var(--asc-text-muted)] tracking-wider">{label.toUpperCase()}</div>
      <div className="text-2xl font-black mt-1" style={{ color: color || "#fff" }}>{value}</div>
    </div>
  );
}

function TabBtn({ active, onClick, testid, children }) {
  return (
    <button
      onClick={onClick}
      data-testid={testid}
      className={`px-4 py-2 text-sm font-bold border-b-2 transition ${active ? "text-[#FFB000] border-[#FFB000]" : "text-[var(--asc-text-muted)] border-transparent hover:text-white"}`}
    >
      {children}
    </button>
  );
}

function ScanFindings({ report, onRefresh }) {
  if (!report) return (
    <div className="asc-card p-8 text-center text-[var(--asc-text-dim)]">
      Click <b className="text-white">Scan now</b> to check all lessons, or <b className="text-white">Scan + Auto-Update</b> to run the full pipeline.
    </div>
  );
  const { counts, findings } = report;
  return (
    <div>
      <div className="grid sm:grid-cols-4 gap-3 mb-4">
        <StatBox label="Total flagged" value={counts.total} />
        <StatBox label="Outdated models" value={counts.outdated_model} color="#FFB000" />
        <StatBox label="Stale (120+ days)" value={counts.stale} color="#38BDF8" />
        <StatBox label="Dead links" value={counts.dead_links} color="#EF4444" />
      </div>
      {findings.length === 0 ? (
        <div className="asc-card p-8 text-center">
          <CheckCircle2 size={28} color="#22c55e" className="mx-auto" />
          <div className="asc-h2 text-xl mt-3">All clear!</div>
          <p className="text-[var(--asc-text-dim)] mt-2 text-sm">No outdated models, stale content, or dead links found.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {findings.map((f) => (
            <div key={f.lesson_id} className="asc-card p-4" data-testid={`finding-${f.lesson_id}`}>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <div className="text-xs text-[var(--asc-text-muted)] mb-1">{f.path_title} › {f.module_title}</div>
                  <div className="font-bold text-white text-lg">{f.lesson_title}</div>
                  {f.last_updated && <div className="text-xs text-[var(--asc-text-muted)] mt-1">Last updated: {new Date(f.last_updated).toLocaleDateString()}</div>}
                </div>
                <button onClick={() => onRefresh(f)} className="asc-btn-secondary text-sm" data-testid={`refresh-${f.lesson_id}`}>
                  <RefreshCw size={12} /> Refresh now
                </button>
              </div>
              <div className="flex flex-wrap gap-2 mt-3">
                {f.outdated_terms?.map((t, i) => (
                  <span key={i} className="px-2 py-1 rounded-full text-xs font-bold flex items-center gap-1" style={{ background: "rgba(255,176,0,0.15)", color: "#FFB000" }}>
                    <AlertTriangle size={11} /> {t}
                  </span>
                ))}
                {f.is_stale && (
                  <span className="px-2 py-1 rounded-full text-xs font-bold flex items-center gap-1" style={{ background: "rgba(56,189,248,0.15)", color: "#38BDF8" }}>
                    <Clock size={11} /> Stale
                  </span>
                )}
                {f.dead_links?.map((d, i) => (
                  <span key={i} className="px-2 py-1 rounded-full text-xs font-bold flex items-center gap-1" style={{ background: "rgba(239,68,68,0.15)", color: "#EF4444" }} title={d.error || `HTTP ${d.status}`}>
                    <Link2Off size={11} /> {d.url.length > 40 ? d.url.slice(0, 40) + "…" : d.url}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function AuditLog({ audit, reverting, onRevert }) {
  if (audit.length === 0) return (
    <div className="asc-card p-8 text-center text-[var(--asc-text-dim)]">No auto-updates yet.</div>
  );
  return (
    <div className="space-y-3">
      {audit.map((a) => (
        <div key={a.id} className="asc-card p-4" data-testid={`audit-${a.id}`}>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <StatusPill status={a.status} />
                <span className="text-xs text-[var(--asc-text-muted)]">{new Date(a.created_at).toLocaleString()}</span>
                <span className="text-xs text-[var(--asc-text-muted)]">· {a.trigger}</span>
              </div>
              <div className="font-bold text-white mt-1">{a.lesson_title}</div>
              {a.reason && (
                <div className="flex flex-wrap gap-1.5 mt-2 text-xs">
                  {a.reason.outdated_terms?.map((t, i) => (
                    <span key={i} className="px-1.5 py-0.5 rounded-full" style={{ background: "rgba(255,176,0,0.12)", color: "#FFB000" }}>{t}</span>
                  ))}
                  {a.reason.is_stale && (<span className="px-1.5 py-0.5 rounded-full" style={{ background: "rgba(56,189,248,0.12)", color: "#38BDF8" }}>stale</span>)}
                </div>
              )}
              {a.error && <div className="text-xs text-[#EF4444] mt-1 font-mono">{a.error}</div>}
            </div>
            {a.status === "success" && a.history_id && (
              <button onClick={() => onRevert(a.history_id, a.lesson_title)} disabled={reverting === a.history_id} className="px-3 py-1.5 rounded-full text-xs font-bold border border-[var(--asc-border)] hover:text-white text-[var(--asc-text-muted)] flex items-center gap-1.5" data-testid={`revert-${a.id}`}>
                <RotateCcw size={11} /> {reverting === a.history_id ? "…" : "Revert"}
              </button>
            )}
            {a.lesson_id && (
              <a href={`/lessons/${a.lesson_id}`} target="_blank" rel="noreferrer noopener" className="text-xs text-[var(--asc-brand)] hover:underline flex items-center gap-1">
                <ExternalLink size={11} /> View
              </a>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

function StatusPill({ status }) {
  const map = {
    success:  { bg: "rgba(34,197,94,0.15)", color: "#22c55e", label: "UPDATED" },
    failed:   { bg: "rgba(239,68,68,0.15)", color: "#EF4444", label: "FAILED" },
    reverted: { bg: "rgba(191,180,255,0.15)", color: "#BFB4FF", label: "REVERTED" },
    "no-op":  { bg: "rgba(148,163,184,0.15)", color: "#94a3b8", label: "NO CHANGE" },
  };
  const s = map[status] || map["no-op"];
  return <span className="px-2 py-0.5 rounded-full text-[10px] font-black tracking-wider" style={{ background: s.bg, color: s.color }}>{s.label}</span>;
}
