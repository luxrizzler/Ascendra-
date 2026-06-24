import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "@/lib/api";
import { AuthShell } from "./Login";
import { toast } from "sonner";

export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [devLink, setDevLink] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const r = await api.post("/auth/forgot-password", { email: email.trim().toLowerCase() });
      setSent(true);
      if (r.dev_reset_token) {
        const link = `${window.location.origin}/reset-password?token=${r.dev_reset_token}`;
        setDevLink(link);
      }
      toast.success("If that email exists, a reset link is on its way.");
    } catch (err) {
      toast.error(err.message || "Could not send reset link");
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthShell title="Reset password" subtitle="Enter your email and we'll send a magic link.">
      {!sent ? (
        <form onSubmit={submit} className="space-y-4" data-testid="forgot-form">
          <input className="asc-input" type="email" placeholder="Email" required value={email} onChange={(e) => setEmail(e.target.value)} data-testid="forgot-email-input" />
          <button type="submit" disabled={busy} className="asc-btn-primary w-full justify-center" data-testid="forgot-submit-btn">
            {busy ? "Sending…" : "Send reset link"}
          </button>
        </form>
      ) : (
        <div className="asc-card p-5" data-testid="forgot-success">
          <p className="text-sm text-[var(--asc-text-dim)]">If an account with that email exists, you'll receive a reset link shortly.</p>
          {devLink && (
            <div className="mt-4 p-3 rounded-lg text-xs" style={{ background: "#1F183A", border: "1px dashed #FFB000" }}>
              <div className="text-[var(--asc-brand)] font-bold mb-1">DEV MODE — Reset link</div>
              <a className="text-[var(--asc-lavender)] break-all underline" href={devLink}>{devLink}</a>
            </div>
          )}
        </div>
      )}
      <div className="mt-5 text-sm text-center">
        <Link to="/login" className="text-[var(--asc-text-dim)] hover:text-white">← Back to sign in</Link>
      </div>
    </AuthShell>
  );
}
