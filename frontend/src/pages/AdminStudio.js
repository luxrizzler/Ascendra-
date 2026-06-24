import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { ArrowLeft, Sparkles, Wand2, BookOpen, Zap, Image as ImageIcon, ChevronRight } from "lucide-react";
import { toast } from "sonner";

const MODES = [
  { id: "lesson", title: "Generate a Lesson", body: "Type a topic. Claude drafts 4 engaging cards + a quiz. Preview before publishing.", icon: BookOpen, color: "#FFB000" },
  { id: "path", title: "Generate a Whole Path", body: "Describe a learning path concept. Get a complete curriculum: modules, lesson titles, and (optionally) full lesson bodies + cover art.", icon: Wand2, color: "#7C3AED" },
];

export default function AdminStudio() {
  const nav = useNavigate();
  const [mode, setMode] = useState("lesson");

  return (
    <div className="max-w-4xl mx-auto px-5 sm:px-8 py-10" data-testid="admin-studio-page">
      <button onClick={() => nav("/admin/curriculum")} className="flex items-center gap-1 text-sm text-[var(--asc-text-dim)] hover:text-white mb-3"><ArrowLeft size={14} /> Curriculum</button>
      <div className="asc-kicker">AI Studio</div>
      <h1 className="asc-h2 text-4xl mt-1 flex items-center gap-2"><Sparkles size={28} className="text-[var(--asc-brand)]" /> Compose new courses with AI</h1>
      <p className="text-[var(--asc-text-dim)] mt-2">Claude Sonnet 4.5 writes the lesson. You stay in editorial control.</p>

      <div className="grid sm:grid-cols-2 gap-3 mt-7">
        {MODES.map((m) => {
          const Icon = m.icon;
          const selected = mode === m.id;
          return (
            <button key={m.id} onClick={() => setMode(m.id)} data-testid={`studio-mode-${m.id}`} className="asc-card p-5 text-left" style={selected ? { borderColor: m.color, background: `${m.color}10` } : {}}>
              <div className="flex items-center gap-3 mb-2">
                <div className="w-10 h-10 rounded-xl grid place-items-center" style={{ background: `${m.color}22`, border: `1px solid ${m.color}66` }}>
                  <Icon size={18} color={m.color} />
                </div>
                <div className="font-black">{m.title}</div>
                {selected && <ChevronRight size={16} className="ml-auto" />}
              </div>
              <p className="text-sm text-[var(--asc-text-dim)]">{m.body}</p>
            </button>
          );
        })}
      </div>

      <div className="mt-7">
        {mode === "lesson" ? <LessonGenerator /> : <PathGenerator />}
      </div>
    </div>
  );
}

function LessonGenerator() {
  const [topic, setTopic] = useState("");
  const [level, setLevel] = useState("Beginner");
  const [busy, setBusy] = useState(false);
  const [draft, setDraft] = useState(null);
  const [publishTo, setPublishTo] = useState({ path_id: "", module_id: "" });
  const [paths, setPaths] = useState([]);

  const loadPaths = async () => {
    try { const r = await api.get("/admin/curriculum/paths"); setPaths(r.paths); } catch {}
  };
  useState(() => { loadPaths(); }, []);
  // useState hack to run once; reasonable since this is dev-only admin page
  if (paths.length === 0) loadPaths();

  const generate = async () => {
    if (!topic.trim()) { toast.error("Enter a topic"); return; }
    setBusy(true);
    setDraft(null);
    try {
      const r = await api.post("/admin/ai/generate-lesson", { topic: topic.trim(), level });
      setDraft(r.draft);
      toast.success("Draft generated");
    } catch (e) { toast.error(e.message); }
    finally { setBusy(false); }
  };

  const publish = async (alsoPublish) => {
    if (alsoPublish && (!publishTo.path_id || !publishTo.module_id)) { toast.error("Pick a destination path + module"); return; }
    setBusy(true);
    try {
      const r = await api.post("/admin/ai/generate-lesson", { topic: topic.trim(), level, path_id: publishTo.path_id || undefined, module_id: publishTo.module_id || undefined, publish: !!alsoPublish });
      setDraft(r.draft);
      toast.success(alsoPublish ? "Lesson generated & published ✨" : "Draft generated");
    } catch (e) { toast.error(e.message); }
    finally { setBusy(false); }
  };

  const selectedPath = paths.find((p) => p.id === publishTo.path_id);
  const modules = selectedPath?.modules || [];

  return (
    <div className="asc-card p-6" data-testid="lesson-generator">
      <h2 className="asc-h2 text-xl mb-4">New lesson</h2>
      <div className="space-y-3">
        <div>
          <div className="asc-label mb-1">Topic / learning objective</div>
          <textarea className="asc-input min-h-[80px]" placeholder="e.g., How to use Claude 4.5 to write a winning cold email in 5 minutes" value={topic} onChange={(e) => setTopic(e.target.value)} data-testid="studio-topic" />
        </div>
        <div className="grid sm:grid-cols-3 gap-3">
          <div>
            <div className="asc-label mb-1">Level</div>
            <select className="asc-input" value={level} onChange={(e) => setLevel(e.target.value)} data-testid="studio-level">
              {["Beginner", "Intermediate", "Advanced"].map((l) => <option key={l}>{l}</option>)}
            </select>
          </div>
          <div>
            <div className="asc-label mb-1">Publish to path (optional)</div>
            <select className="asc-input" value={publishTo.path_id} onChange={(e) => setPublishTo({ path_id: e.target.value, module_id: "" })} data-testid="studio-publish-path">
              <option value="">— Draft only —</option>
              {paths.map((p) => <option key={p.id} value={p.id}>{p.title}</option>)}
            </select>
          </div>
          <div>
            <div className="asc-label mb-1">Module</div>
            <select className="asc-input" value={publishTo.module_id} disabled={!selectedPath} onChange={(e) => setPublishTo({ ...publishTo, module_id: e.target.value })} data-testid="studio-publish-module">
              <option value="">{selectedPath ? "Pick module…" : "Pick a path first"}</option>
              {modules.map((m) => <option key={m.id} value={m.id}>{m.title}</option>)}
            </select>
          </div>
        </div>

        <div className="flex flex-wrap gap-2 pt-2">
          <button onClick={generate} disabled={busy} className="asc-btn-secondary" data-testid="studio-preview-btn"><Wand2 size={14} /> {busy ? "Drafting…" : "Preview draft"}</button>
          <button onClick={() => publish(true)} disabled={busy || !publishTo.path_id || !publishTo.module_id} className="asc-btn-primary" data-testid="studio-autopublish-btn"><Zap size={14} /> Auto-publish</button>
        </div>
      </div>

      {draft && (
        <div className="mt-7 pt-6 border-t border-[var(--asc-border)]" data-testid="studio-draft">
          <div className="asc-kicker mb-1">Draft preview</div>
          <h3 className="asc-h2 text-2xl">{draft.title}</h3>
          <div className="text-xs text-[var(--asc-text-muted)] mt-1">{draft.duration_min} min · {draft.xp} XP · {draft.cards.length} cards</div>

          <div className="mt-4 space-y-3">
            {draft.cards.map((c, i) => (
              <div key={i} className="p-4 rounded-xl" style={{ background: "#1F183A" }}>
                <div className="text-[10px] uppercase tracking-wider text-[var(--asc-text-muted)] mb-1">Card {i + 1}</div>
                <div className="font-bold">{c.title}</div>
                <div className="text-sm text-[var(--asc-text-dim)] mt-1 whitespace-pre-wrap leading-relaxed">{c.body}</div>
              </div>
            ))}
            <div className="p-4 rounded-xl" style={{ background: "rgba(255,176,0,0.06)", border: "1px solid rgba(255,176,0,0.4)" }}>
              <div className="text-[10px] uppercase tracking-wider text-[var(--asc-brand)] mb-1">Quiz</div>
              <div className="font-bold">{draft.quiz.question}</div>
              <ul className="text-sm mt-2 space-y-1">
                {draft.quiz.options.map((o, i) => (
                  <li key={i} className={i === draft.quiz.answer_index ? "text-[var(--asc-success)] font-bold" : "text-[var(--asc-text-dim)]"}>
                    {String.fromCharCode(65 + i)}. {o} {i === draft.quiz.answer_index ? "✓" : ""}
                  </li>
                ))}
              </ul>
              {draft.quiz.explanation && <p className="text-xs text-[var(--asc-text-dim)] mt-2 italic">{draft.quiz.explanation}</p>}
            </div>
          </div>

          {publishTo.path_id && publishTo.module_id && (
            <button onClick={() => publish(true)} disabled={busy} className="asc-btn-primary mt-4" data-testid="studio-publish-draft-btn">
              Publish to {selectedPath?.title}
            </button>
          )}
        </div>
      )}
    </div>
  );
}

function PathGenerator() {
  const [concept, setConcept] = useState("");
  const [level, setLevel] = useState("Beginner");
  const [tier, setTier] = useState("free");
  const [genLessons, setGenLessons] = useState(false);
  const [autoCover, setAutoCover] = useState(true);
  const [busy, setBusy] = useState(false);
  const nav = useNavigate();

  const generate = async () => {
    if (!concept.trim()) { toast.error("Describe the path concept"); return; }
    setBusy(true);
    try {
      toast.info(genLessons ? "Generating full path (may take 1–2 min)…" : "Generating outline (~15 sec)…");
      const r = await api.post("/admin/ai/generate-path", { concept: concept.trim(), level, tier, generate_lessons: genLessons, auto_cover: autoCover });
      toast.success(`Path created: ${r.path.title}${r.generated_lessons ? ` (${r.generated_lessons} lessons authored)` : ""}`);
      nav(`/admin/curriculum/${r.path.id}`);
    } catch (e) { toast.error(e.message); }
    finally { setBusy(false); }
  };

  return (
    <div className="asc-card p-6" data-testid="path-generator">
      <h2 className="asc-h2 text-xl mb-4">New learning path</h2>
      <div className="space-y-3">
        <div>
          <div className="asc-label mb-1">Path concept</div>
          <textarea className="asc-input min-h-[100px]" placeholder="e.g., A path for marketers to master AI-powered campaigns: prompting, image gen, video, agents." value={concept} onChange={(e) => setConcept(e.target.value)} data-testid="path-gen-concept" />
        </div>
        <div className="grid sm:grid-cols-2 gap-3">
          <div>
            <div className="asc-label mb-1">Level</div>
            <select className="asc-input" value={level} onChange={(e) => setLevel(e.target.value)} data-testid="path-gen-level">
              {["Beginner", "Intermediate", "Advanced"].map((l) => <option key={l}>{l}</option>)}
            </select>
          </div>
          <div>
            <div className="asc-label mb-1">Tier (gating)</div>
            <select className="asc-input" value={tier} onChange={(e) => setTier(e.target.value)} data-testid="path-gen-tier">
              {["free", "ascender", "pathfinder", "sage"].map((t) => <option key={t}>{t}</option>)}
            </select>
          </div>
        </div>

        <div className="flex flex-wrap gap-4 pt-2">
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={genLessons} onChange={(e) => setGenLessons(e.target.checked)} className="accent-[var(--asc-brand)]" data-testid="path-gen-fulllessons" />
            Also generate full lesson bodies (slower)
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={autoCover} onChange={(e) => setAutoCover(e.target.checked)} className="accent-[var(--asc-brand)]" data-testid="path-gen-cover" />
            <ImageIcon size={12} /> Generate cover image
          </label>
        </div>

        <button onClick={generate} disabled={busy} className="asc-btn-primary mt-2" data-testid="path-gen-submit">
          <Wand2 size={14} /> {busy ? "Generating…" : "Create path"}
        </button>
      </div>
    </div>
  );
}
