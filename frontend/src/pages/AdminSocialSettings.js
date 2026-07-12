import { useEffect, useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { api } from "@/lib/api";
import Loader from "@/components/Loader";
import {
  ArrowLeft, Settings, CheckCircle2, XCircle, Twitter, Instagram, Music2,
  Facebook, ExternalLink, Copy, RefreshCcw, Shield, AlertTriangle, Link as LinkIcon,
} from "lucide-react";
import { toast } from "sonner";

export default function AdminSocialSettings() {
  const nav = useNavigate();
  const [loading, setLoading] = useState(true);
  const [settings, setSettings] = useState(null);
  const [metaStatus, setMetaStatus] = useState(null);
  const [tiktokStatus, setTiktokStatus] = useState(null);
  const [xBudget, setXBudget] = useState(null);
  const [xTesting, setXTesting] = useState(false);
  const [connecting, setConnecting] = useState(null); // "meta" | "tiktok" | null

  const load = async () => {
    setLoading(true);
    try {
      const [s, m, t, b] = await Promise.all([
        api.get("/admin/social/settings"),
        api.get("/admin/social/meta/status").catch(() => null),
        api.get("/admin/social/tiktok/status").catch(() => null),
        api.get("/admin/social/x/budget").catch(() => null),
      ]);
      setSettings(s);
      setMetaStatus(m);
      setTiktokStatus(t);
      setXBudget(b);
    } catch (e) {
      toast.error(e.message || "Could not load settings");
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => {
    load();
    // Handle OAuth return from Meta/TikTok
    const params = new URLSearchParams(window.location.search);
    const connected = params.get("connected");
    const status = params.get("status");
    const msg = params.get("msg");
    if (connected) {
      if (status === "success") {
        toast.success(`${connected === "meta" ? "Meta" : "TikTok"} connected. ${msg || ""}`);
      } else {
        toast.error(`${connected === "meta" ? "Meta" : "TikTok"} connection failed: ${msg || "Unknown error"}`);
      }
      // Clean the URL
      window.history.replaceState({}, document.title, "/admin/social/settings");
    }
  }, []);

  const connectMeta = async () => {
    setConnecting("meta");
    try {
      const r = await api.get("/admin/social/meta/auth-url");
      window.location.href = r.url;
    } catch (e) {
      toast.error(e.message || "Could not start Meta connect flow");
      setConnecting(null);
    }
  };

  const connectTikTok = async () => {
    setConnecting("tiktok");
    try {
      const r = await api.get("/admin/social/tiktok/auth-url");
      window.location.href = r.url;
    } catch (e) {
      toast.error(e.message || "Could not start TikTok connect flow");
      setConnecting(null);
    }
  };

  const disconnectMeta = async () => {
    if (!confirm("Disconnect Meta? This removes the stored Page Access Token. You can reconnect any time.")) return;
    try {
      await api.post("/admin/social/meta/disconnect");
      toast.success("Meta disconnected");
      load();
    } catch (e) { toast.error(e.message); }
  };

  const disconnectTikTok = async () => {
    if (!confirm("Disconnect TikTok? This removes the stored access + refresh tokens.")) return;
    try {
      await api.post("/admin/social/tiktok/disconnect");
      toast.success("TikTok disconnected");
      load();
    } catch (e) { toast.error(e.message); }
  };

  const testX = async () => {
    setXTesting(true);
    try {
      const r = await api.get("/admin/social/x/status");
      if (r.ok) {
        toast.success(`Connected as @${r.screen_name} — credentials verified.`);
      } else {
        toast.error(r.error || "X credentials invalid.");
      }
      load();
    } catch (e) {
      toast.error(e.message || "Test failed");
    } finally {
      setXTesting(false);
    }
  };

  const testXDryPost = async () => {
    setXTesting(true);
    try {
      const r = await api.post("/admin/social/x/test-post", {
        text: "Ascendra Academy connectivity test — dry run.",
        dry_run: true,
      });
      if (r.ok) {
        toast.success(`Dry-run passed. Would post as @${r.as}.`);
      }
    } catch (e) {
      toast.error(e.message || "Dry-run failed");
    } finally {
      setXTesting(false);
    }
  };

  const copy = (t) => { navigator.clipboard?.writeText(t); toast.success("Copied"); };

  const backendUrl = process.env.REACT_APP_BACKEND_URL || "";
  const domain = backendUrl.replace(/^https?:\/\//, "").replace(/\/$/, "") || "ascendraacademy.com";
  const oauthMeta = `https://${domain}/api/social/meta/callback`;
  const oauthTiktok = `https://${domain}/api/social/tiktok/callback`;

  if (loading) return <div className="max-w-5xl mx-auto px-5 sm:px-8 py-10"><Loader /></div>;

  return (
    <div className="max-w-5xl mx-auto px-5 sm:px-8 py-10" data-testid="admin-social-settings-page">
      <button onClick={() => nav("/admin/social")} className="flex items-center gap-1 text-sm text-[var(--asc-text-dim)] hover:text-white mb-3"><ArrowLeft size={14} /> Social Studio</button>
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="asc-kicker">Configuration</div>
          <h1 className="asc-h2 text-4xl mt-1 flex items-center gap-3"><Settings size={28} className="text-[var(--asc-brand)]" /> Platform Settings</h1>
          <p className="text-[var(--asc-text-dim)] text-sm mt-2 max-w-2xl">Configure API credentials for each social platform. All secrets live in <code className="asc-mono text-[var(--asc-brand)]">/app/backend/.env</code> — never exposed to the browser.</p>
        </div>
        <button onClick={load} className="asc-btn-secondary text-sm" data-testid="settings-refresh"><RefreshCcw size={13} /> Refresh</button>
      </div>

      {/* Security note */}
      <div className="asc-card p-4 mt-6 flex items-start gap-3" style={{ background: "rgba(255,176,0,0.06)", borderColor: "rgba(255,176,0,0.30)" }}>
        <Shield size={16} className="text-[var(--asc-brand)] mt-0.5 shrink-0" />
        <div className="text-sm text-[var(--asc-text-dim)]">
          <strong className="text-white">Never paste secrets into browser storage.</strong> After following each platform’s walkthrough, paste tokens into <code className="asc-mono text-[var(--asc-brand)]">/app/backend/.env</code> and restart the backend. Then hit Refresh above.
        </div>
      </div>

      <div className="space-y-4 mt-6">
        {/* X */}
        <PlatformSection
          testId="settings-x"
          icon={Twitter}
          iconColor="#7CD1FF"
          accent="rgba(29,161,242,0.14)"
          label="X (Twitter)"
          badge="Auto-post supported"
          cfg={settings?.x}
          docsUrl="https://developer.x.com/en/portal/dashboard"
          steps={[
            <>Sign in at <a className="underline text-[var(--asc-brand)]" href="https://developer.x.com/en/portal/dashboard" target="_blank" rel="noreferrer">developer.x.com/en/portal/dashboard</a> with your <strong>@AscendraAcademy</strong> handle.</>,
            <>Create a new Project + App. Under <em>User authentication settings</em>, set <strong>App permissions = Read and write</strong> and <strong>Type of App = Web App</strong>.</>,
            <>Under <em>Keys and tokens</em>, generate <strong>API Key + Secret</strong>, then <strong>Access Token + Secret</strong>. Copy all four.</>,
            <>Paste into <code className="asc-mono text-[var(--asc-brand)]">/app/backend/.env</code> as <code className="asc-mono">X_API_KEY</code>, <code className="asc-mono">X_API_SECRET</code>, <code className="asc-mono">X_ACCESS_TOKEN</code>, <code className="asc-mono">X_ACCESS_TOKEN_SECRET</code>, and set <code className="asc-mono">X_HANDLE=AscendraAcademy</code>.</>,
            <>Restart backend: <code className="asc-mono text-[var(--asc-brand)]">supervisorctl restart backend</code>. Then click <strong>Test connection</strong> below.</>,
          ]}
          extra={
            <div className="mt-3 space-y-3">
              <div className="flex flex-wrap gap-2">
                <button onClick={testX} disabled={xTesting || !settings?.x?.configured} className="asc-btn-secondary text-xs" data-testid="settings-x-test"><RefreshCcw size={12} /> {xTesting ? "Testing…" : "Test connection"}</button>
                <button onClick={testXDryPost} disabled={xTesting || !settings?.x?.configured} className="asc-btn-secondary text-xs" data-testid="settings-x-dryrun">Dry-run test post</button>
                {settings?.x?.screen_name && (
                  <a href={`https://x.com/${settings.x.screen_name}`} target="_blank" rel="noreferrer" className="asc-btn-secondary text-xs">
                    <ExternalLink size={12} /> @{settings.x.screen_name}
                  </a>
                )}
              </div>
              {xBudget && <XBudgetBar budget={xBudget} />}
            </div>
          }
        />

        {/* Facebook + Instagram (Meta) integrations disabled per user request 2026-07-12.
            Backend code (meta_publisher.py, /api/admin/social/meta/*, /api/social/meta/callback)
            remains intact for future reactivation. Uncomment these <PlatformSection> blocks +
            uncomment META_* env vars to re-enable. */}

        {/* TikTok */}
        <PlatformSection
          testId="settings-tiktok"
          icon={Music2}
          iconColor="#FFFFFF"
          accent="rgba(255,255,255,0.10)"
          label="TikTok"
          badge={tiktokStatus?.connected ? "Connected" : "Phase B — Content Posting API"}
          badgeTone={tiktokStatus?.connected ? "ok" : "warn"}
          cfg={{ ...(settings?.tiktok || {}), auto_post: !!tiktokStatus?.connected, configured: !!tiktokStatus?.connected || !!settings?.tiktok?.configured }}
          docsUrl="https://developers.tiktok.com/"
          steps={[
            <>Sign in at <a className="underline text-[var(--asc-brand)]" href="https://developers.tiktok.com/" target="_blank" rel="noreferrer">developers.tiktok.com</a>. Domain verification file already deployed ✅.</>,
            <>Create an app. Add products: <strong>Login Kit</strong> + <strong>Content Posting API</strong>.</>,
            <>Set the OAuth redirect URI to: <CopyRow value={oauthTiktok} onCopy={copy} testId="settings-tt-callback" /></>,
            <>Request scopes: <code className="asc-mono">user.info.basic</code>, <code className="asc-mono">video.upload</code>, <code className="asc-mono">video.publish</code>.</>,
            <>Save <code className="asc-mono">TIKTOK_CLIENT_KEY</code>, <code className="asc-mono">TIKTOK_CLIENT_SECRET</code>, and <code className="asc-mono">TIKTOK_REDIRECT_URI={oauthTiktok}</code> into the backend .env. Restart backend.</>,
            <>Click <strong>Connect TikTok</strong> below. Uses OAuth 2.0 + PKCE. Tokens auto-refresh every 24h.</>,
            <><strong>App Audit required</strong> before you can post publicly. Sandbox allows up to <strong>5 test accounts</strong> immediately. Posts default to <code className="asc-mono">SELF_ONLY</code> until audit passes.</>,
          ]}
          extra={
            <div className="mt-3 space-y-2">
              <div className="flex flex-wrap gap-2">
                {tiktokStatus?.connected ? (
                  <>
                    <span className="asc-btn-secondary text-xs cursor-default" data-testid="settings-tt-connected">
                      <CheckCircle2 size={12} className="text-[#4ADE80]" /> {tiktokStatus.verify?.username ? `@${tiktokStatus.verify.username}` : (tiktokStatus.open_id?.slice(0, 10) + "…")}
                    </span>
                    <button onClick={connectTikTok} disabled={connecting === "tiktok"} className="asc-btn-secondary text-xs" data-testid="settings-tt-reconnect"><RefreshCcw size={12} /> Reconnect</button>
                    <button onClick={disconnectTikTok} className="asc-btn-secondary text-xs" data-testid="settings-tt-disconnect">Disconnect</button>
                  </>
                ) : (
                  <button onClick={connectTikTok} disabled={connecting === "tiktok"} className="asc-btn-primary text-xs" data-testid="settings-tt-connect">
                    <LinkIcon size={12} /> {connecting === "tiktok" ? "Redirecting…" : "Connect TikTok"}
                  </button>
                )}
              </div>
              {tiktokStatus?.verify?.privacy_level_options && (
                <div className="text-[10px] text-[var(--asc-text-muted)]" data-testid="settings-tt-privacy-options">
                  Allowed privacy levels: <code className="asc-mono text-[var(--asc-brand)]">{tiktokStatus.verify.privacy_level_options.join(", ")}</code>
                </div>
              )}
              {tiktokStatus?.verify?.error && (
                <div className="text-[10px] text-[#FB7185] flex items-start gap-1"><AlertTriangle size={10} className="mt-0.5" /> {tiktokStatus.verify.error}</div>
              )}
            </div>
          }
        />
      </div>

      <div className="asc-card p-4 mt-6 flex items-start gap-3" style={{ background: "rgba(124,58,237,0.06)", borderColor: "rgba(124,58,237,0.30)" }}>
        <AlertTriangle size={16} className="text-[#BFB4FF] mt-0.5 shrink-0" />
        <div className="text-sm text-[var(--asc-text-dim)]">
          <strong className="text-white">Phase B is live!</strong> Meta and TikTok auto-posting is wired. Add the API credentials to <code className="asc-mono text-[var(--asc-brand)]">/app/backend/.env</code>, restart the backend, then click the <strong>Connect</strong> buttons above. Once connected, the platform&apos;s Post buttons unlock inside <Link className="underline text-[var(--asc-brand)]" to="/admin/social">Social Studio</Link>.
        </div>
      </div>
    </div>
  );
}

function PlatformSection({ testId, icon: Icon, iconColor, accent, label, badge, badgeTone = "ok", cfg, docsUrl, steps, extra }) {
  const ready = !!cfg?.auto_post;
  const configured = !!cfg?.configured;
  const badgeColor = badgeTone === "warn" ? "#BFB4FF" : (ready ? "#4ADE80" : "#8A83B8");
  const badgeBg = badgeTone === "warn" ? "rgba(124,58,237,0.18)" : (ready ? "rgba(74,222,128,0.15)" : "rgba(138,131,184,0.15)");
  return (
    <div className="asc-card p-5" data-testid={testId}>
      <div className="flex items-start gap-3">
        <div className="w-10 h-10 rounded-xl grid place-items-center shrink-0" style={{ background: accent }}>
          <Icon size={18} style={{ color: iconColor }} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="asc-h2 text-lg">{label}</h2>
            <span className="text-[10px] font-bold px-2 py-0.5 rounded-full" style={{ background: badgeBg, color: badgeColor }}>{badge}</span>
            {ready ? (
              <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full" style={{ background: "rgba(74,222,128,0.15)", color: "#4ADE80" }} data-testid={`${testId}-status-ready`}><CheckCircle2 size={10} /> Connected</span>
            ) : configured ? (
              <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full" style={{ background: "rgba(255,176,0,0.15)", color: "#FFB000" }} data-testid={`${testId}-status-partial`}><AlertTriangle size={10} /> Partial</span>
            ) : (
              <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full" style={{ background: "rgba(255,255,255,0.06)", color: "#8A83B8" }} data-testid={`${testId}-status-off`}><XCircle size={10} /> Not configured</span>
            )}
          </div>
          <div className="text-xs text-[var(--asc-text-muted)] mt-1">
            Env keys: {cfg?.env_keys?.map((k) => <code key={k} className="asc-mono mr-1">{k}</code>)}
          </div>
        </div>
        {docsUrl && (
          <a href={docsUrl} target="_blank" rel="noopener noreferrer" className="asc-btn-secondary text-xs shrink-0" data-testid={`${testId}-docs`}>
            <ExternalLink size={12} /> Docs
          </a>
        )}
      </div>

      <ol className="list-decimal ml-5 mt-4 space-y-2 text-sm text-[var(--asc-text-dim)]">
        {steps.map((s, i) => <li key={i} className="leading-relaxed">{s}</li>)}
      </ol>

      {extra}
    </div>
  );
}

function CopyRow({ value, onCopy, testId }) {
  return (
    <span className="inline-flex items-center gap-1.5 asc-mono text-xs px-2 py-1 rounded-md ml-1" style={{ background: "rgba(255,176,0,0.08)", border: "1px solid rgba(255,176,0,0.25)" }}>
      <span className="text-[var(--asc-brand)]">{value}</span>
      <button onClick={() => onCopy(value)} className="text-[var(--asc-text-muted)] hover:text-white" data-testid={testId}><Copy size={11} /></button>
    </span>
  );
}

function XBudgetBar({ budget }) {
  const m = budget?.month || {};
  const d = budget?.day || {};
  const monthColor = m.blocked ? "#FB7185" : m.warn ? "#FFB000" : "#4ADE80";
  const dayColor = d.blocked ? "#FB7185" : d.warn ? "#FFB000" : "#4ADE80";
  const monthPct = Math.min(100, m.percent || 0);
  const dayPct = Math.min(100, d.percent || 0);
  return (
    <div className="rounded-xl p-3 space-y-3" style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)" }} data-testid="x-budget-bar">
      <div className="flex items-center gap-2">
        <span className="text-[10px] font-bold uppercase tracking-wider text-[var(--asc-text-muted)]">X Free-Tier Budget</span>
        {m.blocked || d.blocked ? (
          <span className="text-[9px] px-1.5 py-0.5 rounded font-bold" style={{ background: "rgba(251,113,133,0.2)", color: "#FB7185" }}>BLOCKED</span>
        ) : (m.warn || d.warn) ? (
          <span className="text-[9px] px-1.5 py-0.5 rounded font-bold" style={{ background: "rgba(255,176,0,0.2)", color: "#FFB000" }}>NEAR LIMIT</span>
        ) : (
          <span className="text-[9px] px-1.5 py-0.5 rounded font-bold" style={{ background: "rgba(74,222,128,0.15)", color: "#4ADE80" }}>HEALTHY</span>
        )}
      </div>
      <div>
        <div className="flex justify-between text-[10px] mb-1">
          <span className="text-[var(--asc-text-dim)]">This month</span>
          <span className="asc-mono" style={{ color: monthColor }}>{m.used}/{m.limit} tweets ({m.remaining} left)</span>
        </div>
        <div className="h-1.5 rounded-full overflow-hidden" style={{ background: "rgba(255,255,255,0.08)" }}>
          <div className="h-full transition-all" style={{ width: `${monthPct}%`, background: monthColor }} />
        </div>
      </div>
      <div>
        <div className="flex justify-between text-[10px] mb-1">
          <span className="text-[var(--asc-text-dim)]">Today</span>
          <span className="asc-mono" style={{ color: dayColor }}>{d.used}/{d.limit} tweets ({d.remaining} left)</span>
        </div>
        <div className="h-1.5 rounded-full overflow-hidden" style={{ background: "rgba(255,255,255,0.08)" }}>
          <div className="h-full transition-all" style={{ width: `${dayPct}%`, background: dayColor }} />
        </div>
      </div>
      <div className="text-[10px] text-[var(--asc-text-muted)] leading-relaxed">
        Ascendra will refuse to post to X once either budget hits zero, so you never accidentally get charged. Adjust with <code className="asc-mono">X_MONTHLY_POST_LIMIT</code> in <code className="asc-mono">.env</code> if X changes their tiers.
      </div>
    </div>
  );
}
