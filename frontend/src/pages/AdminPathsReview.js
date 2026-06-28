import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import Loader from "@/components/Loader";
import {
  ArrowLeft, Sparkles, CheckCircle2, XCircle, Clock4, BookOpen, User, ExternalLink,
} from "lucide-react";
import { toast } from "sonner";
import { formatDate } from "@/lib/utils";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";

const TIERS = ["ascender", "pathfinder", "sage"];

export default function AdminPathsReview() {
  const nav = useNavigate();
  const [pending, setPending] = useState([]);
  const [loading, setLoading] = useState(true);

  const [reviewing, setReviewing] = useState(null);     // path being reviewed
  const [reviewMode, setReviewMode] = useState(null);   // "approve" | "reject"
  const [reviewNotes, setReviewNotes] = useState("");
  const [reviewTier, setReviewTier] = useState("ascender");
  const [busy, setBusy] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const r = await api.get("/admin/paths/pending-review");
      setPending(r.paths || []);
    } catch (e) {
      toast.error(e.message || "Could not load pending paths");
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { load(); }, []);

  const openReview = (path, mode) => {
    setReviewing(path);
    setReviewMode(mode);
    setReviewNotes("");
    setReviewTier(path.tier && TIERS.includes(path.tier) ? path.tier : "ascender");
  };

  const submitReview = async () => {
    if (!reviewing) return;
    setBusy(true);
    try {
      const body = { notes: reviewNotes || null };
      if (reviewMode === "approve") {
        body.new_tier = reviewTier;
        await api.post(`/admin/paths/${reviewing.id}/approve`, body);
        toast.success(`Approved: "${reviewing.title}" — now public for ${reviewTier} tier and above.`);
      } else {
        await api.post(`/admin/paths/${reviewing.id}/reject`, body);
        toast.success(`Rejected: "${reviewing.title}". Creator keeps private access.`);
      }
      setReviewing(null);
      load();
    } catch (e) {
      toast.error(e.message || "Review failed");
    } finally {
      setBusy(false);
    }
  };

  if (loading) return <div className="max-w-6xl mx-auto px-5 py-20"><Loader /></div>;

  return (
    <div className="max-w-7xl mx-auto px-5 sm:px-8 py-10" data-testid="admin-paths-review-page">
      <button onClick={() => nav("/admin")} className="flex items-center gap-1 text-sm text-[var(--asc-text-dim)] hover:text-white mb-3">
        <ArrowLeft size={14} /> Admin
      </button>
      <div className="flex items-end justify-between gap-3 flex-wrap">
        <div>
          <div className="asc-kicker">Path review</div>
          <h1 className="asc-h2 text-4xl mt-1 flex items-center gap-3">
            <Sparkles size={28} className="text-[var(--asc-brand)]" /> User-generated paths
          </h1>
          <p className="text-[var(--asc-text-dim)] text-sm mt-2 max-w-2xl">
            Approve to make public for the chosen tier + everyone above. Reject keeps the path private to the creator only.
          </p>
        </div>
        <div className="asc-card px-5 py-3 flex items-center gap-3" data-testid="pending-count-card">
          <Clock4 size={20} className="text-[#FFB000]" />
          <div>
            <div className="asc-label">Pending review</div>
            <div className="asc-h2 text-2xl">{pending.length}</div>
          </div>
        </div>
      </div>

      {pending.length === 0 ? (
        <div className="asc-card p-10 text-center mt-8" data-testid="no-pending-empty">
          <CheckCircle2 size={36} className="mx-auto text-[#34D399]" />
          <div className="text-lg font-bold mt-3">All caught up</div>
          <div className="text-sm text-[var(--asc-text-dim)] mt-1">No user-generated paths awaiting review.</div>
        </div>
      ) : (
        <div className="grid lg:grid-cols-2 gap-5 mt-8">
          {pending.map((p) => (
            <PathReviewCard
              key={p.id}
              path={p}
              onApprove={() => openReview(p, "approve")}
              onReject={() => openReview(p, "reject")}
            />
          ))}
        </div>
      )}

      {/* Approve/Reject dialog */}
      <Dialog open={!!reviewing} onOpenChange={(open) => !open && setReviewing(null)}>
        <DialogContent data-testid="review-modal">
          <DialogHeader>
            <DialogTitle className="text-xl">
              {reviewMode === "approve" ? "Approve path" : "Reject path"}: {reviewing?.title}
            </DialogTitle>
            <DialogDescription>
              {reviewMode === "approve" ? (
                <>Making this public will let everyone at the selected tier <strong>and above</strong> see and start this path.</>
              ) : (
                <>The path stays private to the creator. Add a short note so they understand what to improve (optional).</>
              )}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 mt-2">
            {reviewMode === "approve" && (
              <div>
                <label className="asc-label">Available from tier</label>
                <Select value={reviewTier} onValueChange={setReviewTier}>
                  <SelectTrigger className="asc-input mt-1" data-testid="review-tier-select">
                    <SelectValue placeholder="Choose tier" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="ascender">Ascender (and above)</SelectItem>
                    <SelectItem value="pathfinder">Pathfinder (and above)</SelectItem>
                    <SelectItem value="sage">Sage only</SelectItem>
                  </SelectContent>
                </Select>
                <div className="text-xs text-[var(--asc-text-muted)] mt-1">
                  Pathfinder users see Ascender + Pathfinder paths. Sage users see all.
                </div>
              </div>
            )}
            <div>
              <label className="asc-label">Notes {reviewMode === "approve" ? "(internal)" : "(visible to creator)"}</label>
              <Textarea
                value={reviewNotes}
                onChange={(e) => setReviewNotes(e.target.value)}
                className="asc-input mt-1"
                style={{ minHeight: 100 }}
                maxLength={500}
                placeholder={reviewMode === "approve" ? "Why this is a great fit (internal log)…" : "Suggest what would make this approval-ready…"}
                data-testid="review-notes-input"
              />
              <div className="text-xs text-[var(--asc-text-muted)] mt-1 text-right">{reviewNotes.length}/500</div>
            </div>
          </div>
          <DialogFooter className="gap-2">
            <Button variant="outline" onClick={() => setReviewing(null)} data-testid="review-cancel-btn">Cancel</Button>
            <Button
              onClick={submitReview}
              disabled={busy}
              className={reviewMode === "approve" ? "asc-btn-primary" : ""}
              style={reviewMode === "reject" ? { background: "#FB7185", color: "#000" } : {}}
              data-testid="review-submit-btn"
            >
              {busy ? "Saving…" : reviewMode === "approve" ? "Approve & publish" : "Reject"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}


function PathReviewCard({ path, onApprove, onReject }) {
  return (
    <div className="asc-card p-5" data-testid={`path-review-card-${path.id}`}>
      <div className="flex items-start gap-3">
        <div className="w-12 h-12 rounded-xl grid place-items-center shrink-0"
              style={{ background: `${path.color}22`, border: `1px solid ${path.color}55` }}>
          <Sparkles size={20} color={path.color} />
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="asc-h2 text-lg leading-tight">{path.title}</h3>
          <p className="text-sm text-[var(--asc-text-dim)] mt-1 line-clamp-2">{path.tagline}</p>
          <div className="flex flex-wrap gap-3 mt-3 text-xs text-[var(--asc-text-muted)]">
            <span className="flex items-center gap-1"><BookOpen size={12} /> {path.total_lessons} lessons</span>
            <span className="flex items-center gap-1"><User size={12} /> {path.creator_email || "unknown"}</span>
            <span className="asc-mono">{path.created_at ? formatDate(path.created_at) : ""}</span>
          </div>
        </div>
      </div>
      <div className="flex flex-wrap gap-2 mt-4">
        <a
          href={`/paths/${path.id}`}
          target="_blank"
          rel="noreferrer"
          className="asc-btn-secondary text-xs"
          data-testid={`path-review-preview-${path.id}`}
        >
          <ExternalLink size={12} /> Preview
        </a>
        <button
          onClick={onApprove}
          className="asc-btn-secondary text-xs"
          style={{ color: "#34D399", borderColor: "rgba(52,211,153,0.5)" }}
          data-testid={`path-review-approve-${path.id}`}
        >
          <CheckCircle2 size={12} /> Approve
        </button>
        <button
          onClick={onReject}
          className="asc-btn-secondary text-xs"
          style={{ color: "#FB7185", borderColor: "rgba(251,113,133,0.5)" }}
          data-testid={`path-review-reject-${path.id}`}
        >
          <XCircle size={12} /> Reject
        </button>
      </div>
    </div>
  );
}
