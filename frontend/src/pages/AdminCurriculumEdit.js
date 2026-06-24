import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { api } from "@/lib/api";
import Loader from "@/components/Loader";
import TierBadge from "@/components/TierBadge";
import { ArrowLeft, Plus, Trash2, Save, Sparkles, RefreshCw, Image as ImageIcon, ChevronDown, ChevronRight, Edit3 } from "lucide-react";
import { toast } from "sonner";

const TIERS = ["free", "ascender", "pathfinder", "sage"];
const COLORS = ["#FFB000", "#FF6B35", "#BFB4FF", "#7C3AED", "#E8C572", "#34D399", "#FB7185", "#38BDF8"];

export default function AdminCurriculumEdit() {
  const { pathId } = useParams();
  const nav = useNavigate();
  const [params] = useSearchParams();
  const focusLessonId = params.get("lesson");

  const [path, setPath] = useState(null);
  const [loading, setLoading] = useState(true);
  const [savingMeta, setSavingMeta] = useState(false);
  const [genCover, setGenCover] = useState(false);
  const [expandedModules, setExpandedModules] = useState({});
  const [editingLesson, setEditingLesson] = useState(null);

  const load = async () => {
    setLoading(true);
    try {
      const p = await api.get(`/admin/curriculum/paths/${pathId}`);
      setPath(p);
      // expand modules by default; if a specific lesson is focused, open its module
      const exp = {};
      for (const m of p.modules) exp[m.id] = true;
      setExpandedModules(exp);
      if (focusLessonId) {
        for (const m of p.modules) {
          const lsn = (m.lessons || []).find((l) => l.id === focusLessonId);
          if (lsn) { setEditingLesson({ ...lsn, _module_id: m.id }); break; }
        }
      }
    } catch (e) { toast.error(e.message); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, [pathId]);

  const saveMeta = async (patch) => {
    setSavingMeta(true);
    try {
      const updated = await api.patch(`/admin/curriculum/paths/${pathId}`, { title: path.title, ...patch });
      setPath(updated);
      toast.success("Saved");
    } catch (e) { toast.error(e.message); }
    finally { setSavingMeta(false); }
  };

  const regenCover = async () => {
    setGenCover(true);
    try {
      const r = await api.post("/admin/ai/generate-cover", { prompt: path.title + " — " + (path.tagline || ""), path_id: pathId });
      const url = r.url;
      setPath((p) => ({ ...p, image: url }));
      toast.success("Cover image generated");
    } catch (e) { toast.error(e.message); }
    finally { setGenCover(false); }
  };

  const addModule = async () => {
    const title = window.prompt("New module title:");
    if (!title) return;
    try {
      await api.post(`/admin/curriculum/paths/${pathId}/modules`, { title });
      toast.success("Module added");
      load();
    } catch (e) { toast.error(e.message); }
  };

  const deleteModule = async (mid) => {
    if (!window.confirm("Delete this module and all its lessons?")) return;
    try {
      await api.del(`/admin/curriculum/paths/${pathId}/modules/${mid}`);
      toast.success("Module deleted");
      load();
    } catch (e) { toast.error(e.message); }
  };

  const deleteLesson = async (mid, lid) => {
    if (!window.confirm("Delete this lesson?")) return;
    try {
      await api.del(`/admin/curriculum/paths/${pathId}/modules/${mid}/lessons/${lid}`);
      toast.success("Lesson deleted");
      load();
    } catch (e) { toast.error(e.message); }
  };

  const refreshLessonAI = async (mid, lid) => {
    if (!window.confirm("Use AI to refresh this lesson for 2026? This rewrites cards and quiz where needed.")) return;
    try {
      toast.info("AI refreshing lesson… give it ~20 sec.");
      const r = await api.post(`/admin/ai/refresh-lesson/${pathId}/${mid}/${lid}`);
      toast.success("Lesson refreshed");
      load();
      if (editingLesson?.id === lid) setEditingLesson({ ...r.lesson, _module_id: mid });
    } catch (e) { toast.error(e.message); }
  };

  const aiAddLesson = async (mid) => {
    const topic = window.prompt("What's the lesson about? (one clear sentence is best)");
    if (!topic) return;
    try {
      toast.info("Generating with Claude… ~15 sec.");
      const r = await api.post("/admin/ai/generate-lesson", { topic, level: path.level || "Beginner", path_id: pathId, module_id: mid, publish: true });
      toast.success(r.published ? "Lesson published ✨" : "Draft created (but not published)");
      load();
    } catch (e) { toast.error(e.message); }
  };

  if (loading || !path) return <Loader />;

  return (
    <div className="max-w-5xl mx-auto px-5 sm:px-8 py-10" data-testid="admin-curriculum-edit-page">
      <button onClick={() => nav("/admin/curriculum")} className="flex items-center gap-1 text-sm text-[var(--asc-text-dim)] hover:text-white mb-3"><ArrowLeft size={14} /> Back to curriculum</button>

      {/* Path meta card */}
      <div className="asc-card overflow-hidden">
        <div className="relative h-48">
          <img src={path.image} alt="" className="absolute inset-0 w-full h-full object-cover" />
          <div className="absolute inset-0" style={{ background: `linear-gradient(135deg, ${path.color}77, rgba(10,4,19,0.85))` }} />
          <button onClick={regenCover} disabled={genCover} className="absolute top-3 right-3 asc-btn-primary text-xs" data-testid="regen-cover-btn">
            <ImageIcon size={12} /> {genCover ? "Generating cover…" : "Re-generate cover (AI)"}
          </button>
          <div className="absolute bottom-3 left-3 flex gap-2 items-center">
            <code className="text-[10px] text-white px-2 py-0.5 rounded-full" style={{ background: "rgba(0,0,0,0.4)" }}>{path.id}</code>
            <TierBadge tier={path.tier || "free"} />
          </div>
        </div>
        <div className="p-5 space-y-3">
          <FormRow label="Title"><input className="asc-input" value={path.title} onChange={(e) => setPath({ ...path, title: e.target.value })} onBlur={(e) => saveMeta({ title: e.target.value })} data-testid="meta-title" /></FormRow>
          <FormRow label="Subtitle"><input className="asc-input" value={path.subtitle || ""} onChange={(e) => setPath({ ...path, subtitle: e.target.value })} onBlur={(e) => saveMeta({ subtitle: e.target.value })} /></FormRow>
          <FormRow label="Tagline"><input className="asc-input" value={path.tagline || ""} onChange={(e) => setPath({ ...path, tagline: e.target.value })} onBlur={(e) => saveMeta({ tagline: e.target.value })} /></FormRow>
          <div className="grid sm:grid-cols-3 gap-3">
            <FormRow label="Level">
              <select className="asc-input" value={path.level || "Beginner"} onChange={(e) => { setPath({ ...path, level: e.target.value }); saveMeta({ level: e.target.value }); }}>
                {["Beginner", "Intermediate", "Advanced"].map((l) => <option key={l}>{l}</option>)}
              </select>
            </FormRow>
            <FormRow label="Duration"><input className="asc-input" value={path.duration || ""} onChange={(e) => setPath({ ...path, duration: e.target.value })} onBlur={(e) => saveMeta({ duration: e.target.value })} /></FormRow>
            <FormRow label="Tier">
              <select className="asc-input" value={path.tier || "free"} onChange={(e) => { setPath({ ...path, tier: e.target.value }); saveMeta({ tier: e.target.value }); }} data-testid="meta-tier">
                {TIERS.map((t) => <option key={t}>{t}</option>)}
              </select>
            </FormRow>
          </div>
          <FormRow label="Color">
            <div className="flex flex-wrap gap-2">
              {COLORS.map((c) => (
                <button key={c} onClick={() => { setPath({ ...path, color: c }); saveMeta({ color: c }); }} className="w-7 h-7 rounded-full border" style={{ background: c, borderColor: path.color === c ? "#fff" : "transparent" }} aria-label={c} />
              ))}
            </div>
          </FormRow>
        </div>
      </div>

      {/* Modules */}
      <div className="flex items-center justify-between mt-8 mb-3">
        <h2 className="asc-h2 text-xl">Modules & lessons</h2>
        <button onClick={addModule} className="asc-btn-secondary text-sm" data-testid="add-module-btn"><Plus size={14} /> Add module</button>
      </div>

      <div className="space-y-3">
        {path.modules.map((m, mi) => (
          <div key={m.id} className="asc-card overflow-hidden" data-testid={`module-${m.id}`}>
            <div className="p-4 flex items-center gap-3">
              <button onClick={() => setExpandedModules((s) => ({ ...s, [m.id]: !s[m.id] }))} className="p-1">
                {expandedModules[m.id] ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
              </button>
              <div className="w-7 h-7 rounded-full grid place-items-center font-black text-sm shrink-0" style={{ background: path.color, color: "#000" }}>{mi + 1}</div>
              <div className="flex-1 min-w-0">
                <div className="font-bold truncate">{m.title}</div>
                <div className="text-xs text-[var(--asc-text-muted)]">{(m.lessons || []).length} lessons</div>
              </div>
              <button onClick={() => aiAddLesson(m.id)} className="asc-btn-primary text-xs" data-testid={`ai-add-lesson-${m.id}`}><Sparkles size={12} /> AI Lesson</button>
              <button onClick={() => deleteModule(m.id)} className="asc-btn-secondary text-xs"><Trash2 size={12} /></button>
            </div>
            {expandedModules[m.id] && (
              <div className="border-t border-[var(--asc-border)] divide-y divide-[var(--asc-border)]">
                {(m.lessons || []).map((lsn) => (
                  <div key={lsn.id} className="p-3 flex items-center gap-3" data-testid={`lesson-row-${lsn.id}`}>
                    <div className="w-9 h-9 rounded-lg grid place-items-center shrink-0" style={{ background: "rgba(255,176,0,0.15)" }}><Sparkles size={14} color="#FFB000" /></div>
                    <div className="flex-1 min-w-0">
                      <div className="font-bold truncate text-sm">{lsn.title}</div>
                      <div className="text-xs text-[var(--asc-text-muted)]">{(lsn.cards || []).length} cards · {lsn.duration_min} min · {lsn.xp} XP</div>
                    </div>
                    <button onClick={() => setEditingLesson({ ...lsn, _module_id: m.id })} className="asc-btn-secondary text-xs" data-testid={`edit-lesson-${lsn.id}`}><Edit3 size={12} /></button>
                    <button onClick={() => refreshLessonAI(m.id, lsn.id)} className="asc-btn-secondary text-xs" title="AI refresh for 2026" data-testid={`refresh-lesson-${lsn.id}`}><RefreshCw size={12} /></button>
                    <button onClick={() => deleteLesson(m.id, lsn.id)} className="asc-btn-secondary text-xs"><Trash2 size={12} /></button>
                  </div>
                ))}
                {(m.lessons || []).length === 0 && (
                  <div className="p-4 text-center text-sm text-[var(--asc-text-muted)]">No lessons yet. Click “AI Lesson” to generate one.</div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>

      {editingLesson && (
        <LessonEditor
          pathId={pathId}
          lesson={editingLesson}
          onClose={() => setEditingLesson(null)}
          onSaved={() => { setEditingLesson(null); load(); }}
        />
      )}
    </div>
  );
}

function FormRow({ label, children }) {
  return (
    <div>
      <div className="asc-label mb-1">{label}</div>
      {children}
    </div>
  );
}

function LessonEditor({ pathId, lesson, onClose, onSaved }) {
  const moduleId = lesson._module_id;
  const [title, setTitle] = useState(lesson.title || "");
  const [duration, setDuration] = useState(lesson.duration_min || 5);
  const [xp, setXp] = useState(lesson.xp || 50);
  const [cards, setCards] = useState(lesson.cards || []);
  const [quiz, setQuiz] = useState(lesson.quiz || { question: "", options: ["", "", "", ""], answer_index: 0, explanation: "" });
  const [busy, setBusy] = useState(false);

  const save = async () => {
    setBusy(true);
    try {
      await api.patch(`/admin/curriculum/paths/${pathId}/modules/${moduleId}/lessons/${lesson.id}`, { title, duration_min: Number(duration), xp: Number(xp), cards, quiz });
      toast.success("Lesson saved");
      onSaved();
    } catch (e) { toast.error(e.message); }
    finally { setBusy(false); }
  };

  return (
    <div className="fixed inset-0 z-50 grid place-items-center p-4" style={{ background: "rgba(10,4,19,0.85)" }} onClick={onClose}>
      <div className="asc-card max-w-2xl w-full max-h-[90vh] overflow-y-auto p-6" onClick={(e) => e.stopPropagation()} data-testid="lesson-editor-modal">
        <div className="flex items-center justify-between mb-4">
          <h3 className="asc-h2 text-xl">Edit lesson</h3>
          <button onClick={onClose} className="text-2xl px-2">×</button>
        </div>
        <div className="space-y-3">
          <FormRow label="Title"><input className="asc-input" value={title} onChange={(e) => setTitle(e.target.value)} data-testid="editor-title" /></FormRow>
          <div className="grid grid-cols-2 gap-3">
            <FormRow label="Duration (min)"><input className="asc-input" type="number" min="1" max="30" value={duration} onChange={(e) => setDuration(e.target.value)} /></FormRow>
            <FormRow label="XP"><input className="asc-input" type="number" min="10" max="200" value={xp} onChange={(e) => setXp(e.target.value)} /></FormRow>
          </div>

          <div className="mt-4">
            <div className="asc-label mb-2">Cards ({cards.length})</div>
            {cards.map((c, i) => (
              <div key={i} className="p-3 rounded-lg mb-2" style={{ background: "#1F183A" }} data-testid={`editor-card-${i}`}>
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-xs text-[var(--asc-text-muted)] font-bold">CARD {i + 1}</span>
                  <button onClick={() => setCards(cards.filter((_, j) => j !== i))} className="ml-auto text-xs text-[var(--asc-danger)]">Remove</button>
                </div>
                <input className="asc-input mb-2" placeholder="Card title" value={c.title} onChange={(e) => setCards(cards.map((x, j) => j === i ? { ...x, title: e.target.value } : x))} />
                <textarea className="asc-input min-h-[100px]" placeholder="Card body" value={c.body} onChange={(e) => setCards(cards.map((x, j) => j === i ? { ...x, body: e.target.value } : x))} />
              </div>
            ))}
            <button onClick={() => setCards([...cards, { title: "", body: "" }])} className="asc-btn-secondary text-xs"><Plus size={12} /> Add card</button>
          </div>

          <div className="mt-4">
            <div className="asc-label mb-2">Quiz</div>
            <input className="asc-input mb-2" placeholder="Question" value={quiz.question} onChange={(e) => setQuiz({ ...quiz, question: e.target.value })} data-testid="editor-quiz-q" />
            {(quiz.options || []).map((opt, i) => (
              <div key={i} className="flex items-center gap-2 mb-2">
                <input type="radio" checked={quiz.answer_index === i} onChange={() => setQuiz({ ...quiz, answer_index: i })} className="accent-[var(--asc-brand)]" />
                <input className="asc-input flex-1" placeholder={`Option ${String.fromCharCode(65 + i)}`} value={opt} onChange={(e) => setQuiz({ ...quiz, options: quiz.options.map((x, j) => j === i ? e.target.value : x) })} />
              </div>
            ))}
            <textarea className="asc-input min-h-[60px]" placeholder="Explanation (why the correct answer is correct)" value={quiz.explanation || ""} onChange={(e) => setQuiz({ ...quiz, explanation: e.target.value })} />
          </div>

          <button onClick={save} disabled={busy} className="asc-btn-primary w-full justify-center mt-2" data-testid="editor-save"><Save size={14} /> {busy ? "Saving…" : "Save lesson"}</button>
        </div>
      </div>
    </div>
  );
}
