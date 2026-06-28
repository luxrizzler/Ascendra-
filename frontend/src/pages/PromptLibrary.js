import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, BookOpen, Copy, Library, Search, Sparkles } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import Loader from "@/components/Loader";

export default function PromptLibrary() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState("");
  const [path, setPath] = useState("all");

  useEffect(() => {
    setLoading(true);
    const params = new URLSearchParams();
    if (q) params.set("q", q);
    if (path && path !== "all") params.set("path_id", path);
    api.get(`/prompts/library${params.toString() ? `?${params}` : ""}`)
      .then(setData)
      .finally(() => setLoading(false));
  }, [q, path]);

  const items = data?.items || [];
  const pathOptions = data?.paths || [];

  const copy = async (text) => {
    try { await navigator.clipboard.writeText(text); toast.success("Prompt copied"); } catch (_e) { toast.error("Could not copy"); }
  };

  return (
    <div className="min-h-screen" style={{ background: "#0A0413" }}>
      <div className="max-w-5xl mx-auto px-6 py-10">
        <Link to="/dashboard" className="text-xs text-[var(--asc-text-muted)] hover:text-white flex items-center gap-1.5"><ArrowLeft size={12} /> Back to dashboard</Link>

        {/* Header */}
        <div className="mt-4 flex items-center gap-3">
          <div className="w-12 h-12 rounded-2xl grid place-items-center" style={{ background: "rgba(124,58,237,0.18)" }}>
            <Library size={22} color="#BFB4FF" />
          </div>
          <div>
            <h1 className="asc-h2 text-3xl sm:text-4xl">Prompt Library</h1>
            <p className="text-[var(--asc-text-dim)] text-sm">Every playground prompt across every lesson, in one place.</p>
          </div>
        </div>

        {/* Filters */}
        <div className="asc-card p-4 mt-6 flex items-center gap-3 flex-wrap" data-testid="prompts-filters">
          <div className="flex-1 min-w-[240px] flex items-center gap-2 px-3 py-2 rounded-xl" style={{ background: "#1F183A", border: "1px solid rgba(191,180,255,0.12)" }}>
            <Search size={14} color="#7a7a85" />
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Search prompts, instructions, lesson titles…"
              data-testid="prompts-search"
              className="bg-transparent outline-none flex-1 text-sm"
            />
          </div>
          <select
            value={path}
            onChange={(e) => setPath(e.target.value)}
            data-testid="prompts-path-filter"
            className="px-3 py-2 rounded-xl text-sm"
            style={{ background: "#1F183A", border: "1px solid rgba(191,180,255,0.12)", color: "#fff" }}
          >
            <option value="all">All paths ({items.length})</option>
            {pathOptions.map((p) => (<option key={p.id} value={p.id}>{p.title}</option>))}
          </select>
        </div>

        {/* Results */}
        {loading ? <Loader label="Loading prompts…" /> : (
          <div className="mt-6 grid gap-4" data-testid="prompts-results">
            {items.length === 0 && (
              <div className="asc-card p-8 text-center text-[var(--asc-text-dim)]">No prompts match your search.</div>
            )}
            {items.map((p, i) => (
              <div key={`${p.lesson_id}-${i}`} className="asc-card p-5" data-testid={`prompt-card-${i}`}>
                <div className="flex items-center justify-between gap-3 mb-2 flex-wrap">
                  <div className="flex items-center gap-2">
                    <Sparkles size={14} color="#FFB000" />
                    <span className="font-bold text-base">{p.card_title}</span>
                  </div>
                  <Link to={`/lessons/${p.lesson_id}`} className="text-xs text-[var(--asc-brand)] hover:underline flex items-center gap-1">
                    <BookOpen size={11} /> {p.lesson_title}
                  </Link>
                </div>
                <div className="text-xs text-[var(--asc-text-muted)] mb-2">{p.path_title}</div>
                <p className="text-sm text-[var(--asc-text-dim)] leading-relaxed">{p.instruction}</p>
                {p.seed_prompt && (
                  <div className="mt-3 p-3 rounded-xl relative" style={{ background: "rgba(255,176,0,0.04)", border: "1px solid rgba(255,176,0,0.20)" }}>
                    <div className="text-[10px] tracking-widest font-black mb-1" style={{ color: "#FFB000" }}>SEED PROMPT</div>
                    <div className="text-sm whitespace-pre-wrap pr-10">{p.seed_prompt}</div>
                    <button onClick={() => copy(p.seed_prompt)} data-testid={`prompt-copy-${i}`} className="absolute top-3 right-3 p-1.5 rounded-md hover:bg-white/10" aria-label="Copy prompt">
                      <Copy size={12} />
                    </button>
                  </div>
                )}
                <div className="mt-3 flex justify-end">
                  <Link to={`/lessons/${p.lesson_id}`} className="asc-btn-secondary text-xs">Open lesson →</Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
