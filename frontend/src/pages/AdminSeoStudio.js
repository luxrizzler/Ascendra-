import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, BACKEND_URL } from "@/lib/api";
import Loader from "@/components/Loader";
import { ArrowLeft, Sparkles, Eye, FileText, CheckCircle2, Archive, Trash2, Plus, ExternalLink, Globe } from "lucide-react";
import { toast } from "sonner";
import { formatDate } from "@/lib/utils";

const SUGGESTED_MODELS = ["Claude Sonnet 4.5", "GPT-5.2", "Gemini 3", "Sora 2", "Nano Banana", "ElevenLabs", "Veo 3", "Midjourney", "Perplexity", "Suno", "Whisper", "Cursor"];
const SUGGESTED_USECASES = ["For Marketing", "For Founders", "For Sales", "For Designers", "For Writing", "For Code", "For Research", "For Education"];

export default function AdminSeoStudio() {
  const nav = useNavigate();
  const [pages, setPages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("all");
  const [showGenHub, setShowGenHub] = useState(false);
  const [showGenUC, setShowGenUC] = useState(false);
  const [genBusy, setGenBusy] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const url = statusFilter === "all" ? "/admin/seo/pages" : `/admin/seo/pages?status=${statusFilter}`;
      const r = await api.get(url);
      setPages(r.pages || []);
    } catch (e) {
      toast.error(e.message || "Could not load");
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [statusFilter]);

  // Generate hub
  const [hubModel, setHubModel] = useState("");
  const [hubPublish, setHubPublish] = useState(true);
  const generateHub = async () => {
    if (!hubModel.trim()) { toast.error("Model name required"); return; }
    setGenBusy(true);
    try {
      const r = await api.post("/admin/seo/generate-hub", { model_name: hubModel.trim(), publish: hubPublish });
      toast.success(`${hubPublish ? "Published" : "Drafted"}: ${r.page.title}`);
      setHubModel("");
      setShowGenHub(false);
      load();
    } catch (e) {
      toast.error(e.message || "Generation failed");
    } finally {
      setGenBusy(false);
    }
  };

  // Generate use case
  const [ucModel, setUcModel] = useState("");
  const [ucUseCase, setUcUseCase] = useState("");
  const [ucPublish, setUcPublish] = useState(true);
  const generateUseCase = async () => {
    if (!ucModel.trim() || !ucUseCase.trim()) { toast.error("Model and use case required"); return; }
    setGenBusy(true);
    try {
      const r = await api.post("/admin/seo/generate-usecase", { model_name: ucModel.trim(), use_case: ucUseCase.trim(), publish: ucPublish });
      toast.success(`${ucPublish ? "Published" : "Drafted"}: ${r.page.title}`);
      setUcModel("");
      setUcUseCase("");
      setShowGenUC(false);
      load();
    } catch (e) {
      toast.error(e.message || "Generation failed");
    } finally {
      setGenBusy(false);
    }
  };

  const setStatus = async (p, status) => {
    try {
      const path = p.use_case_slug ? `/admin/seo/page/${p.model_slug}/${p.use_case_slug}/status` : `/admin/seo/page/${p.model_slug}/status`;
      await api.post(path, { status });
      toast.success(`Marked as ${status}`);
      load();
    } catch (e) {
      toast.error(e.message || "Update failed");
    }
  };

  const deletePage = async (p) => {
    if (!confirm(`Delete "${p.title}"? This can't be undone.`)) return;
    try {
      const path = p.use_case_slug ? `/admin/seo/page/${p.model_slug}/${p.use_case_slug}` : `/admin/seo/page/${p.model_slug}`;
      await api.del(path);
      toast.success("Deleted");
      load();
    } catch (e) {
      toast.error(e.message || "Delete failed");
    }
  };

  const previewUrl = (p) => {
    const base = BACKEND_URL.replace(/\/$/, "");
    return p.use_case_slug ? `${base}/learn/${p.model_slug}/${p.use_case_slug}` : `${base}/learn/${p.model_slug}`;
  };

  const counts = {
    all: pages.length,
    published: pages.filter((p) => p.status === "published").length,
    draft: pages.filter((p) => p.status === "draft").length,
    archived: pages.filter((p) => p.status === "archived").length,
  };

  return (
    <div className="max-w-7xl mx-auto px-5 sm:px-8 py-10" data-testid="admin-seo-studio-page">
      <button onClick={() => nav("/admin")} className="flex items-center gap-1 text-sm text-[var(--asc-text-dim)] hover:text-white mb-3"><ArrowLeft size={14} /> Admin</button>
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="asc-kicker">Growth</div>
          <h1 className="asc-h2 text-4xl mt-1 flex items-center gap-3"><Globe size={28} className="text-[var(--asc-brand)]" /> SEO Studio</h1>
          <p className="text-[var(--asc-text-dim)] text-sm mt-2 max-w-2xl">AI-generated landing pages for every model and use-case. Published pages appear in <code className="asc-mono text-xs px-1 rounded bg-[#15102B]">sitemap.xml</code> for Google.</p>
        </div>
        <div className="flex gap-2 flex-wrap">
          <button onClick={() => setShowGenHub(true)} className="asc-btn-primary text-sm" data-testid="seo-generate-hub-btn"><Sparkles size={14} /> Generate model hub</button>
          <button onClick={() => setShowGenUC(true)} className="asc-btn-secondary text-sm" data-testid="seo-generate-usecase-btn"><Plus size={14} /> Generate use-case page</button>
          <a href={`${BACKEND_URL.replace(/\/$/, "")}/api/seo/sitemap.xml`} target="_blank" rel="noopener noreferrer" className="asc-btn-secondary text-sm" data-testid="seo-view-sitemap-btn"><ExternalLink size={14} /> View sitemap.xml</a>
        </div>
      </div>

      {/* Filter pills */}
      <div className="flex flex-wrap gap-2 mt-6">
        {["all", "published", "draft", "archived"].map((s) => (
          <button key={s} onClick={() => setStatusFilter(s)} data-testid={`seo-filter-${s}`} className="px-3 py-1.5 rounded-full text-xs font-bold transition border" style={statusFilter === s ? { background: "#FFB000", color: "#000", borderColor: "#FFB000" } : { background: "transparent", color: "#C8C5E6", borderColor: "rgba(191,180,255,0.28)" }}>
            {s.toUpperCase()} ({counts[s] || 0})
          </button>
        ))}
      </div>

      {/* Pages list */}
      <div className="mt-6">
        {loading ? (
          <Loader />
        ) : pages.length === 0 ? (
          <div className="asc-card p-10 text-center" data-testid="seo-empty">
            <div className="w-12 h-12 mx-auto rounded-2xl grid place-items-center mb-3" style={{ background: "rgba(255,176,0,0.10)" }}><FileText size={20} color="#FFB000" /></div>
            <div className="asc-h2 text-lg">No pages yet</div>
            <p className="text-[var(--asc-text-dim)] text-sm mt-2 max-w-md mx-auto">Generate your first model hub to start ranking on Google. Suggested first batch: Claude, GPT-5.2, Gemini, Sora.</p>
            <button onClick={() => setShowGenHub(true)} className="asc-btn-primary text-sm mt-5"><Sparkles size={14} /> Generate first page</button>
          </div>
        ) : (
          <div className="space-y-2" data-testid="seo-pages-list">
            {pages.map((p) => (
              <div key={p.id} className="asc-card p-4 flex flex-wrap items-center gap-3" data-testid={`seo-page-${p.id.replace("/", "-")}`}>
                <StatusPill status={p.status} />
                <div className="flex-1 min-w-[280px]">
                  <div className="font-bold text-sm">{p.title}</div>
                  <div className="text-xs text-[var(--asc-text-muted)] asc-mono">/learn/{p.model_slug}{p.use_case_slug ? `/${p.use_case_slug}` : ""} · updated {formatDate(p.updated_at)}</div>
                </div>
                <a href={previewUrl(p)} target="_blank" rel="noopener noreferrer" className="asc-btn-secondary text-xs" data-testid={`seo-preview-${p.id.replace("/", "-")}`}><Eye size={12} /> Preview</a>
                {p.status !== "published" && <button onClick={() => setStatus(p, "published")} className="asc-btn-secondary text-xs"><CheckCircle2 size={12} /> Publish</button>}
                {p.status !== "archived" && <button onClick={() => setStatus(p, "archived")} className="asc-btn-secondary text-xs"><Archive size={12} /> Archive</button>}
                <button onClick={() => deletePage(p)} className="asc-btn-secondary text-xs" style={{ color: "#FB7185" }}><Trash2 size={12} /></button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Generate hub modal */}
      {showGenHub && (
        <Modal onClose={() => setShowGenHub(false)} title="Generate model hub page">
          <p className="text-sm text-[var(--asc-text-dim)] mb-3">Generates a /learn/{`{model}`} landing page using Claude 4.5. Takes ~10–20 seconds.</p>
          <label className="asc-label">Model name</label>
          <input className="asc-input w-full mt-1" placeholder="e.g. Claude Sonnet 4.5" value={hubModel} onChange={(e) => setHubModel(e.target.value)} data-testid="seo-hub-input" />
          <div className="flex flex-wrap gap-1 mt-2">
            {SUGGESTED_MODELS.map((m) => (
              <button key={m} onClick={() => setHubModel(m)} className="text-[10px] px-2 py-1 rounded-full border border-[var(--asc-border)] text-[var(--asc-text-dim)] hover:text-white">{m}</button>
            ))}
          </div>
          <label className="flex items-center gap-2 mt-4 text-sm">
            <input type="checkbox" checked={hubPublish} onChange={(e) => setHubPublish(e.target.checked)} /> Publish immediately
          </label>
          <div className="flex justify-end gap-2 mt-5">
            <button onClick={() => setShowGenHub(false)} className="asc-btn-secondary text-sm">Cancel</button>
            <button onClick={generateHub} disabled={genBusy} className="asc-btn-primary text-sm" data-testid="seo-hub-generate-confirm">{genBusy ? "Generating…" : "Generate"}</button>
          </div>
        </Modal>
      )}

      {/* Generate use case modal */}
      {showGenUC && (
        <Modal onClose={() => setShowGenUC(false)} title="Generate use-case page">
          <p className="text-sm text-[var(--asc-text-dim)] mb-3">Generates /learn/{`{model}`}/{`{use-case}`} landing page.</p>
          <label className="asc-label">Model name</label>
          <input className="asc-input w-full mt-1" placeholder="e.g. Claude" value={ucModel} onChange={(e) => setUcModel(e.target.value)} data-testid="seo-uc-model-input" />
          <label className="asc-label mt-3 block">Use case</label>
          <input className="asc-input w-full mt-1" placeholder="e.g. For Marketing" value={ucUseCase} onChange={(e) => setUcUseCase(e.target.value)} data-testid="seo-uc-usecase-input" />
          <div className="flex flex-wrap gap-1 mt-2">
            {SUGGESTED_USECASES.map((u) => (
              <button key={u} onClick={() => setUcUseCase(u)} className="text-[10px] px-2 py-1 rounded-full border border-[var(--asc-border)] text-[var(--asc-text-dim)] hover:text-white">{u}</button>
            ))}
          </div>
          <label className="flex items-center gap-2 mt-4 text-sm">
            <input type="checkbox" checked={ucPublish} onChange={(e) => setUcPublish(e.target.checked)} /> Publish immediately
          </label>
          <div className="flex justify-end gap-2 mt-5">
            <button onClick={() => setShowGenUC(false)} className="asc-btn-secondary text-sm">Cancel</button>
            <button onClick={generateUseCase} disabled={genBusy} className="asc-btn-primary text-sm" data-testid="seo-uc-generate-confirm">{genBusy ? "Generating…" : "Generate"}</button>
          </div>
        </Modal>
      )}
    </div>
  );
}

function StatusPill({ status }) {
  const palette = {
    published: { bg: "rgba(52,211,153,0.15)", color: "#34D399" },
    draft: { bg: "rgba(255,176,0,0.15)", color: "#FFB000" },
    archived: { bg: "rgba(255,255,255,0.05)", color: "#C8C5E6" },
  };
  const p = palette[status] || palette.draft;
  return <span className="px-2 py-0.5 rounded-full text-[10px] font-black tracking-wider shrink-0" style={{ background: p.bg, color: p.color }}>{(status || "draft").toUpperCase()}</span>;
}

function Modal({ children, onClose, title }) {
  return (
    <div className="fixed inset-0 z-50 grid place-items-center p-4" style={{ background: "rgba(0,0,0,0.7)", backdropFilter: "blur(8px)" }} onClick={onClose}>
      <div onClick={(e) => e.stopPropagation()} className="asc-card w-full max-w-lg p-6">
        <h2 className="asc-h2 text-xl mb-3">{title}</h2>
        {children}
      </div>
    </div>
  );
}
