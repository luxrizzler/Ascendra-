import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { AuthShell } from "./Login";
import { ArrowRight } from "lucide-react";
import { toast } from "sonner";

export default function Signup() {
  const { signup } = useAuth();
  const nav = useNavigate();
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    if (password.length < 6) { toast.error("Password must be 6+ characters"); return; }
    setBusy(true);
    try {
      await signup(email.trim().toLowerCase(), password, name.trim() || undefined);
      toast.success("Account created — welcome to Ascendra!");
      nav("/onboarding");
    } catch (err) {
      toast.error(err.message || "Could not create account");
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthShell title="Begin your ascent" subtitle="Create a free account. No card required.">
      <form onSubmit={submit} className="space-y-4" data-testid="signup-form">
        <input className="asc-input" type="text" placeholder="Your name (optional)" value={name} onChange={(e) => setName(e.target.value)} data-testid="signup-name-input" />
        <input className="asc-input" type="email" placeholder="Email" required value={email} onChange={(e) => setEmail(e.target.value)} data-testid="signup-email-input" />
        <input className="asc-input" type="password" placeholder="Password (6+ chars)" required value={password} onChange={(e) => setPassword(e.target.value)} data-testid="signup-password-input" />
        <button type="submit" disabled={busy} className="asc-btn-primary w-full justify-center" data-testid="signup-submit-btn">
          {busy ? "Creating…" : "Create account"} <ArrowRight size={16} />
        </button>
      </form>
      <p className="text-xs text-[var(--asc-text-muted)] mt-4 text-center">
        By creating an account, you agree to our terms. By accessing this site, you accept that this is a demo.
      </p>
      <div className="mt-5 text-sm text-center text-[var(--asc-text-dim)]">
        Already have an account? <Link to="/login" className="text-[var(--asc-brand)] hover:underline">Sign in</Link>
      </div>
    </AuthShell>
  );
}
