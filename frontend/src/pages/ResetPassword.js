import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { api } from "@/lib/api";
import { AuthShell } from "./Login";
import { toast } from "sonner";

export default function ResetPassword() {
  const [params] = useSearchParams();
  const token = params.get("token") || "";
  const [pw, setPw] = useState("");
  const [pw2, setPw2] = useState("");
  const [busy, setBusy] = useState(false);
  const nav = useNavigate();

  const submit = async (e) => {
    e.preventDefault();
    if (pw !== pw2) { toast.error("Passwords don't match"); return; }
    if (pw.length < 6) { toast.error("Password must be 6+ chars"); return; }
    setBusy(true);
    try {
      await api.post("/auth/reset-password", { token, new_password: pw });
      toast.success("Password updated. Please sign in.");
      nav("/login");
    } catch (err) {
      toast.error(err.message || "Reset failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthShell title="Set a new password" subtitle="Choose a strong password (6+ characters).">
      {!token ? (
        <div className="asc-card p-5 text-sm text-[var(--asc-text-dim)]">
          Missing reset token. <Link to="/forgot-password" className="text-[var(--asc-brand)] hover:underline">Request a new link</Link>.
        </div>
      ) : (
        <form onSubmit={submit} className="space-y-4" data-testid="reset-form">
          <input className="asc-input" type="password" placeholder="New password" required value={pw} onChange={(e) => setPw(e.target.value)} data-testid="reset-pw-input" />
          <input className="asc-input" type="password" placeholder="Confirm new password" required value={pw2} onChange={(e) => setPw2(e.target.value)} data-testid="reset-pw2-input" />
          <button type="submit" disabled={busy} className="asc-btn-primary w-full justify-center" data-testid="reset-submit-btn">
            {busy ? "Updating…" : "Set new password"}
          </button>
        </form>
      )}
    </AuthShell>
  );
}
