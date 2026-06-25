import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import Loader from "@/components/Loader";
import { ArrowLeft, Sparkles, BookOpen, Layers, Filter, ChevronRight } from "lucide-react";
import { toast } from "sonner";
import { formatDate } from "@/lib/utils";

const WINDOW_OPTIONS = [
  { label: "7 days", value: 7 },
  { label: "30 days", value: 30 },
  { label: "90 days", value: 90 },
  { label: "All time", value: 365 },
];

export default function AdminWhatsNew() {
  const nav = useNavigate();
  const [days, setDays] = useState(30);
  const [items, setItems] = useState([]);
  const [typeFilter, setTypeFilter] = useState("all");
  const [loading, setLoading] = useState(true);

  const load = async (d = days) => {
    setLoading(true);
    try {
      const r = await api.get(`/admin/whats-new?days=${d}&limit=200`);
      setItems(r.items || []);
    } catch (e) {
      toast.error(e.message || "Could not load What's New");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(days); /* eslint-disable-next-line */ }, [days]);

  const filtered = typeFilter === "all" ? items : items.filter((i) => i.type === typeFilter);
  const pathCount = items.filter((i) => i.type === "path").length;
  const lessonCount = items.filter((i) => i.type === "lesson").length;

  return (
    <div className="max-w-6xl mx-auto px-5 sm:px-8 py-10" data-testid="admin-whats-new-page">
      <button onClick={() => nav("/admin")} className="flex items-center gap-1 text-sm text-[var(--asc-text-dim)] hover:text-white mb-3" data-testid="whats-new-back-btn"><ArrowLeft size={14} /> Admin</button>
      <div className="asc-kicker">Content</div>
      <h1 className="asc-h2 text-4xl mt-1 flex items-center gap-3"><Sparkles size={28} className="text-[var(--asc-brand)]" /> What’s New</h1>
      <p className="text-[var(--asc-text-dim)] text-sm mt-2 max-w-2xl">Every path and lesson the AI Studio has shipped, ordered from newest to oldest. This is what your learners see in the “New this week” widget on their dashboard.</p>

      {/* Controls */}
      <div className="flex flex-wrap items-center gap-3 mt-6">
        <div className="flex items-center gap-1 p-1 rounded-full border border-[var(--asc-border)]" style={{ background: "#15102B" }}>
          {WINDOW_OPTIONS.map((w) => (
            <button key={w.value} onClick={() => setDays(w.value)} data-testid={`whats-new-window-${w.value}`} className="px-3 py-1.5 rounded-full text-xs font-bold transition" style={days === w.value ? { background: "#FFB000", color: "#000" } : { color: "#C8C5E6" }}>{w.label}</button>
          ))}
        </div>
        <div className="flex items-center gap-1 p-1 rounded-full border border-[var(--asc-border)]" style={{ background: "#15102B" }}>
          {[
            { id: "all", label: `All (${items.length})` },
            { id: "path", label: `Paths (${pathCount})` },
            { id: "lesson", label: `Lessons (${lessonCount})` },
          ].map((f) => (
            <button key={f.id} onClick={() => setTypeFilter(f.id)} data-testid={`whats-new-filter-${f.id}`} className="px-3 py-1.5 rounded-full text-xs font-bold transition" style={typeFilter === f.id ? { background: "#7C3AED", color: "#fff" } : { color: "#C8C5E6" }}>{f.label}</button>
          ))}
        </div>
      </div>

      {/* List */}
      <div className="mt-6">
        {loading ? (
          <Loader label="Loading recent content…" />
        ) : filtered.length === 0 ? (
          <div className="asc-card p-10 text-center" data-testid="whats-new-empty">
            <div className="w-12 h-12 mx-auto rounded-2xl grid place-items-center mb-3" style={{ background: "rgba(255,176,0,0.10)" }}><Filter size={20} color="#FFB000" /></div>
            <div className="asc-h2 text-lg">Nothing here yet</div>
            <p className="text-[var(--asc-text-dim)] text-sm mt-2 max-w-md mx-auto">Once you publish content from the AI Studio it will appear here, ordered from newest to oldest. Try generating a path to populate this view.</p>
            <button onClick={() => nav("/admin/studio")} className="asc-btn-primary text-sm mt-5" data-testid="whats-new-go-studio-btn"><Sparkles size={14} /> Open AI Studio</button>
          </div>
        ) : (
          <ul className="space-y-3" data-testid="whats-new-list">
            {filtered.map((it, idx) => (
              <li key={`${it.type}-${it.path_id}-${it.lesson_id || idx}`} className="asc-card p-4 flex items-center gap-4" data-testid={`whats-new-item-${it.type}-${it.lesson_id || it.path_id}`}>
                <div className="w-12 h-12 rounded-xl grid place-items-center shrink-0" style={{ background: it.type === "path" ? "rgba(124,58,237,0.18)" : "rgba(255,176,0,0.12)", border: `1px solid ${it.type === "path" ? "rgba(191,180,255,0.35)" : "rgba(255,176,0,0.35)"}` }}>
                  {it.type === "path" ? <Layers size={18} color="#BFB4FF" /> : <BookOpen size={18} color="#FFB000" />}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="asc-kicker text-[10px]" style={{ color: it.type === "path" ? "#BFB4FF" : "#FFB000" }}>{it.type === "path" ? "NEW PATH" : "NEW LESSON"}</span>
                    <span className="asc-mono text-xs text-[var(--asc-text-muted)]">{formatDate(it.created_at)}</span>
                  </div>
                  <div className="font-bold text-sm mt-1 truncate">
                    {it.type === "path" ? it.path_title : it.lesson_title}
                  </div>
                  <div className="text-xs text-[var(--asc-text-dim)] mt-0.5 truncate">
                    {it.type === "lesson" && (<><span style={{ color: it.path_color }}>{it.path_title}</span> · {it.module_title} · </>)}
                    <span className="uppercase font-bold tracking-wider" style={{ color: it.tier === "sage" ? "#FFB000" : it.tier === "pathfinder" ? "#7C3AED" : "#34D399" }}>{it.tier}</span>
                  </div>
                </div>
                <Link to={it.type === "path" ? `/admin/curriculum/${it.path_id}` : `/admin/curriculum/${it.path_id}`} className="asc-btn-secondary text-xs shrink-0" data-testid={`whats-new-open-${it.type}-${it.lesson_id || it.path_id}`}>
                  Open <ChevronRight size={14} />
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
