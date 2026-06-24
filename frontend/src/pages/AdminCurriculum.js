import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import Loader from "@/components/Loader";
import TierBadge from "@/components/TierBadge";
import { Plus, Edit3, Trash2, Sparkles, AlertCircle, ArrowLeft, RefreshCw, Search } from "lucide-react";
import { toast } from "sonner";

export default function AdminCurriculum() {
  const nav = useNavigate();
  const [paths, setPaths] = useState([]);
  const [findings, setFindings] = useState(null);
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [q, setQ] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      const r = await api.get("/admin/curriculum/paths");
      setPaths(r.paths);
    } catch (e) { toast.error(e.message); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  const deletePath = async (id) => {
    if (!window.confirm(`Delete path "${id}"? This removes all its modules and lessons.`)) return;
    try {
      await api.del(`/admin/curriculum/paths/${id}`);
      toast.success("Path deleted");
      load();
    } catch (e) { toast.error(e.message); }
  };

  const scan = async () => {
    setScanning(true);
    try {
      const r = await api.get("/admin/ai/scan-outdated");
      setFindings(r);
      toast.success(`Scan complete — ${r.count} flagged lesson${r.count === 1 ? "" : "s"}`);
    } catch (e) { toast.error(e.message); }
    finally { setScanning(false); }
  };

  if (loading) return <Loader />;

  const filtered = paths.filter((p) => !q || `${p.title} ${p.subtitle}`.toLowerCase().includes(q.toLowerCase()));

  return (
    <div className="max-w-6xl mx-auto px-5 sm:px-8 py-10" data-testid="admin-curriculum-page">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <button onClick={() => nav("/admin")} className="flex items-center gap-1 text-sm text-[var(--asc-text-dim)] hover:text-white mb-2"><ArrowLeft size={14} /> Admin</button>
          <div className="asc-kicker">Curriculum Manager</div>
          <h1 className="asc-h2 text-4xl mt-1">All paths</h1>
          <p className="text-[var(--asc-text-dim)] text-sm mt-1">{paths.length} paths in curriculum.</p>
        </div>
        <div className="flex gap-2 flex-wrap">
          <button onClick={scan} disabled={scanning} className="asc-btn-secondary text-sm" data-testid="scan-outdated-btn">
            <RefreshCw size={14} className={scanning ? "animate-spin" : ""} /> {scanning ? "Scanning…" : "Scan for outdated content"}
          </button>
          <Link to="/admin/studio" className="asc-btn-primary text-sm" data-testid="open-studio-btn"><Sparkles size={14} /> AI Studio</Link>
        </div>
      </div>

      {findings && (
        <div className="asc-card p-5 mt-6" style={findings.count > 0 ? { borderColor: "#FFB000" } : { borderColor: "#34D399" }} data-testid="scan-findings">
          <div className="flex items-center gap-2 mb-2">
            <AlertCircle size={16} color={findings.count > 0 ? "#FFB000" : "#34D399"} />
            <span className="font-bold">{findings.count === 0 ? "No outdated content found" : `${findings.count} lesson(s) reference outdated models`}</span>
          </div>
          {findings.findings.map((f) => (
            <div key={f.lesson_id} className="flex items-center justify-between gap-3 mt-2 p-3 rounded-lg" style={{ background: "#1F183A" }}>
              <div className="text-sm min-w-0">
                <div className="font-bold truncate">{f.lesson_title}</div>
                <div className="text-xs text-[var(--asc-text-muted)]">{f.path_title} · {f.module_title}</div>
                <div className="text-xs text-[var(--asc-brand)] mt-1">Mentions: {f.outdated_terms.join(", ")}</div>
              </div>
              <Link to={`/admin/curriculum/${f.path_id}?lesson=${f.lesson_id}`} className="asc-btn-secondary text-xs shrink-0">Review</Link>
            </div>
          ))}
        </div>
      )}

      <div className="flex items-center gap-2 mt-6">
        <Search size={16} className="text-[var(--asc-text-muted)]" />
        <input className="asc-input flex-1 max-w-md" placeholder="Search paths…" value={q} onChange={(e) => setQ(e.target.value)} />
      </div>

      <div className="grid md:grid-cols-2 gap-4 mt-6">
        {filtered.map((p) => {
          const lessonCount = p.modules.reduce((s, m) => s + (m.lessons?.length || 0), 0);
          return (
            <div key={p.id} className="asc-card overflow-hidden" data-testid={`admin-path-${p.id}`}>
              <div className="relative h-32">
                <img src={p.image} alt={p.title} className="absolute inset-0 w-full h-full object-cover" onError={(e) => e.target.style.opacity = 0.2} />
                <div className="absolute inset-0" style={{ background: `linear-gradient(135deg, ${p.color}66, rgba(10,4,19,0.85))` }} />
                <div className="absolute top-3 left-3 flex gap-2">
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-black tracking-wider" style={{ background: p.color, color: "#000" }}>{p.level}</span>
                  <TierBadge tier={p.tier || "free"} />
                </div>
              </div>
              <div className="p-5">
                <div className="flex items-center justify-between gap-2">
                  <h3 className="asc-h2 text-lg truncate">{p.title}</h3>
                  <code className="text-[10px] text-[var(--asc-text-muted)]">{p.id}</code>
                </div>
                <p className="text-sm text-[var(--asc-text-dim)] mt-1 line-clamp-2">{p.tagline}</p>
                <div className="text-xs text-[var(--asc-text-muted)] mt-3">{p.modules.length} modules · {lessonCount} lessons</div>
                <div className="flex gap-2 mt-4">
                  <Link to={`/admin/curriculum/${p.id}`} className="asc-btn-primary text-xs flex-1 justify-center" data-testid={`edit-path-${p.id}`}>
                    <Edit3 size={12} /> Edit
                  </Link>
                  <button onClick={() => deletePath(p.id)} className="asc-btn-secondary text-xs" data-testid={`delete-path-${p.id}`}><Trash2 size={12} /></button>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
