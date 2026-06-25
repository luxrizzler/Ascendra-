import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import Loader from "@/components/Loader";
import { ArrowLeft, Mail, Send, KeyRound, CreditCard, UserPlus, RefreshCw } from "lucide-react";
import { toast } from "sonner";

const TEMPLATES = [
  { id: "password_reset", title: "Password Reset", icon: KeyRound, body: "Sent when a user requests to reset their password." },
  { id: "checkout_success", title: "Checkout Success", icon: CreditCard, body: "Sent automatically when a Stripe payment is confirmed." },
  { id: "invite", title: "Invite (Temp Password)", icon: UserPlus, body: "Sent when an admin creates an account with a temporary password." },
];

export default function AdminEmail() {
  const nav = useNavigate();
  const { user } = useAuth();
  const [active, setActive] = useState("password_reset");
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [customTo, setCustomTo] = useState("");

  const load = async (id) => {
    setLoading(true);
    try {
      const r = await api.get(`/admin/email/preview/${id}`);
      setPreview(r);
    } catch (e) {
      toast.error(e.message || "Could not load preview");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(active); }, [active]);

  const sendTest = async () => {
    setSending(true);
    try {
      const body = { template: active };
      if (customTo.trim()) body.to = customTo.trim().toLowerCase();
      const r = await api.post("/admin/email/test-send", body);
      toast.success(
        r.dry_run
          ? `Dry-run logged (no RESEND_API_KEY) → ${r.to}`
          : `Sent to ${r.to} (id: ${r.id?.slice(0, 8)}…)`
      );
    } catch (e) {
      toast.error(e.message || "Send failed");
    } finally {
      setSending(false);
    }
  };

  const cur = TEMPLATES.find((t) => t.id === active);
  const Icon = cur?.icon || Mail;

  return (
    <div className="max-w-6xl mx-auto px-5 sm:px-8 py-10" data-testid="admin-email-page">
      <button onClick={() => nav("/admin")} className="flex items-center gap-1 text-sm text-[var(--asc-text-dim)] hover:text-white mb-3"><ArrowLeft size={14} /> Admin</button>
      <div className="asc-kicker">Email Templates</div>
      <h1 className="asc-h2 text-4xl mt-1 flex items-center gap-3"><Mail size={28} className="text-[var(--asc-brand)]" /> Preview & test</h1>
      <p className="text-[var(--asc-text-dim)] text-sm mt-2">Preview every transactional email before a user sees it. Send a test to yourself or any address.</p>

      <div className="grid lg:grid-cols-[280px_1fr] gap-6 mt-8">
        {/* Sidebar */}
        <aside className="space-y-2">
          {TEMPLATES.map((t) => {
            const TIcon = t.icon;
            const isActive = active === t.id;
            return (
              <button
                key={t.id}
                onClick={() => setActive(t.id)}
                data-testid={`email-template-${t.id}`}
                className="w-full text-left asc-card p-4 transition"
                style={isActive ? { borderColor: "#FFB000", background: "rgba(255,176,0,0.06)" } : {}}
              >
                <div className="flex items-center gap-2 mb-1">
                  <TIcon size={16} color={isActive ? "#FFB000" : "#BFB4FF"} />
                  <span className="font-bold text-sm">{t.title}</span>
                </div>
                <div className="text-xs text-[var(--asc-text-muted)] leading-relaxed">{t.body}</div>
              </button>
            );
          })}
        </aside>

        {/* Main */}
        <main>
          <div className="asc-card p-5">
            <div className="flex items-center justify-between gap-4 flex-wrap mb-4">
              <div className="flex items-center gap-3 min-w-0">
                <div className="w-10 h-10 rounded-xl grid place-items-center" style={{ background: "rgba(255,176,0,0.12)", border: "1px solid rgba(255,176,0,0.35)" }}>
                  <Icon size={18} color="#FFB000" />
                </div>
                <div className="min-w-0">
                  <div className="font-black text-base truncate">{cur?.title}</div>
                  <div className="text-xs text-[var(--asc-text-muted)] truncate">{preview?.subject || "—"}</div>
                </div>
              </div>
              <div className="flex items-center gap-2 flex-wrap">
                <input
                  className="asc-input text-sm"
                  placeholder={user?.email}
                  value={customTo}
                  onChange={(e) => setCustomTo(e.target.value)}
                  data-testid="email-test-to"
                  style={{ maxWidth: 240 }}
                />
                <button onClick={() => load(active)} className="asc-btn-secondary text-xs" data-testid="email-refresh-btn"><RefreshCw size={12} /> Refresh</button>
                <button onClick={sendTest} disabled={sending} className="asc-btn-primary text-xs" data-testid="email-send-test-btn">
                  <Send size={12} /> {sending ? "Sending…" : "Send test"}
                </button>
              </div>
            </div>

            {/* Iframe Preview */}
            {loading ? (
              <Loader label="Rendering preview…" />
            ) : preview ? (
              <iframe
                key={active}
                srcDoc={preview.html}
                title={`Preview: ${cur?.title}`}
                data-testid="email-preview-iframe"
                style={{ width: "100%", minHeight: 720, border: "1px solid rgba(191,180,255,0.18)", borderRadius: 14, background: "#0a0a0a" }}
                sandbox="allow-same-origin"
              />
            ) : null}
          </div>
        </main>
      </div>
    </div>
  );
}
