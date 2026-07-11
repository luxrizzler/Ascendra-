import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import Loader from "@/components/Loader";
import {
  ArrowLeft, Zap, Play, Pause, Plus, Trash2, RefreshCw, CheckCircle2,
  AlertTriangle, XCircle, Clock, Sparkles, Settings as SettingsIcon, Calendar, Send,
  RotateCw, Pencil, Ban,
} from "lucide-react";
import { toast } from "sonner";
import { formatDate } from "@/lib/utils";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";

const STATUS_COLORS = {
  pending: { bg: "rgba(124,58,237,0.15)", color: "#BFB4FF", label: "PENDING" },
  published: { bg: "rgba(52,211,153,0.15)", color: "#34D399", label: "PUBLISHED" },
  needs_review: { bg: "rgba(255,176,0,0.15)", color: "#FFB000", label: "NEEDS REVIEW" },
  failed: { bg: "rgba(251,113,133,0.15)", color: "#FB7185", label: "FAILED" },
  drafted: { bg: "rgba(255,176,0,0.15)", color: "#FFB000", label: "DRAFTED" },
  skipped: { bg: "rgba(255,255,255,0.05)", color: "#C8C5E6", label: "SKIPPED" },
  rejected: { bg: "rgba(120,120,140,0.15)", color: "#9CA0B8", label: "REJECTED" },
};

const RUN_ICON = {
  published: { Icon: CheckCircle2, color: "#34D399" },
  drafted: { Icon: AlertTriangle, color: "#FFB000" },
  needs_review: { Icon: AlertTriangle, color: "#FFB000" },
  failed: { Icon: XCircle, color: "#FB7185" },
  skipped: { Icon: Clock, color: "#C8C5E6" },
};

export default function AdminAutoContent() {
  const nav = useNavigate();
  const [settings, setSettings] = useState(null);
  const [queue, setQueue] = useState([]);
  const [runs, setRuns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(null);

  const load = async () => {
    setLoading(true);
    try {
      const [s, q, r] = await Promise.all([
        api.get("/admin/auto/settings"),
        api.get("/admin/auto/queue?limit=200"),
        api.get("/admin/auto/runs?limit=30"),
      ]);
      setSettings(s);
      setQueue(q.items || []);
      setRuns(r.runs || []);
    } catch (e) {
      toast.error(e.message || "Could not load auto-content");
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { load(); }, []);

  const togglePaused = async () => {
    setBusy("pause");
    try {
      const next = !settings.paused;
      const s = await api.post("/admin/auto/settings", { paused: next });
      setSettings({ ...s, next_runs: settings.next_runs });
      toast.success(next ? "Auto-pilot paused" : "Auto-pilot resumed");
    } catch (e) {
      toast.error(e.message || "Could not update settings");
    } finally {
      setBusy(null);
    }
  };

  const toggleAutoPublish = async () => {
    setBusy("autopub");
    try {
      const next = !settings.auto_publish;
      const s = await api.post("/admin/auto/settings", { auto_publish: next });
      setSettings({ ...s, next_runs: settings.next_runs });
      toast.success(next ? "Auto-publish ON" : "Auto-publish OFF — content will be drafted only");
    } catch (e) {
      toast.error(e.message || "Could not update settings");
    } finally {
      setBusy(null);
    }
  };

  const runManual = async (kind) => {
    setBusy(kind);
    toast.info(`Running ${kind} — this can take 30–90 seconds (Claude is working)...`);
    try {
      const r = await api.post("/admin/auto/run", { kind });
      if (r.status === "published") {
        toast.success(`Published: ${r.topic || "(no topic)"}`);
      } else if (r.status === "drafted") {
        toast.success(`Drafted (flagged for review): ${r.topic || "(no topic)"}`);
      } else if (r.status === "skipped") {
        toast.info(`Skipped: ${r.reason}`);
      } else if (r.status === "failed") {
        toast.error(`Failed: ${r.error}`);
      } else {
        toast.success(`Run complete: ${r.status}`);
      }
      load();
    } catch (e) {
      toast.error(e.message || "Run failed");
    } finally {
      setBusy(null);
    }
  };

  const [addTopic, setAddTopic] = useState("");
  const [addKind, setAddKind] = useState("lesson");
  const [addLevel, setAddLevel] = useState("Beginner");
  const [adding, setAdding] = useState(false);
  const addToQueue = async () => {
    if (!addTopic.trim()) { toast.error("Topic required"); return; }
    setAdding(true);
    try {
      await api.post("/admin/auto/queue", { topic: addTopic.trim(), kind: addKind, level: addLevel });
      setAddTopic("");
      toast.success("Added to queue");
      load();
    } catch (e) {
      toast.error(e.message || "Add failed");
    } finally {
      setAdding(false);
    }
  };

  const removeFromQueue = async (id) => {
    if (!confirm("Remove from queue?")) return;
    try {
      await api.del(`/admin/auto/queue/${id}`);
      toast.success("Removed");
      load();
    } catch (e) {
      toast.error(e.message || "Remove failed");
    }
  };

  const [resolving, setResolving] = useState(false);
  const autoResolveAll = async () => {
    if (!confirm("Auto-publish every draft awaiting review and reset any failed items back to pending? This bypasses the quality gate for existing drafts.")) return;
    setResolving(true);
    try {
      const r = await api.post("/admin/auto/queue/auto-resolve");
      toast.success(`Auto-resolved: ${r.auto_published} published, ${r.reset_to_pending} reset to pending`);
      load();
    } catch (e) {
      toast.error(e.message || "Auto-resolve failed");
    } finally {
      setResolving(false);
    }
  };

  const publishFlagged = async (id, topic) => {
    if (!confirm(`Publish flagged draft "${topic}" anyway?\n\nThis will add it live even though it failed the quality gate.`)) return;
    try {
      const r = await api.post(`/admin/auto/queue/${id}/publish`, {});
      toast.success(`Published ${r.kind}`);
      load();
    } catch (e) {
      toast.error(e.message || "Publish failed");
    }
  };

  const regenerate = async (id, topic) => {
    if (!confirm(`Regenerate "${topic}" with Claude?\n\nThis will discard the previous attempt and run fresh AI generation. Up to ~90 seconds with auto-retry on rate-limits.`)) return;
    setBusy(`regen-${id}`);
    toast.info(`Regenerating "${topic}" — Claude is working...`);
    try {
      const r = await api.post(`/admin/auto/queue/${id}/regenerate`, {});
      const status = r.run?.status;
      if (status === "published") {
        toast.success(`Published! "${r.run?.topic || topic}"`);
      } else if (status === "drafted") {
        toast.success(`Drafted (flagged for review): "${r.run?.topic || topic}"`);
      } else if (status === "failed") {
        toast.error(`Regeneration failed: ${r.run?.error || "Unknown error"}`);
      } else {
        toast.info(`Regeneration complete: ${status || "see queue"}`);
      }
      load();
    } catch (e) {
      // Friendly message comes from backend now (server.py uses friendly_llm_error)
      const msg = e?.message || "Could not regenerate";
      if (/busy|wait|overloaded|hiccup/i.test(msg)) {
        toast.warning(msg);
      } else {
        toast.error(msg);
      }
      load();
    } finally {
      setBusy(null);
    }
  };

  const rejectItem = async (id, topic) => {
    const reason = prompt(`Reject "${topic}"?\n\nOptional: type a reason (or leave blank).`);
    if (reason === null) return; // user cancelled
    try {
      await api.post(`/admin/auto/queue/${id}/reject`, { reason: reason || null });
      toast.success("Rejected");
      load();
    } catch (e) {
      toast.error(e.message || "Reject failed");
    }
  };

  // ─── Edit-draft modal state ────────────────────────────────────────────
  const [editing, setEditing] = useState(null); // queue item or null
  const [editTitle, setEditTitle] = useState("");
  const [editBody, setEditBody] = useState("");
  const [editSaving, setEditSaving] = useState(false);

  const openEdit = (item) => {
    setEditing(item);
    setEditTitle(item.draft?.title || item.topic || "");
    // Flatten draft cards into editable text. We collapse multi-card lessons to one body field —
    // operator can re-split into cards by clicking "Regenerate" instead if they need full structure.
    const cards = item.draft?.cards || [];
    const flat = cards.map((c) => {
      const head = c.title ? `## ${c.title}\n` : "";
      return head + (c.body || "");
    }).join("\n\n");
    setEditBody(flat);
  };

  const saveEdit = async () => {
    if (!editing) return;
    setEditSaving(true);
    try {
      await api.patch(`/admin/auto/queue/${editing.id}/draft`, {
        title: editTitle,
        body_text: editBody,
      });
      toast.success("Draft updated. Click 'Publish anyway' to make it live.");
      setEditing(null);
      load();
    } catch (e) {
      toast.error(e.message || "Save failed");
    } finally {
      setEditSaving(false);
    }
  };

  if (loading) return <div className="max-w-6xl mx-auto px-5 py-20"><Loader /></div>;

  const pendingLessons = queue.filter((q) => q.status === "pending" && q.kind === "lesson").length;
  const pendingPaths = queue.filter((q) => q.status === "pending" && q.kind === "path").length;
  const needsReview = queue.filter((q) => q.status === "needs_review").length;

  return (
    <div className="max-w-7xl mx-auto px-5 sm:px-8 py-10" data-testid="admin-auto-content-page">
      <button onClick={() => nav("/admin")} className="flex items-center gap-1 text-sm text-[var(--asc-text-dim)] hover:text-white mb-3">
        <ArrowLeft size={14} /> Admin
      </button>
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="asc-kicker">Automation</div>
          <h1 className="asc-h2 text-4xl mt-1 flex items-center gap-3"><Zap size={28} className="text-[var(--asc-brand)]" /> Auto-Pilot</h1>
          <p className="text-[var(--asc-text-dim)] text-sm mt-2 max-w-2xl">A new lesson every weekday at 10am UTC. A full course every Monday at 10am UTC. Quality-graded by Claude. Auto-publishes if it passes.</p>
        </div>
        <div className="flex gap-2 flex-wrap">
          <button
            onClick={togglePaused}
            disabled={busy === "pause"}
            className={settings.paused ? "asc-btn-primary text-sm" : "asc-btn-secondary text-sm"}
            data-testid="auto-toggle-pause"
            style={settings.paused ? {} : { color: "#FB7185", borderColor: "rgba(251,113,133,0.5)" }}
          >
            {settings.paused ? <><Play size={14} /> Resume auto-pilot</> : <><Pause size={14} /> Pause auto-pilot</>}
          </button>
        </div>
      </div>

      {settings.paused && (
        <div className="asc-card p-4 mt-5 flex items-center gap-3" style={{ background: "rgba(251,113,133,0.08)", borderColor: "rgba(251,113,133,0.35)" }} data-testid="auto-paused-banner">
          <AlertTriangle size={18} color="#FB7185" />
          <div className="text-sm"><strong>Auto-pilot is paused.</strong> Scheduled jobs will run but skip immediately. Resume to start shipping again.</div>
        </div>
      )}

      {/* Stats */}
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 mt-6">
        <Stat icon={Calendar} label="Pending lessons" value={pendingLessons} hint="Drains 1/day" color="#FFB000" testId="auto-stat-pending-lessons" />
        <Stat icon={Sparkles} label="Pending paths" value={pendingPaths} hint="Drains 1/Monday" color="#BFB4FF" testId="auto-stat-pending-paths" />
        <Stat icon={AlertTriangle} label="Needs review" value={needsReview} hint="Failed quality gate" color="#FB7185" testId="auto-stat-needs-review" />
        <div className="asc-card p-5">
          <div className="asc-label flex items-center gap-2"><SettingsIcon size={12} /> Quick controls</div>
          <div className="mt-3 space-y-2 text-sm">
            <label className="flex items-center gap-2" data-testid="auto-autopublish-toggle">
              <input type="checkbox" checked={settings.auto_publish} onChange={toggleAutoPublish} disabled={busy === "autopub"} />
              <span>Auto-publish if grade ≥ {settings.quality_threshold}</span>
            </label>
            <div className="text-xs text-[var(--asc-text-muted)]">Otherwise, content stays as draft for your review.</div>
          </div>
        </div>
      </div>

      {/* Next runs */}
      {settings.next_runs && (
        <div className="asc-card p-5 mt-6">
          <div className="asc-kicker flex items-center gap-2"><Clock size={12} /> Next scheduled runs (UTC)</div>
          <div className="grid sm:grid-cols-3 gap-3 mt-3">
            <NextRun label="Daily lesson" when={settings.next_runs.daily_lesson} />
            <NextRun label="Monday course" when={settings.next_runs.monday_path} />
            <NextRun label="Daily digest email" when={settings.next_runs.daily_digest} />
          </div>
          <div className="flex flex-wrap gap-2 mt-4">
            <button onClick={() => runManual("daily_lesson")} disabled={busy === "daily_lesson"} className="asc-btn-secondary text-xs" data-testid="auto-run-lesson-now-btn">
              <Play size={12} /> {busy === "daily_lesson" ? "Running…" : "Run a lesson now"}
            </button>
            <button onClick={() => runManual("monday_path")} disabled={busy === "monday_path"} className="asc-btn-secondary text-xs" data-testid="auto-run-path-now-btn">
              <Play size={12} /> {busy === "monday_path" ? "Running…" : "Run a course now"}
            </button>
            <button onClick={() => runManual("digest")} disabled={busy === "digest"} className="asc-btn-secondary text-xs" data-testid="auto-send-digest-now-btn">
              <Send size={12} /> {busy === "digest" ? "Sending…" : "Send digest now"}
            </button>
            <button onClick={load} className="asc-btn-secondary text-xs ml-auto" data-testid="auto-refresh-btn"><RefreshCw size={12} /> Refresh</button>
          </div>
        </div>
      )}

      <div className="grid lg:grid-cols-5 gap-6 mt-8">
        {/* Queue */}
        <section className="lg:col-span-3">
          <h2 className="asc-h2 text-2xl mb-3">Content queue ({queue.length})</h2>
          <div className="asc-card p-4 mb-3">
            <div className="asc-label mb-2">Add to queue</div>
            <div className="flex flex-wrap gap-2">
              <input className="asc-input text-sm flex-1 min-w-[200px]" placeholder="Topic…" value={addTopic} onChange={(e) => setAddTopic(e.target.value)} onKeyDown={(e) => e.key === "Enter" && addToQueue()} data-testid="auto-queue-topic-input" />
              <select className="asc-input text-sm" value={addKind} onChange={(e) => setAddKind(e.target.value)} data-testid="auto-queue-kind-select">
                <option value="lesson">Lesson</option>
                <option value="path">Full course</option>
              </select>
              <select className="asc-input text-sm" value={addLevel} onChange={(e) => setAddLevel(e.target.value)} data-testid="auto-queue-level-select">
                <option>Beginner</option><option>Intermediate</option><option>Advanced</option>
              </select>
              <button onClick={addToQueue} disabled={adding} className="asc-btn-primary text-sm" data-testid="auto-queue-add-btn"><Plus size={14} /> Add</button>
              <button onClick={autoResolveAll} disabled={resolving} className="asc-btn-secondary text-sm" data-testid="auto-queue-resolve-all-btn" title="Auto-publish all 'needs review' drafts + reset failed items to pending">
                {resolving ? "Resolving…" : (<><Zap size={14} /> Auto-resolve all</>)}
              </button>
            </div>
          </div>
          <div className="space-y-2 max-h-[600px] overflow-y-auto pr-1" data-testid="auto-queue-list">
            {queue.length === 0 ? (
              <div className="asc-card p-6 text-center text-sm text-[var(--asc-text-dim)]">Queue empty.</div>
            ) : queue.map((q) => {
              const canRegen = ["failed", "needs_review", "rejected"].includes(q.status);
              const canEdit = q.status === "needs_review" && !!q.draft;
              const canPublishFromReview = q.status === "needs_review" && !!q.draft;
              const isRegenBusy = busy === `regen-${q.id}`;
              return (
              <div key={q.id} className="asc-card p-3 flex items-center gap-3 flex-wrap" data-testid={`auto-queue-item-${q.id}`}>
                <StatusPill status={q.status} />
                <div className="flex-1 min-w-0">
                  <div className="font-bold text-sm truncate">{q.topic}</div>
                  <div className="text-xs text-[var(--asc-text-muted)]">
                    {q.kind} · {q.level || "Beginner"}{q.model_hint ? ` · ${q.model_hint}` : ""}
                    {q.regen_count ? ` · regenerated ${q.regen_count}×` : ""}
                  </div>
                  {q.error && (
                    <div className="text-[11px] text-[#FB7185] mt-1 truncate" title={q.error}>
                      Error: {q.error}
                    </div>
                  )}
                  {q.reject_reason && (
                    <div className="text-[11px] text-[#9CA0B8] mt-1 truncate" title={q.reject_reason}>
                      Rejected: {q.reject_reason}
                    </div>
                  )}
                </div>
                {q.grades && (
                  <div className="text-[10px] text-[var(--asc-text-muted)] asc-mono shrink-0" title={JSON.stringify(q.grades)}>
                    {q.grades.accuracy}/{q.grades.clarity}/{q.grades.brand_fit}/{q.grades.depth}
                  </div>
                )}
                <div className="flex flex-wrap gap-1.5 shrink-0">
                  {canRegen && (
                    <button
                      onClick={() => regenerate(q.id, q.topic)}
                      disabled={isRegenBusy}
                      className="asc-btn-secondary text-xs"
                      data-testid={`auto-queue-regenerate-${q.id}`}
                      title="Re-run AI generation (~30–90s)"
                      style={{ color: "#BFB4FF", borderColor: "rgba(191,180,255,0.45)" }}
                    >
                      <RotateCw size={12} className={isRegenBusy ? "animate-spin" : ""} />
                      {isRegenBusy ? "Regenerating…" : "Regenerate"}
                    </button>
                  )}
                  {canEdit && (
                    <button
                      onClick={() => openEdit(q)}
                      className="asc-btn-secondary text-xs"
                      data-testid={`auto-queue-edit-${q.id}`}
                      title="Edit draft before publishing"
                      style={{ color: "#FFB000", borderColor: "rgba(255,176,0,0.45)" }}
                    >
                      <Pencil size={12} /> Edit
                    </button>
                  )}
                  {canPublishFromReview && (
                    <button
                      onClick={() => publishFlagged(q.id, q.topic)}
                      className="asc-btn-secondary text-xs"
                      data-testid={`auto-queue-publish-${q.id}`}
                      style={{ color: "#34D399", borderColor: "rgba(52,211,153,0.5)" }}
                    >
                      <CheckCircle2 size={12} /> Publish
                    </button>
                  )}
                  {q.status === "pending" && (
                    <button
                      onClick={() => removeFromQueue(q.id)}
                      className="text-[var(--asc-text-muted)] hover:text-[#FB7185] p-1.5 rounded-md hover:bg-[rgba(251,113,133,0.1)]"
                      data-testid={`auto-queue-remove-${q.id}`}
                      title="Delete (pending items only)"
                    >
                      <Trash2 size={14} />
                    </button>
                  )}
                  {q.status !== "pending" && q.status !== "published" && q.status !== "rejected" && (
                    <button
                      onClick={() => rejectItem(q.id, q.topic)}
                      className="asc-btn-secondary text-xs"
                      data-testid={`auto-queue-reject-${q.id}`}
                      title="Reject and remove from active queue"
                      style={{ color: "#9CA0B8", borderColor: "rgba(156,160,184,0.4)" }}
                    >
                      <Ban size={12} /> Reject
                    </button>
                  )}
                </div>
              </div>
              );
            })}
          </div>
        </section>

        {/* Runs */}
        <section className="lg:col-span-2">
          <h2 className="asc-h2 text-2xl mb-3">Recent runs ({runs.length})</h2>
          <div className="space-y-2 max-h-[700px] overflow-y-auto pr-1" data-testid="auto-runs-list">
            {runs.length === 0 ? (
              <div className="asc-card p-6 text-center text-sm text-[var(--asc-text-dim)]">No runs yet. Trigger one above.</div>
            ) : runs.map((r) => {
              const { Icon, color } = RUN_ICON[r.status] || { Icon: Clock, color: "#C8C5E6" };
              return (
                <div key={r.id} className="asc-card p-3" data-testid={`auto-run-${r.id}`}>
                  <div className="flex items-start gap-2">
                    <Icon size={14} color={color} className="mt-0.5 shrink-0" />
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-bold">{r.kind === "monday_path" ? "Course" : r.kind === "daily_lesson" ? "Lesson" : "Digest"} · {(r.status || "").toUpperCase()}</div>
                      <div className="text-xs text-[var(--asc-text-dim)] truncate">{r.summary?.topic || r.summary?.reason || ""}</div>
                      <div className="text-[10px] text-[var(--asc-text-muted)] mt-0.5 asc-mono">{formatDate(r.created_at)}</div>
                      {r.summary?.grades && (
                        <div className="text-[10px] text-[var(--asc-text-muted)] mt-1">acc {r.summary.grades.accuracy} · cl {r.summary.grades.clarity} · br {r.summary.grades.brand_fit} · dp {r.summary.grades.depth}</div>
                      )}
                      {r.summary?.error && (
                        <div className="text-[10px] text-[#FB7185] mt-1 truncate">{r.summary.error}</div>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      </div>

      {/* Edit-draft modal */}
      <Dialog open={!!editing} onOpenChange={(open) => !open && setEditing(null)}>
        <DialogContent className="max-w-2xl" data-testid="auto-edit-draft-modal">
          <DialogHeader>
            <DialogTitle className="text-xl">Edit draft</DialogTitle>
            <DialogDescription>
              Adjust the title or rewrite the lesson body. After saving, click <strong>Publish</strong> on the queue row to make it live.
              <br />
              <span className="text-xs text-[var(--asc-text-muted)]">
                Note: interactive cards (quizzes, fill-in-blanks, playgrounds) will be auto-generated by the next sweep after publish.
              </span>
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 mt-2">
            <div>
              <label className="asc-label">Title</label>
              <Input
                value={editTitle}
                onChange={(e) => setEditTitle(e.target.value)}
                className="asc-input mt-1"
                data-testid="auto-edit-title-input"
                maxLength={200}
              />
            </div>
            <div>
              <label className="asc-label">Body</label>
              <Textarea
                value={editBody}
                onChange={(e) => setEditBody(e.target.value)}
                className="asc-input mt-1 font-mono text-sm"
                style={{ minHeight: 280 }}
                data-testid="auto-edit-body-input"
                maxLength={8000}
                placeholder="Write the lesson body. Use ## Heading lines for sections."
              />
              <div className="text-xs text-[var(--asc-text-muted)] mt-1 text-right">
                {editBody.length}/8000
              </div>
            </div>
          </div>
          <DialogFooter className="gap-2">
            <Button
              variant="outline"
              onClick={() => setEditing(null)}
              data-testid="auto-edit-cancel-btn"
            >
              Cancel
            </Button>
            <Button
              onClick={saveEdit}
              disabled={editSaving || !editTitle.trim()}
              data-testid="auto-edit-save-btn"
              className="asc-btn-primary"
            >
              {editSaving ? "Saving…" : "Save draft"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function Stat({ icon: Icon, label, value, hint, color, testId }) {
  return (
    <div className="asc-card p-5" data-testid={testId}>
      <div className="flex items-start gap-3">
        <div className="w-10 h-10 rounded-xl grid place-items-center" style={{ background: `${color}22`, border: `1px solid ${color}55` }}><Icon size={18} color={color} /></div>
        <div className="flex-1">
          <div className="asc-label">{label}</div>
          <div className="asc-h2 text-2xl mt-1">{value}</div>
          <div className="text-xs text-[var(--asc-text-muted)] mt-0.5">{hint}</div>
        </div>
      </div>
    </div>
  );
}

function NextRun({ label, when }) {
  if (!when) return <div className="text-sm text-[var(--asc-text-muted)]">{label}: <span className="asc-mono">—</span></div>;
  const date = new Date(when);
  const fmt = date.toLocaleString("en-US", { month: "short", day: "numeric", hour: "numeric", minute: "2-digit", timeZone: "UTC" });
  return (
    <div className="asc-card p-3" style={{ background: "#0A0413" }}>
      <div className="text-xs text-[var(--asc-text-muted)] uppercase tracking-wider">{label}</div>
      <div className="asc-mono text-sm mt-1">{fmt} UTC</div>
    </div>
  );
}

function StatusPill({ status }) {
  const p = STATUS_COLORS[status] || STATUS_COLORS.pending;
  return <span className="px-2 py-0.5 rounded-full text-[10px] font-black tracking-wider shrink-0" style={{ background: p.bg, color: p.color }}>{p.label}</span>;
}
