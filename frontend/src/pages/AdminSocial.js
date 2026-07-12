import { useEffect, useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { api, BACKEND_URL } from "@/lib/api";
import Loader from "@/components/Loader";
import {
  ArrowLeft, Share2, Twitter, Instagram, Music2, Copy, Trash2, Sparkles,
  Download, Send, ExternalLink, Settings, CheckCircle2, AlertCircle, Facebook,
} from "lucide-react";
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
  const [settings, setSettings] = useState(null);
  const [metaStatus, setMetaStatus] = useState(null);
  const [tiktokStatus, setTiktokStatus] = useState(null);
  const [xBudget, setXBudget] = useState(null);
  const [posting, setPosting] = useState(null); // "x" | "facebook" | "instagram" | "tiktok" | null

  const load = async () => {
    setLoading(true);
    try {
      const [r, p, s, m, t, b] = await Promise.all([
        api.get("/admin/social/posts"),
        api.get("/admin/curriculum/paths"),
        api.get("/admin/social/settings").catch(() => null),
        api.get("/admin/social/meta/status").catch(() => null),
        api.get("/admin/social/tiktok/status").catch(() => null),
        api.get("/admin/social/x/budget").catch(() => null),
      ]);
      setPosts(r.posts || []);
      setPaths(p.paths || []);
      if (s) setSettings(s);
      setMetaStatus(m);
      setTiktokStatus(t);
      setXBudget(b);
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

  const copyText = (txt, label = "Copied") => {
    navigator.clipboard?.writeText(txt);
    toast.success(label);
  };

  const deletePost = async (id) => {
    if (!confirm("Delete this social post?")) return;
    try {
      await api.del(`/admin/social/post/${id}`);
      toast.success("Deleted");
      if (selected?.id === id) setSelected(null);
      load();
    } catch (e) { toast.error(e.message); }
  };

  const postToX = async () => {
    if (!selected) return;
    if (xBudget?.month?.blocked) { toast.error("Monthly X budget exhausted. Resets on the 1st."); return; }
    if (xBudget?.day?.blocked) { toast.error("Daily X posting cap hit. Try again tomorrow."); return; }
    if (!confirm(`Post this thread live to X as @${settings?.x?.handle || "your brand"}? This cannot be undone.\n\nThis will use ${selected.tweets?.length || 5} of your ${xBudget?.month?.remaining ?? "?"} remaining X posts this month.`)) return;
    setPosting("x");
    try {
      const r = await api.post(`/admin/social/post/${selected.id}/post-to-x`, {});
      toast.success(`Posted ${r.count} tweets to X! ${r.budget_after ? `${r.budget_after.month.remaining} posts left this month.` : ""}`);
      if (r.budget_after) setXBudget(r.budget_after);
      if (r.first_url) {
        window.open(r.first_url, "_blank", "noopener,noreferrer");
      }
      load();
    } catch (e) {
      toast.error(e.message || "Post to X failed");
    } finally {
      setPosting(null);
    }
  };

  const postToFacebook = async () => {
    if (!selected) return;
    if (!confirm(`Post to Facebook Page "${metaStatus?.fb_page_name || "your Page"}"? This publishes immediately.`)) return;
    setPosting("facebook");
    try {
      const r = await api.post(`/admin/social/post/${selected.id}/post-to-facebook`, {});
      toast.success("Posted to Facebook!");
      if (r.url) window.open(r.url, "_blank", "noopener,noreferrer");
      load();
    } catch (e) {
      toast.error(e.message || "Post to Facebook failed");
    } finally {
      setPosting(null);
    }
  };

  const postToInstagram = async (asReel = false) => {
    if (!selected) return;
    const kind = asReel ? "Reel" : "carousel";
    if (!confirm(`Post ${kind} to Instagram Business account? This publishes immediately.`)) return;
    setPosting("instagram");
    try {
      const r = await api.post(`/admin/social/post/${selected.id}/post-to-instagram?as_reel=${asReel}`, {});
      toast.success(`Posted ${kind} to Instagram!`);
      if (r.url) window.open(r.url, "_blank", "noopener,noreferrer");
      load();
    } catch (e) {
      toast.error(e.message || "Post to Instagram failed");
    } finally {
      setPosting(null);
    }
  };

  const postToTikTok = async (privacy = "SELF_ONLY") => {
    if (!selected) return;
    const canPublic = tiktokStatus?.verify?.can_public;
    if (privacy === "PUBLIC_TO_EVERYONE" && !canPublic) {
      toast.error("Public posting requires TikTok App Audit approval. Falling back to SELF_ONLY.");
      privacy = "SELF_ONLY";
    }
    if (!confirm(`Post video to TikTok with privacy = ${privacy}? Video will appear on your TikTok account.`)) return;
    setPosting("tiktok");
    try {
      const r = await api.post(`/admin/social/post/${selected.id}/post-to-tiktok`, { privacy });
      toast.success(`TikTok publish started. ID: ${r.publish_id?.slice(0, 8)}…`);
      load();
    } catch (e) {
      toast.error(e.message || "Post to TikTok failed");
    } finally {
      setPosting(null);
    }
  };

  const downloadSlide = async (idx) => {
    if (!selected) return;
    try {
      const token = localStorage.getItem("ascendra_token");
      const url = `${BACKEND_URL.replace(/\/$/, "")}/api/admin/social/post/${selected.id}/slide/${idx}.png`;
      const resp = await fetch(url, { headers: { Authorization: `Bearer ${token}` } });
      const blob = await resp.blob();
      const objectUrl = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = objectUrl;
      a.download = `ascendra-slide-${idx + 1}.png`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(objectUrl);
    } catch (e) { toast.error("Download failed"); }
  };

  const downloadAllSlides = async () => {
    if (!selected) return;
    toast.info(`Downloading ${selected.slide_count} slides…`);
    for (let i = 0; i < (selected.slide_count || 0); i++) {
      await downloadSlide(i);
      await new Promise((r) => setTimeout(r, 250));
    }
    toast.success("Slides downloaded. Upload them to your platform in order.");
  };

  const downloadVideo = async () => {
    if (!selected?.has_video) return;
    try {
      const token = localStorage.getItem("ascendra_token");
      const url = `${BACKEND_URL.replace(/\/$/, "")}/api/admin/social/post/${selected.id}/video.mp4`;
      const resp = await fetch(url, { headers: { Authorization: `Bearer ${token}` } });
      const blob = await resp.blob();
      const objectUrl = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = objectUrl;
      a.download = `ascendra-${selected.id.slice(0, 8)}.mp4`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(objectUrl);
    } catch (e) { toast.error("Download failed"); }
  };

  const selectedPath = paths.find((p) => p.id === genPath);
  const selectedModule = selectedPath?.modules?.find((m) => m.id === genModule);

  // Compose platform-tailored copy blocks
  const composeThreadText = () => {
    if (!selected) return "";
    const t = selected.tweets || [];
    const tags = (selected.hashtags || []).join(" ");
    return t.map((tw, i) => `${i + 1}/${t.length} ${tw}`).join("\n\n") + (tags ? `\n\n${tags}` : "");
  };
  const composeCaption = (withHashtags = true) => {
    if (!selected) return "";
    const cap = selected.caption || "";
    const tags = withHashtags ? (selected.hashtags || []).join(" ") : "";
    return tags ? `${cap}\n\n${tags}` : cap;
  };

  return (
    <div className="max-w-7xl mx-auto px-5 sm:px-8 py-10" data-testid="admin-social-page">
      <button onClick={() => nav("/admin")} className="flex items-center gap-1 text-sm text-[var(--asc-text-dim)] hover:text-white mb-3"><ArrowLeft size={14} /> Admin</button>
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="asc-kicker">Distribution</div>
          <h1 className="asc-h2 text-4xl mt-1 flex items-center gap-3"><Share2 size={28} className="text-[var(--asc-brand)]" /> Social Studio</h1>
          <p className="text-[var(--asc-text-dim)] text-sm mt-2 max-w-2xl">Generate tweet threads + Instagram carousels + silent TikTok-ready MP4s for any lesson. Post to X automatically, or copy/download for FB, IG, and TikTok until their APIs are configured.</p>
        </div>
        <div className="flex gap-2">
          <Link to="/admin/social/settings" className="asc-btn-secondary text-sm" data-testid="social-settings-link"><Settings size={14} /> Platform Settings</Link>
          <button onClick={() => setShowGen(true)} className="asc-btn-primary text-sm" data-testid="social-generate-btn"><Sparkles size={14} /> Generate from lesson</button>
        </div>
      </div>

      {/* Global platform status strip (Facebook + Instagram disabled per user request 2026-07-12) */}
      {settings && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2 mt-6" data-testid="social-platform-strip">
          <PlatformStatusChip icon={Twitter} label="X" cfg={settings.x} />
          <PlatformStatusChip icon={Music2} label="TikTok" cfg={{ ...(settings.tiktok || {}), auto_post: !!tiktokStatus?.connected, configured: !!tiktokStatus?.connected || !!settings.tiktok?.configured }} />
        </div>
      )}

      <div className="grid lg:grid-cols-5 gap-6 mt-6">
        {/* List */}
        <div className="lg:col-span-2 space-y-2 max-h-[800px] overflow-y-auto pr-1" data-testid="social-posts-list">
          {loading ? <Loader /> : posts.length === 0 ? (
            <div className="asc-card p-8 text-center" data-testid="social-empty">
              <div className="w-12 h-12 mx-auto rounded-2xl grid place-items-center mb-3" style={{ background: "rgba(255,176,0,0.10)" }}><Share2 size={20} color="#FFB000" /></div>
              <div className="asc-h2 text-lg">Nothing generated yet</div>
              <p className="text-[var(--asc-text-dim)] text-sm mt-2 max-w-md mx-auto">Click &ldquo;Generate from lesson&rdquo; to create your first social content pack from any lesson in your curriculum.</p>
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
                <div className="flex gap-1 mt-1">
                  {p.platforms?.twitter === "posted" && <span className="text-[9px] px-1.5 py-0.5 rounded font-bold" style={{ background: "rgba(29,161,242,0.18)", color: "#7CD1FF" }}>X POSTED</span>}
                  {p.platforms?.facebook === "posted" && <span className="text-[9px] px-1.5 py-0.5 rounded font-bold" style={{ background: "rgba(66,103,178,0.18)", color: "#93B7FF" }}>FB POSTED</span>}
                  {p.platforms?.instagram === "posted" && <span className="text-[9px] px-1.5 py-0.5 rounded font-bold" style={{ background: "rgba(228,64,95,0.18)", color: "#FF9CB0" }}>IG POSTED</span>}
                  {p.platforms?.tiktok === "posted" && <span className="text-[9px] px-1.5 py-0.5 rounded font-bold" style={{ background: "rgba(255,255,255,0.10)", color: "#fff" }}>TT POSTED</span>}
                </div>
              </div>
              <button onClick={(e) => { e.stopPropagation(); deletePost(p.id); }} className="text-[var(--asc-text-muted)] hover:text-[#FB7185]" data-testid={`social-delete-${p.id}`}><Trash2 size={14} /></button>
            </button>
          ))}
        </div>

        {/* Detail */}
        <div className="lg:col-span-3">
          {!selected ? (
            <div className="asc-card p-10 text-center text-[var(--asc-text-dim)]">Pick a post to preview and distribute.</div>
          ) : (
            <div className="space-y-6" data-testid="social-detail">
              <div>
                <div className="asc-kicker">Lesson</div>
                <div className="asc-h2 text-2xl mt-1">{selected.lesson_title}</div>
                <div className="text-sm text-[var(--asc-text-muted)] mt-1">{selected.path_title}</div>
              </div>

              {/* Assets preview */}
              <section className="asc-card p-4">
                <div className="asc-kicker mb-3">Assets · {selected.slide_count} slides{selected.has_video ? " · 1 video" : ""}</div>
                <div className="grid grid-cols-3 sm:grid-cols-5 gap-2">
                  {Array.from({ length: selected.slide_count || 0 }).map((_, i) => {
                    const url = `${BACKEND_URL.replace(/\/$/, "")}/api/admin/social/post/${selected.id}/slide/${i}.png`;
                    return (
                      <div key={i} className="aspect-square rounded-lg overflow-hidden border border-[var(--asc-border)]" data-testid={`social-slide-${i}`}>
                        <AuthedImage src={url} alt={`Slide ${i + 1}`} />
                      </div>
                    );
                  })}
                </div>
                {selected.has_video && <AuthedVideo postId={selected.id} />}
              </section>

              {/* Distribution Panel — 4 platform cards */}
              <section>
                <div className="asc-kicker mb-3 flex items-center gap-2"><Send size={12} /> Distribute</div>
                <div className="grid md:grid-cols-2 gap-3">
                  {/* X / Twitter */}
                  <PlatformCard
                    testId="platform-card-x"
                    icon={Twitter}
                    iconColor="#7CD1FF"
                    accent="rgba(29,161,242,0.14)"
                    label="X (Twitter)"
                    cfg={settings?.x}
                    alreadyPosted={selected.platforms?.twitter === "posted"}
                    postedUrl={selected.x_first_url}
                    primary={settings?.x?.auto_post ? {
                      label: posting === "x" ? "Posting…"
                        : selected.platforms?.twitter === "posted" ? "Posted ✓"
                        : xBudget?.month?.blocked ? "Budget exhausted"
                        : xBudget?.day?.blocked ? "Daily cap hit"
                        : `Post Thread Live${xBudget?.month?.remaining != null ? ` (${xBudget.month.remaining} left)` : ""}`,
                      onClick: postToX,
                      disabled: !!posting || selected.platforms?.twitter === "posted"
                                || !!xBudget?.month?.blocked || !!xBudget?.day?.blocked,
                      testId: "platform-x-post-btn",
                      icon: Send,
                    } : null}
                    hint={xBudget?.month?.warn && !xBudget.month.blocked ? `⚠️ Only ${xBudget.month.remaining} X posts left this month (free tier). Consider spacing them out.` : undefined}
                    actions={[
                      { label: "Copy Thread", onClick: () => copyText(composeThreadText(), "Thread copied"), icon: Copy, testId: "platform-x-copy-thread" },
                      { label: "Compose in X", onClick: () => window.open(`https://twitter.com/intent/tweet?text=${encodeURIComponent((selected.tweets?.[0] || "") + "\n\n" + (selected.hashtags || []).join(" "))}`, "_blank", "noopener,noreferrer"), icon: ExternalLink, testId: "platform-x-compose" },
                    ]}
                  />

                  {/* Facebook + Instagram cards removed per user request 2026-07-12.
                      Backend code + endpoints preserved. To re-enable, restore the two
                      <PlatformCard> blocks that used metaStatus + postToFacebook/postToInstagram. */}

                  {/* TikTok */}
                  <PlatformCard
                    testId="platform-card-tiktok"
                    icon={Music2}
                    iconColor="#FFFFFF"
                    accent="rgba(255,255,255,0.10)"
                    label="TikTok"
                    cfg={{ auto_post: !!tiktokStatus?.connected, configured: !!tiktokStatus?.connected }}
                    alreadyPosted={selected.platforms?.tiktok === "posted"}
                    primary={tiktokStatus?.connected && selected.has_video ? {
                      label: posting === "tiktok" ? "Posting…" : (selected.platforms?.tiktok === "posted" ? "Posted ✓" : "Post to TikTok (Private)"),
                      onClick: () => postToTikTok("SELF_ONLY"),
                      disabled: !!posting || selected.platforms?.tiktok === "posted",
                      testId: "platform-tt-post-btn",
                      icon: Send,
                    } : null}
                    secondary={tiktokStatus?.verify?.can_public && selected.has_video ? {
                      label: posting === "tiktok" ? "Posting…" : "Post Publicly",
                      onClick: () => postToTikTok("PUBLIC_TO_EVERYONE"),
                      disabled: !!posting || selected.platforms?.tiktok === "posted",
                      testId: "platform-tt-post-public-btn",
                      icon: Send,
                    } : null}
                    hint={!tiktokStatus?.connected ? "Connect TikTok in Platform Settings first." : (!selected.has_video ? "No video generated — regenerate with video enabled." : (!tiktokStatus.verify?.can_public ? "Sandbox / pre-audit posts default to SELF_ONLY (private on your profile). Public posting unlocks after App Audit." : "Add music or voiceover in TikTok's editor after upload."))}
                    actions={[
                      selected.has_video ? { label: "Download MP4", onClick: downloadVideo, icon: Download, testId: "platform-tt-download-mp4" } : null,
                      { label: "Copy Caption", onClick: () => copyText(composeCaption(true), "Caption copied"), icon: Copy, testId: "platform-tt-copy-caption" },
                      { label: "Open TikTok Upload", onClick: () => window.open("https://www.tiktok.com/upload", "_blank", "noopener,noreferrer"), icon: ExternalLink, testId: "platform-tt-open" },
                    ].filter(Boolean)}
                  />
                </div>
              </section>

              {/* Raw content preview (expandable text) */}
              <details className="asc-card p-4" data-testid="social-raw-content">
                <summary className="cursor-pointer text-sm font-bold">Raw generated content (tweets + caption)</summary>
                <div className="mt-3 space-y-4">
                  <div>
                    <div className="asc-kicker mb-2">Thread</div>
                    <div className="space-y-2">
                      {(selected.tweets || []).map((t, i) => (
                        <div key={i} className="flex items-start gap-2 text-sm">
                          <span className="text-[10px] font-bold text-[var(--asc-text-muted)] asc-mono w-6 shrink-0 mt-0.5">{i + 1}/{selected.tweets.length}</span>
                          <p className="flex-1 whitespace-pre-wrap">{t}</p>
                          <button onClick={() => copyText(t, "Tweet copied")} className="text-[var(--asc-text-muted)] hover:text-white shrink-0" data-testid={`social-copy-tweet-${i}`}><Copy size={13} /></button>
                        </div>
                      ))}
                    </div>
                    {selected.hashtags?.length > 0 && (
                      <div className="text-xs text-[var(--asc-text-muted)] mt-2 asc-mono">{selected.hashtags.join(" ")}</div>
                    )}
                  </div>
                  {selected.caption && (
                    <div>
                      <div className="asc-kicker mb-2 flex items-center justify-between"><span>Caption</span><button onClick={() => copyText(selected.caption, "Caption copied")} className="text-[var(--asc-text-muted)] hover:text-white" data-testid="social-copy-caption"><Copy size={13} /></button></div>
                      <p className="text-sm whitespace-pre-wrap text-[var(--asc-text-dim)]">{selected.caption}</p>
                    </div>
                  )}
                </div>
              </details>
            </div>
          )}
        </div>
      </div>

      {/* Generate modal */}
      {showGen && (
        <div className="fixed inset-0 z-50 grid place-items-center p-4" style={{ background: "rgba(0,0,0,0.78)", backdropFilter: "blur(8px)" }} onClick={() => setShowGen(false)}>
          <div className="asc-card w-full max-w-lg p-6" onClick={(e) => e.stopPropagation()}>
            <h2 className="asc-h2 text-xl mb-3">Generate social content</h2>
            <p className="text-sm text-[var(--asc-text-dim)] mb-4">Pick a lesson. We’ll generate a 5-tweet thread, 5-slide carousel (PNG images), and a silent MP4. Takes 30–90 seconds.</p>
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

function PlatformStatusChip({ icon: Icon, label, cfg }) {
  const ready = !!cfg?.auto_post;
  const configured = !!cfg?.configured;
  const color = ready ? "#4ADE80" : (configured ? "#FFB000" : "#8A83B8");
  const bg = ready ? "rgba(74,222,128,0.10)" : (configured ? "rgba(255,176,0,0.10)" : "rgba(138,131,184,0.08)");
  const status = ready ? "Auto ready" : (configured ? "Needs verify" : "Manual");
  return (
    <Link
      to="/admin/social/settings"
      className="asc-card px-3 py-2 flex items-center gap-2 hover:border-[var(--asc-brand)] transition"
      style={{ background: bg, borderColor: `${color}33` }}
      data-testid={`platform-chip-${label.toLowerCase().replace(/[^a-z]/g, "")}`}
    >
      <Icon size={14} style={{ color }} />
      <div className="flex-1 min-w-0">
        <div className="text-xs font-bold truncate">{label}</div>
        <div className="text-[10px] uppercase tracking-wider" style={{ color }}>{status}</div>
      </div>
      {ready ? <CheckCircle2 size={12} style={{ color }} /> : <Settings size={11} className="text-[var(--asc-text-muted)]" />}
    </Link>
  );
}

function PlatformCard({ testId, icon: Icon, iconColor, accent, label, cfg, primary, secondary, actions = [], hint, alreadyPosted, postedUrl }) {
  const ready = !!cfg?.auto_post;
  return (
    <div className="asc-card p-4 flex flex-col gap-3" data-testid={testId}>
      <div className="flex items-center gap-2">
        <div className="w-8 h-8 rounded-lg grid place-items-center shrink-0" style={{ background: accent }}>
          <Icon size={16} style={{ color: iconColor }} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="font-bold text-sm">{label}</div>
          <div className="text-[10px] uppercase tracking-wider" style={{ color: ready ? "#4ADE80" : "#8A83B8" }}>
            {alreadyPosted ? "Posted ✓" : (ready ? "Auto ready" : "Manual mode")}
          </div>
        </div>
        {alreadyPosted && postedUrl && (
          <a href={postedUrl} target="_blank" rel="noopener noreferrer" className="text-[var(--asc-text-muted)] hover:text-white" data-testid={`${testId}-view`}>
            <ExternalLink size={13} />
          </a>
        )}
      </div>

      {primary && (
        <button
          onClick={primary.onClick}
          disabled={primary.disabled}
          className="asc-btn-primary text-sm w-full disabled:opacity-50"
          data-testid={primary.testId}
        >
          {primary.icon && <primary.icon size={13} />} {primary.label}
        </button>
      )}

      {secondary && (
        <button
          onClick={secondary.onClick}
          disabled={secondary.disabled}
          className="asc-btn-secondary text-sm w-full disabled:opacity-50"
          data-testid={secondary.testId}
        >
          {secondary.icon && <secondary.icon size={13} />} {secondary.label}
        </button>
      )}

      <div className="grid grid-cols-1 gap-1.5">
        {actions.map((a, i) => (
          <button
            key={i}
            onClick={a.onClick}
            className="asc-btn-secondary text-xs justify-start"
            data-testid={a.testId}
          >
            <a.icon size={12} /> {a.label}
          </button>
        ))}
      </div>

      {hint && (
        <div className="text-[10px] text-[var(--asc-text-muted)] leading-relaxed flex items-start gap-1">
          <AlertCircle size={10} className="shrink-0 mt-0.5" /> {hint}
        </div>
      )}
    </div>
  );
}

function AuthedImage({ src, alt }) {
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [postId]);
  if (!url) return <div className="w-full max-w-xs aspect-square bg-[#15102B] animate-pulse rounded-2xl mt-3" />;
  return (
    <video src={url} controls className="rounded-2xl border border-[var(--asc-border)] w-full max-w-xs mt-3" data-testid="social-video-player" />
  );
}
