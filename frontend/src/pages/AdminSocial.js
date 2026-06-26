import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, BACKEND_URL } from "@/lib/api";
import Loader from "@/components/Loader";
import { ArrowLeft, Share2, Image, Twitter, Instagram, Music2, Copy, Trash2, Sparkles, Download, Eye } from "lucide-react";
import { toast } from "sonner";
import { formatDate } from "@/lib/utils";

export default function AdminSocial() {
  const nav = useNavigate();
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState(null);
  const [genPath, setGenPath] = useState("");
  const [genModule, setGenModule] = useState("");
  const [genLesson, setGenLesson] = useState("");
  const [paths, setPaths] = useState([]);
  const [busy, setBusy] = useState(false);
  const [showGen, setShowGen] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const [r, p] = await Promise.all([
        api.get("/admin/social/posts"),
        api.get("/admin/curriculum/paths"),
      ]);
      setPosts(r.posts || []);
      setPaths(p.paths || []);
    } catch (e) {
      toast.error(e.message || "Could not load");
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { load(); }, []);

  const generate = async () => {
    if (!genPath || !genModule || !genLesson) { toast.error("Pick a lesson first"); return; }
    setBusy(true);
    toast.info("Generating tweets + carousel + video — this takes 30–90 seconds…");
    try {
      const r = await api.post("/admin/social/generate", { path_id: genPath, module_id: genModule, lesson_id: genLesson, include_video: true });
      toast.success(`Generated: ${r.post.lesson_title}`);
      setShowGen(false);
      load();
    } catch (e) {
      toast.error(e.message || "Generation failed");
    } finally {
      setBusy(false);
    }
  };

  const copyTweet = (txt) => {
    navigator.clipboard?.writeText(txt);
    toast.success("Tweet copied");
  };

  const deletePost = async (id) => {
    if (!confirm("Delete this social post?")) return;
    try {
      await api.del(`/admin/social/post/${id}`);
      toast.success("Deleted");
      load();
    } catch (e) { toast.error(e.message); }
  };

  const selectedPath = paths.find((p) => p.id === genPath);
  const selectedModule = selectedPath?.modules?.find((m) => m.id === genModule);

  return (
    <div className="max-w-7xl mx-auto px-5 sm:px-8 py-10" data-testid="admin-social-page">
      <button onClick={() => nav("/admin")} className="flex items-center gap-1 text-sm text-[var(--asc-text-dim)] hover:text-white mb-3"><ArrowLeft size={14} /> Admin</button>
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="asc-kicker">Distribution</div>
          <h1 className="asc-h2 text-4xl mt-1 flex items-center gap-3"><Share2 size={28} className="text-[var(--asc-brand)]" /> Social Studio</h1>
          <p className="text-[var(--asc-text-dim)] text-sm mt-2 max-w-2xl">Generate tweet threads + Instagram carousels + silent TikTok-ready MP4s for any lesson. <strong className="text-[var(--asc-warn)]">Posting requires you to create the brand accounts + add API tokens</strong> — until then, copy/paste from the previews below.</p>
        </div>
        <button onClick={() => setShowGen(true)} className="asc-btn-primary text-sm" data-testid="social-generate-btn"><Sparkles size={14} /> Generate from lesson</button>
      </div>

      <div className="grid lg:grid-cols-5 gap-6 mt-8">
        {/* List */}
        <div className="lg:col-span-2 space-y-2 max-h-[800px] overflow-y-auto pr-1" data-testid="social-posts-list">
          {loading ? <Loader /> : posts.length === 0 ? (
            <div className="asc-card p-8 text-center" data-testid="social-empty">
              <div className="w-12 h-12 mx-auto rounded-2xl grid place-items-center mb-3" style={{ background: "rgba(255,176,0,0.10)" }}><Share2 size={20} color="#FFB000" /></div>
              <div className="asc-h2 text-lg">Nothing generated yet</div>
              <p className="text-[var(--asc-text-dim)] text-sm mt-2 max-w-md mx-auto">Click "Generate from lesson" to create your first social content pack from any lesson in your curriculum.</p>
            </div>
          ) : posts.map((p) => (
            <button
              key={p.id}
              onClick={() => setSelected(p)}
              className="asc-card p-3 w-full text-left flex items-center gap-3 hover:border-[var(--asc-brand)] transition"
              data-testid={`social-post-${p.id}`}
              style={selected?.id === p.id ? { borderColor: "#FFB000", background: "rgba(255,176,0,0.04)" } : {}}
            >
              <div className="w-10 h-10 rounded-xl grid place-items-center shrink-0" style={{ background: "rgba(124,58,237,0.18)" }}><Share2 size={14} color="#BFB4FF" /></div>
              <div className="flex-1 min-w-0">
                <div className="font-bold text-sm truncate">{p.lesson_title}</div>
                <div className="text-xs text-[var(--asc-text-muted)] truncate">{p.path_title} · {p.slide_count} slides{p.has_video ? " · video" : ""} · {formatDate(p.created_at)}</div>
              </div>
              <button onClick={(e) => { e.stopPropagation(); deletePost(p.id); }} className="text-[var(--asc-text-muted)] hover:text-[#FB7185]" data-testid={`social-delete-${p.id}`}><Trash2 size={14} /></button>
            </button>
          ))}
        </div>

        {/* Detail */}
        <div className="lg:col-span-3">
          {!selected ? (
            <div className="asc-card p-10 text-center text-[var(--asc-text-dim)]">Pick a post to preview tweets, carousel, and video.</div>
          ) : (
            <div className="space-y-6" data-testid="social-detail">
              <div>
                <div className="asc-kicker">Lesson</div>
                <div className="asc-h2 text-2xl mt-1">{selected.lesson_title}</div>
                <div className="text-sm text-[var(--asc-text-muted)] mt-1">{selected.path_title}</div>
              </div>

              {/* Twitter */}
              <section>
                <h3 className="asc-h2 text-lg flex items-center gap-2 mb-3"><Twitter size={16} className="text-[var(--asc-brand)]" /> Twitter/X thread</h3>
                <div className="space-y-2">
                  {(selected.tweets || []).map((t, i) => (
                    <div key={i} className="asc-card p-3 flex items-start gap-2" data-testid={`social-tweet-${i}`}>
                      <span className="text-[10px] font-bold text-[var(--asc-text-muted)] asc-mono w-6 shrink-0 mt-0.5">{i + 1}/{selected.tweets.length}</span>
                      <p className="text-sm flex-1 whitespace-pre-wrap">{t}</p>
                      <button onClick={() => copyTweet(t)} className="text-[var(--asc-text-muted)] hover:text-white shrink-0" data-testid={`social-copy-tweet-${i}`}><Copy size={14} /></button>
                    </div>
                  ))}
                </div>
                {selected.hashtags?.length > 0 && (
                  <div className="text-xs text-[var(--asc-text-muted)] mt-2 asc-mono">{selected.hashtags.join(" ")}</div>
                )}
              </section>

              {/* Instagram carousel */}
              <section>
                <h3 className="asc-h2 text-lg flex items-center gap-2 mb-3"><Instagram size={16} className="text-[var(--asc-brand)]" /> Instagram / LinkedIn carousel</h3>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                  {Array.from({ length: selected.slide_count || 0 }).map((_, i) => {
                    const token = localStorage.getItem("ascendra_token");
                    const url = `${BACKEND_URL.replace(/\/$/, "")}/api/admin/social/post/${selected.id}/slide/${i}.png`;
                    return (
                      <a key={i} href={`${url}?t=${token?.slice(-8)}`} target="_blank" rel="noopener noreferrer" className="asc-card overflow-hidden block aspect-square relative group" data-testid={`social-slide-${i}`}>
                        <AuthedImage src={url} alt={`Slide ${i + 1}`} />
                        <div className="absolute bottom-1 right-1 text-[10px] px-1.5 py-0.5 rounded font-bold" style={{ background: "rgba(0,0,0,0.6)", color: "#fff" }}>{i + 1}</div>
                      </a>
                    );
                  })}
                </div>
                {selected.caption && (
                  <div className="asc-card p-4 mt-3">
                    <div className="asc-kicker mb-2 flex items-center justify-between">
                      <span>Caption</span>
                      <button onClick={() => copyTweet(selected.caption)} className="text-[var(--asc-text-muted)] hover:text-white" data-testid="social-copy-caption"><Copy size={14} /></button>
                    </div>
                    <p className="text-sm whitespace-pre-wrap text-[var(--asc-text-dim)]">{selected.caption}</p>
                  </div>
                )}
              </section>

              {/* Video */}
              {selected.has_video && (
                <section>
                  <h3 className="asc-h2 text-lg flex items-center gap-2 mb-3"><Music2 size={16} className="text-[var(--asc-brand)]" /> TikTok / Reels video</h3>
                  <p className="text-xs text-[var(--asc-text-dim)] mb-3">Silent 1080x1080 MP4 stitched from the carousel slides. Add your own music or voiceover in your platform editor.</p>
                  <AuthedVideo postId={selected.id} />
                </section>
              )}

              {/* Platform status (gated on tokens) */}
              <section className="asc-card p-4">
                <div className="asc-kicker mb-2">Posting status</div>
                <p className="text-xs text-[var(--asc-text-dim)]">Auto-posting requires brand accounts + API tokens for each platform. Until you set those up, copy the content above and post manually.</p>
                <div className="grid grid-cols-3 gap-2 mt-3 text-xs">
                  <PlatformPill icon={Twitter} label="Twitter/X" status="manual" />
                  <PlatformPill icon={Instagram} label="Instagram" status="manual" />
                  <PlatformPill icon={Music2} label="TikTok" status="manual" />
                </div>
              </section>
            </div>
          )}
        </div>
      </div>

      {/* Generate modal */}
      {showGen && (
        <div className="fixed inset-0 z-50 grid place-items-center p-4" style={{ background: "rgba(0,0,0,0.78)", backdropFilter: "blur(8px)" }} onClick={() => setShowGen(false)}>
          <div className="asc-card w-full max-w-lg p-6" onClick={(e) => e.stopPropagation()}>
            <h2 className="asc-h2 text-xl mb-3">Generate social content</h2>
            <p className="text-sm text-[var(--asc-text-dim)] mb-4">Pick a lesson. We'll generate a 5-tweet thread, 5-slide carousel (PNG images), and a silent MP4. Takes 30–90 seconds.</p>
            <label className="asc-label">Path</label>
            <select className="asc-input w-full mt-1" value={genPath} onChange={(e) => { setGenPath(e.target.value); setGenModule(""); setGenLesson(""); }} data-testid="social-gen-path">
              <option value="">Select a path…</option>
              {paths.map((p) => <option key={p.id} value={p.id}>{p.title}</option>)}
            </select>
            {selectedPath && (
              <>
                <label className="asc-label mt-3 block">Module</label>
                <select className="asc-input w-full mt-1" value={genModule} onChange={(e) => { setGenModule(e.target.value); setGenLesson(""); }} data-testid="social-gen-module">
                  <option value="">Select a module…</option>
                  {selectedPath.modules.map((m) => <option key={m.id} value={m.id}>{m.title}</option>)}
                </select>
              </>
            )}
            {selectedModule && (
              <>
                <label className="asc-label mt-3 block">Lesson</label>
                <select className="asc-input w-full mt-1" value={genLesson} onChange={(e) => setGenLesson(e.target.value)} data-testid="social-gen-lesson">
                  <option value="">Select a lesson…</option>
                  {selectedModule.lessons.map((l) => <option key={l.id} value={l.id}>{l.title}</option>)}
                </select>
              </>
            )}
            <div className="flex justify-end gap-2 mt-5">
              <button onClick={() => setShowGen(false)} className="asc-btn-secondary text-sm">Cancel</button>
              <button onClick={generate} disabled={busy || !genLesson} className="asc-btn-primary text-sm" data-testid="social-gen-confirm">{busy ? "Generating…" : "Generate"}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function AuthedImage({ src, alt }) {
  // The /api/admin/social endpoints require Bearer auth — we fetch + create blob URL
  const [url, setUrl] = useState(null);
  useEffect(() => {
    let cancel = false;
    const token = localStorage.getItem("ascendra_token");
    fetch(src, { headers: { Authorization: `Bearer ${token}` } })
      .then((r) => r.blob())
      .then((blob) => {
        if (!cancel) setUrl(URL.createObjectURL(blob));
      })
      .catch(() => {});
    return () => {
      cancel = true;
      if (url) URL.revokeObjectURL(url);
    };
    // eslint-disable-next-line
  }, [src]);
  if (!url) return <div className="w-full h-full bg-[#15102B] animate-pulse" />;
  return <img src={url} alt={alt} className="w-full h-full object-cover" loading="lazy" />;
}

function AuthedVideo({ postId }) {
  const [url, setUrl] = useState(null);
  useEffect(() => {
    let cancel = false;
    const token = localStorage.getItem("ascendra_token");
    fetch(`${BACKEND_URL.replace(/\/$/, "")}/api/admin/social/post/${postId}/video.mp4`, { headers: { Authorization: `Bearer ${token}` } })
      .then((r) => r.blob())
      .then((blob) => {
        if (!cancel) setUrl(URL.createObjectURL(blob));
      })
      .catch(() => {});
    return () => { cancel = true; if (url) URL.revokeObjectURL(url); };
    // eslint-disable-next-line
  }, [postId]);
  if (!url) return <div className="w-full max-w-sm aspect-square bg-[#15102B] animate-pulse rounded-2xl" />;
  return (
    <div className="space-y-2">
      <video src={url} controls className="rounded-2xl border border-[var(--asc-border)] w-full max-w-sm" data-testid="social-video-player" />
      <a href={url} download={`ascendra-${postId.slice(0, 8)}.mp4`} className="asc-btn-secondary text-xs inline-flex" data-testid="social-video-download"><Download size={12} /> Download MP4</a>
    </div>
  );
}

function PlatformPill({ icon: Icon, label, status }) {
  return (
    <div className="asc-card p-2 flex items-center justify-center gap-1.5">
      <Icon size={12} className="text-[var(--asc-text-muted)]" />
      <span className="font-bold">{label}</span>
      <span className="text-[10px] text-[var(--asc-text-muted)]">{status}</span>
    </div>
  );
}
