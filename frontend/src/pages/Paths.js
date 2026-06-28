import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import Loader from "@/components/Loader";
import TierBadge from "@/components/TierBadge";
import {
  Lock, ArrowRight, BookOpen, Clock, Zap, Sparkles, Plus, Clock4, CheckCircle2, XCircle,
} from "lucide-react";
import { canAccess } from "@/lib/utils";
import { toast } from "sonner";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

export default function Paths() {
  const { user } = useAuth();
  const nav = useNavigate();
  const [paths, setPaths] = useState([]);
  const [myPaths, setMyPaths] = useState([]);
  const [progress, setProgress] = useState(null);
  const [loading, setLoading] = useState(true);

  // Generation modal state
  const [genOpen, setGenOpen] = useState(false);
  const [genGoal, setGenGoal] = useState("");
  const [generating, setGenerating] = useState(false);

  const loadAll = async () => {
    try {
      const [ps, pr, mine] = await Promise.all([
        api.get("/paths"),
        api.get("/progress"),
        user ? api.get("/paths/mine").catch(() => ({ paths: [] })) : Promise.resolve({ paths: [] }),
      ]);
      setPaths(ps.paths || []);
      setMyPaths(mine.paths || []);
      setProgress(pr);
    } catch (e) {
      toast.error(e.message || "Could not load paths");
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { loadAll(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const isPaid = user && user.tier && user.tier !== "free";

  const handleGenerate = async () => {
    if (!isPaid) {
      toast.info("Custom path generation requires a paid plan. Upgrade to Ascender or higher.");
      nav("/pricing");
      return;
    }
    const goal = genGoal.trim();
    if (goal.length < 8) {
      toast.error("Please describe your goal in a bit more detail.");
      return;
    }
    setGenerating(true);
    try {
      toast.info("Drafting your custom path with Claude — this takes 10-20 seconds...");
      const res = await api.post("/paths/generate", { goal, fill_lessons: true });
      toast.success("Path created! Lessons are being filled in the background. Head in to start the first one.");
      setGenOpen(false);
      setGenGoal("");
      await loadAll();
      // Route to the new path
      if (res?.path?.id) {
        nav(`/paths/${res.path.id}`);
      }
    } catch (e) {
      const msg = e?.message || "Could not generate path";
      if (/paid feature/i.test(msg)) {
        toast.error("Custom path generation is a paid feature. Upgrade to continue.");
        nav("/pricing");
      } else if (/wait/i.test(msg)) {
        toast.warning(msg);
      } else {
        toast.error(msg);
      }
    } finally {
      setGenerating(false);
    }
  };

  if (loading) return <Loader />;

  // Filter myPaths to only show ones not also in the public catalog (avoid duplication).
  const publicIds = new Set(paths.map((p) => p.id));
  const onlyMine = myPaths.filter((p) => !publicIds.has(p.id));

  return (
    <div className="max-w-7xl mx-auto px-5 sm:px-8 py-10" data-testid="paths-page">
      <div className="flex items-end justify-between gap-3 flex-wrap">
        <div>
          <div className="asc-kicker">All paths</div>
          <h1 className="asc-h2 text-4xl sm:text-5xl mt-2">Choose your ascent.</h1>
          <p className="text-[var(--asc-text-dim)] mt-2 max-w-2xl">
            Curated paths covering every facet of AI in 2026 — or generate your own custom path tailored to your exact goal.
          </p>
        </div>
        <Button
          onClick={() => setGenOpen(true)}
          className="asc-btn-primary"
          data-testid="create-custom-path-btn"
          style={{ background: "linear-gradient(135deg, #FFB000, #FF6B35)" }}
        >
          <Sparkles size={16} className="mr-1" />
          {isPaid ? "Create your own path" : "Upgrade to create paths"}
        </Button>
      </div>

      {/* My custom paths */}
      {onlyMine.length > 0 && (
        <section className="mt-8" data-testid="my-paths-section">
          <h2 className="asc-h2 text-2xl flex items-center gap-2">
            <Sparkles size={22} className="text-[var(--asc-brand)]" /> Your custom paths
          </h2>
          <p className="text-sm text-[var(--asc-text-dim)] mt-1">
            Paths you generated. Pending admin review will become public after approval.
          </p>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-5 mt-4">
            {onlyMine.map((p) => (
              <UserPathCard key={p.id} path={p} progress={progress} />
            ))}
          </div>
        </section>
      )}

      {/* Public catalog */}
      <section className="mt-10">
        <h2 className="asc-h2 text-2xl">Curated catalog</h2>
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-5 mt-4">
          {paths.map((p) => {
            const pr = (progress && progress.path_progress[p.id]) || { completed: 0, total: p.total_lessons, pct: 0 };
            const locked = !canAccess(user, p.tier);
            return (
              <Link
                key={p.id}
                to={`/paths/${p.id}`}
                data-testid={`path-card-${p.id}`}
                className="asc-card overflow-hidden relative"
              >
                <div className="relative h-40">
                  <img src={p.image} alt={p.title} className="absolute inset-0 w-full h-full object-cover" />
                  <div className="absolute inset-0" style={{ background: `linear-gradient(135deg, ${p.color}55, rgba(10,4,19,0.85))` }} />
                  <div className="absolute top-3 left-3 flex gap-2">
                    <span className="px-2 py-1 rounded-full text-[10px] font-black tracking-wider" style={{ background: p.color, color: "#000" }}>{p.level}</span>
                    {p.tier !== "free" && <TierBadge tier={p.tier} />}
                  </div>
                  {locked && (
                    <div className="absolute inset-0 grid place-items-center backdrop-blur-sm" style={{ background: "rgba(10,4,19,0.55)" }}>
                      <Lock size={28} className="text-white" />
                    </div>
                  )}
                </div>
                <div className="p-5">
                  <div className="asc-label" style={{ color: p.color }}>{p.subtitle}</div>
                  <h3 className="asc-h2 text-xl mt-2">{p.title}</h3>
                  <p className="text-[var(--asc-text-dim)] text-sm mt-2 line-clamp-2">{p.tagline}</p>

                  <div className="flex gap-3 mt-4 text-xs text-[var(--asc-text-muted)]">
                    <span className="flex items-center gap-1"><BookOpen size={12} /> {p.total_lessons}</span>
                    <span className="flex items-center gap-1"><Clock size={12} /> {p.duration}</span>
                    <span className="flex items-center gap-1"><Zap size={12} /> {p.total_xp} XP</span>
                  </div>

                  <div className="h-1.5 mt-4 rounded-full overflow-hidden" style={{ background: "rgba(191,180,255,0.1)" }}>
                    <div className="h-full" style={{ width: `${pr.pct}%`, background: p.color }} />
                  </div>
                  <div className="flex items-center justify-between mt-3">
                    <span className="text-xs text-[var(--asc-text-dim)]">{pr.completed} / {pr.total}</span>
                    <span className="flex items-center gap-1 text-sm text-[var(--asc-brand)] font-bold">{locked ? "Upgrade" : pr.completed === 0 ? "Start" : pr.pct === 100 ? "Review" : "Continue"} <ArrowRight size={14} /></span>
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
      </section>

      {/* Generation modal */}
      <Dialog open={genOpen} onOpenChange={setGenOpen}>
        <DialogContent className="max-w-xl" data-testid="create-path-modal">
          <DialogHeader>
            <DialogTitle className="text-2xl flex items-center gap-2">
              <Sparkles size={22} className="text-[var(--asc-brand)]" /> Create your own path
            </DialogTitle>
            <DialogDescription>
              Describe the AI skill or outcome you want to master. Claude will design a complete 3-level path
              (Beginner → Intermediate → Advanced) tailored to your goal.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3 mt-3">
            <label className="asc-label">Your goal</label>
            <Textarea
              value={genGoal}
              onChange={(e) => setGenGoal(e.target.value)}
              className="asc-input"
              style={{ minHeight: 140 }}
              placeholder="e.g. I want to use AI to grow my Etsy shop — research products, write listings, generate cover photos, and automate customer replies."
              maxLength={2000}
              data-testid="create-path-goal-input"
            />
            <div className="text-xs text-[var(--asc-text-muted)] text-right">{genGoal.length}/2000</div>
            <div className="text-xs text-[var(--asc-text-muted)] flex items-start gap-2">
              <Clock4 size={12} className="mt-0.5 shrink-0" />
              <span>Takes ~15-20 seconds for the outline. Lesson content fills in over the next minute or two — you can start the first lesson as soon as it&apos;s ready.</span>
            </div>
            {!isPaid && (
              <div className="asc-card p-3 text-sm" style={{ background: "rgba(255,176,0,0.08)", borderColor: "rgba(255,176,0,0.45)" }}>
                <strong className="text-[var(--asc-brand)]">Paid feature.</strong> Upgrade to Ascender or higher to generate unlimited custom paths.
              </div>
            )}
          </div>
          <DialogFooter className="gap-2">
            <Button variant="outline" onClick={() => setGenOpen(false)} data-testid="create-path-cancel-btn">
              Cancel
            </Button>
            <Button
              onClick={handleGenerate}
              disabled={generating || genGoal.trim().length < 8}
              className="asc-btn-primary"
              data-testid="create-path-submit-btn"
            >
              {generating ? "Generating…" : isPaid ? "Generate path" : "Upgrade & generate"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}


function UserPathCard({ path, progress }) {
  const pr = (progress && progress.path_progress[path.id]) || { completed: 0, total: path.total_lessons, pct: 0 };
  const statusBadge = statusBadgeFor(path);
  return (
    <Link
      to={`/paths/${path.id}`}
      data-testid={`my-path-card-${path.id}`}
      className="asc-card overflow-hidden relative"
    >
      <div className="relative h-32" style={{ background: `linear-gradient(135deg, ${path.color}88, rgba(10,4,19,0.9))` }}>
        <div className="absolute top-3 left-3 flex gap-2 flex-wrap">
          <span className="px-2 py-1 rounded-full text-[10px] font-black tracking-wider" style={{ background: path.color, color: "#000" }}>
            {path.level || "Mixed"}
          </span>
          <span className="px-2 py-1 rounded-full text-[10px] font-black tracking-wider"
                 style={{ background: "rgba(191,180,255,0.2)", color: "#BFB4FF" }}>
            CUSTOM
          </span>
          {statusBadge}
        </div>
        <div className="absolute bottom-3 right-3">
          <Sparkles size={28} className="text-white/80" />
        </div>
      </div>
      <div className="p-5">
        <h3 className="asc-h2 text-xl">{path.title}</h3>
        <p className="text-[var(--asc-text-dim)] text-sm mt-2 line-clamp-2">{path.tagline}</p>
        <div className="flex gap-3 mt-4 text-xs text-[var(--asc-text-muted)]">
          <span className="flex items-center gap-1"><BookOpen size={12} /> {path.total_lessons}</span>
          <span className="flex items-center gap-1"><Clock size={12} /> {path.duration}</span>
        </div>
        <div className="h-1.5 mt-4 rounded-full overflow-hidden" style={{ background: "rgba(191,180,255,0.1)" }}>
          <div className="h-full" style={{ width: `${pr.pct}%`, background: path.color }} />
        </div>
        <div className="flex items-center justify-between mt-3">
          <span className="text-xs text-[var(--asc-text-dim)]">{pr.completed} / {pr.total}</span>
          <span className="flex items-center gap-1 text-sm text-[var(--asc-brand)] font-bold">
            {pr.completed === 0 ? "Start" : pr.pct === 100 ? "Review" : "Continue"} <ArrowRight size={14} />
          </span>
        </div>
      </div>
    </Link>
  );
}


function statusBadgeFor(path) {
  const v = path.visibility;
  const review = path.admin_review_status;
  if (v === "public" || review === "approved") {
    return (
      <span className="px-2 py-1 rounded-full text-[10px] font-black tracking-wider flex items-center gap-1"
             style={{ background: "rgba(52,211,153,0.18)", color: "#34D399" }}
             data-testid={`path-status-${path.id}`}>
        <CheckCircle2 size={10} /> APPROVED
      </span>
    );
  }
  if (review === "rejected" || v === "rejected") {
    return (
      <span className="px-2 py-1 rounded-full text-[10px] font-black tracking-wider flex items-center gap-1"
             style={{ background: "rgba(251,113,133,0.18)", color: "#FB7185" }}
             data-testid={`path-status-${path.id}`}>
        <XCircle size={10} /> NEEDS WORK
      </span>
    );
  }
  // pending
  return (
    <span className="px-2 py-1 rounded-full text-[10px] font-black tracking-wider flex items-center gap-1"
           style={{ background: "rgba(255,176,0,0.18)", color: "#FFB000" }}
           data-testid={`path-status-${path.id}`}>
      <Clock4 size={10} /> PENDING REVIEW
    </span>
  );
}
