import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Trophy,
  Eye,
  EyeOff,
  Copy,
  Share2,
  ChevronDown,
  ChevronUp,
  Sparkles,
  CheckCircle2,
  ExternalLink,
} from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import SEO from "@/components/SEO";
import Loader from "@/components/Loader";

export default function Portfolio() {
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [items, setItems] = useState([]);
  const [publicCount, setPublicCount] = useState(0);
  const [expanded, setExpanded] = useState(null);
  const [toggling, setToggling] = useState(null);

  const load = async () => {
    setLoading(true);
    try {
      const r = await api.get("/practice/portfolio/mine");
      setItems(r.items || []);
      setPublicCount(r.public_count || 0);
    } catch (e) {
      toast.error(e.message || "Could not load portfolio");
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { load(); }, []);

  const togglePublic = async (attemptId) => {
    setToggling(attemptId);
    try {
      const r = await api.post(`/practice/portfolio/${attemptId}/toggle-public`);
      setItems((list) => list.map((it) => it.attempt_id === attemptId ? { ...it, is_public: r.is_public } : it));
      setPublicCount((n) => n + (r.is_public ? 1 : -1));
      toast.success(r.is_public ? "Now public — shareable" : "Made private");
    } catch (e) {
      toast.error(e.message || "Could not update");
    } finally {
      setToggling(null);
    }
  };

  const copyShareLink = () => {
    if (!user?.email) return;
    const url = `${window.location.origin}/portfolio/${encodeURIComponent(user.email)}`;
    navigator.clipboard?.writeText(url);
    toast.success("Public link copied!");
  };

  const copyAttemptText = (text) => {
    navigator.clipboard?.writeText(text);
    toast.success("Copied to clipboard");
  };

  return (
    <div className="min-h-screen" data-testid="portfolio-page">
      <SEO title="My Portfolio" description="Your mastered practice challenges on Ascendra Academy." path="/portfolio" noindex />

      {/* Hero */}
      <section className="px-6 pt-14 pb-8 border-b border-[var(--asc-border)]">
        <div className="max-w-6xl mx-auto">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-[var(--asc-border-strong)] mb-5" style={{ background: "rgba(255,176,0,0.08)" }}>
            <Trophy size={14} color="#FFB000" />
            <span className="asc-label">Your Practice Portfolio</span>
          </div>
          <div className="flex flex-wrap items-end justify-between gap-6">
            <div>
              <h1 className="asc-h1 text-4xl sm:text-5xl" data-testid="portfolio-heading">
                Your best work
              </h1>
              <p className="text-[var(--asc-text-dim)] mt-3 max-w-2xl leading-relaxed">
                Every practice challenge you&apos;ve mastered lives here. Items are private by default —
                toggle any one to public to share it, or share your full public showcase link.
              </p>
            </div>
            {items.length > 0 && (
              <div className="flex flex-wrap items-center gap-3">
                <div className="asc-card px-4 py-2.5" data-testid="portfolio-stats">
                  <div className="text-xs text-[var(--asc-text-muted)] tracking-wider">MASTERED</div>
                  <div className="text-2xl font-black text-white">{items.length}</div>
                </div>
                <div className="asc-card px-4 py-2.5">
                  <div className="text-xs text-[var(--asc-text-muted)] tracking-wider">PUBLIC</div>
                  <div className="text-2xl font-black" style={{ color: publicCount > 0 ? "#22c55e" : "#BFB4FF" }}>
                    {publicCount}
                  </div>
                </div>
                {publicCount > 0 && (
                  <button
                    onClick={copyShareLink}
                    className="asc-btn-primary"
                    data-testid="portfolio-share-btn"
                  >
                    <Share2 size={14} /> Share public link
                  </button>
                )}
              </div>
            )}
          </div>
        </div>
      </section>

      {/* Body */}
      <section className="px-6 py-10">
        <div className="max-w-6xl mx-auto">
          {loading ? (
            <div className="py-16"><Loader /></div>
          ) : items.length === 0 ? (
            <EmptyState />
          ) : (
            <div className="grid gap-4">
              {items.map((it) => (
                <PortfolioItem
                  key={it.attempt_id}
                  item={it}
                  isExpanded={expanded === it.attempt_id}
                  isToggling={toggling === it.attempt_id}
                  onToggleExpand={() => setExpanded(expanded === it.attempt_id ? null : it.attempt_id)}
                  onTogglePublic={() => togglePublic(it.attempt_id)}
                  onCopy={() => copyAttemptText(it.attempt_text)}
                />
              ))}
            </div>
          )}
        </div>
      </section>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="asc-card p-10 text-center max-w-2xl mx-auto" data-testid="portfolio-empty">
      <div className="w-14 h-14 rounded-full mx-auto grid place-items-center" style={{ background: "rgba(255,176,0,0.15)" }}>
        <Trophy size={24} color="#FFB000" />
      </div>
      <h2 className="asc-h2 text-2xl mt-5">No masteries yet</h2>
      <p className="text-[var(--asc-text-dim)] mt-3 leading-relaxed">
        Complete a “Try It Live” practice challenge in any lesson with a score of 80 or higher
        and your best attempt lands here automatically. Ready to earn your first?
      </p>
      <Link to="/paths" className="asc-btn-primary mt-6 inline-flex" data-testid="portfolio-cta-browse">
        Browse learning paths <ExternalLink size={14} />
      </Link>
    </div>
  );
}

function PortfolioItem({ item, isExpanded, isToggling, onToggleExpand, onTogglePublic, onCopy }) {
  const dateStr = item.created_at ? new Date(item.created_at).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" }) : "";
  const scoreColor = item.score >= 90 ? "#22c55e" : "#FFB000";
  return (
    <div className="asc-card p-6" data-testid={`portfolio-item-${item.attempt_id}`}>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 text-xs text-[var(--asc-text-muted)] tracking-wider">
            <span>{dateStr}</span>
            {item.is_public && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold" style={{ background: "rgba(34,197,94,0.15)", color: "#22c55e" }}>
                <Eye size={9} /> PUBLIC
              </span>
            )}
          </div>
          <h3 className="asc-h2 text-xl sm:text-2xl mt-1">{item.challenge_title || "Practice challenge"}</h3>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2" title="Mastery score">
            <div className="text-xs text-[var(--asc-text-muted)]">SCORE</div>
            <div className="text-2xl font-black" style={{ color: scoreColor }} data-testid={`portfolio-score-${item.attempt_id}`}>
              {item.score}
            </div>
          </div>
          <button
            onClick={onTogglePublic}
            disabled={isToggling}
            data-testid={`portfolio-toggle-${item.attempt_id}`}
            className={`px-3 py-1.5 rounded-full text-xs font-bold border transition flex items-center gap-1.5 ${
              item.is_public
                ? "bg-[rgba(34,197,94,0.15)] border-[rgba(34,197,94,0.4)] text-[#22c55e] hover:bg-[rgba(34,197,94,0.22)]"
                : "bg-[rgba(191,180,255,0.05)] border-[var(--asc-border)] text-[var(--asc-text-dim)] hover:text-white"
            }`}
          >
            {isToggling ? "…" : item.is_public ? (<><Eye size={12} /> Public</>) : (<><EyeOff size={12} /> Private</>)}
          </button>
        </div>
      </div>

      {/* Preview of attempt (truncated) */}
      <div className="mt-4">
        <div
          className={`p-4 rounded-xl text-sm leading-relaxed whitespace-pre-wrap transition-all ${
            isExpanded ? "" : "max-h-32 overflow-hidden relative"
          }`}
          style={{ background: "rgba(191,180,255,0.04)", border: "1px solid rgba(191,180,255,0.12)" }}
        >
          <div className="text-[var(--asc-text-dim)]">{item.attempt_text}</div>
          {!isExpanded && item.attempt_text.length > 200 && (
            <div className="absolute inset-x-0 bottom-0 h-16 pointer-events-none" style={{ background: "linear-gradient(to bottom, transparent, #14092A)" }} />
          )}
        </div>

        {/* Expanded details */}
        {isExpanded && (
          <div className="mt-4 space-y-3">
            {item.strengths?.length > 0 && (
              <div className="p-3 rounded-lg text-sm" style={{ background: "rgba(34,197,94,0.06)", border: "1px solid rgba(34,197,94,0.2)" }}>
                <div className="asc-label mb-1.5" style={{ color: "#22c55e" }}>Strengths</div>
                <ul className="space-y-1 text-[var(--asc-text-dim)]">
                  {item.strengths.map((s, i) => (<li key={i} className="flex gap-2"><CheckCircle2 size={13} color="#22c55e" className="flex-shrink-0 mt-0.5" /><span>{s}</span></li>))}
                </ul>
              </div>
            )}
            {item.ai_response && (
              <div className="p-3 rounded-lg text-sm" style={{ background: "rgba(255,176,0,0.04)", border: "1px solid rgba(255,176,0,0.2)" }}>
                <div className="asc-label mb-1.5" style={{ color: "#FFB000" }}>What the AI produced</div>
                <div className="text-[var(--asc-text-dim)] whitespace-pre-wrap">{item.ai_response}</div>
              </div>
            )}
          </div>
        )}
      </div>

      <div className="mt-4 flex items-center justify-between gap-3 flex-wrap">
        <button onClick={onToggleExpand} className="text-xs text-[var(--asc-text-muted)] hover:text-white flex items-center gap-1 transition" data-testid={`portfolio-expand-${item.attempt_id}`}>
          {isExpanded ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
          {isExpanded ? "Show less" : "Show feedback"}
        </button>
        <div className="flex items-center gap-2">
          <button onClick={onCopy} className="text-xs text-[var(--asc-text-muted)] hover:text-white flex items-center gap-1 px-3 py-1.5 rounded-full border border-[var(--asc-border)]" data-testid={`portfolio-copy-${item.attempt_id}`}>
            <Copy size={12} /> Copy attempt
          </button>
          {item.lesson_id && (
            <Link to={`/lessons/${item.lesson_id}`} className="text-xs text-[var(--asc-brand)] hover:underline flex items-center gap-1">
              <Sparkles size={12} /> Revisit lesson
            </Link>
          )}
        </div>
      </div>
    </div>
  );
}
