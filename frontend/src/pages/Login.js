import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { Sparkles, ArrowRight } from "lucide-react";
import { toast } from "sonner";
import GoogleButton from "@/components/GoogleButton";
import SEO from "@/components/SEO";

export default function Login() {
  const { login } = useAuth();
  const nav = useNavigate();
  const [params] = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const u = await login(email.trim().toLowerCase(), password);
      if (u?.must_change_password) {
        nav("/profile?force_change=1");
      } else {
        nav(params.get("next") || "/dashboard");
      }
      toast.success("Welcome back");
    } catch (err) {
      toast.error(err.message || "Login failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthShell title="Welcome back" subtitle="Sign in to continue your ascent.">
      <SEO
        title="Sign in to Ascendra Academy"
        description="Sign in to your Ascendra Academy account to continue your AI learning path, track your streak, and access certificates."
        path="/login"
        noindex
      />
      <GoogleButton label="Continue with Google" />
      <Divider />
      <form onSubmit={submit} className="space-y-4" data-testid="login-form">
        <input className="asc-input" type="email" placeholder="Email" required value={email} onChange={(e) => setEmail(e.target.value)} data-testid="login-email-input" />
        <input className="asc-input" type="password" placeholder="Password" required value={password} onChange={(e) => setPassword(e.target.value)} data-testid="login-password-input" />
        <button type="submit" disabled={busy} className="asc-btn-primary w-full justify-center" data-testid="login-submit-btn">
          {busy ? "Signing in…" : "Sign in"} <ArrowRight size={16} />
        </button>
      </form>
      <div className="flex justify-between mt-5 text-sm">
        <Link to="/forgot-password" className="text-[var(--asc-text-dim)] hover:text-white">Forgot password?</Link>
        <Link to="/signup" className="text-[var(--asc-brand)] hover:underline">Create account →</Link>
      </div>
    </AuthShell>
  );
}

function Divider() {
  return (
    <div className="flex items-center gap-3 my-4">
      <div className="flex-1 h-px" style={{ background: "rgba(191,180,255,0.18)" }} />
      <div className="text-[10px] uppercase tracking-[0.25em] text-[var(--asc-text-muted)]">Or with email</div>
      <div className="flex-1 h-px" style={{ background: "rgba(191,180,255,0.18)" }} />
    </div>
  );
}

export function AuthShell({ title, subtitle, children }) {
  return (
    <div className="min-h-[80vh] grid place-items-center px-5 py-10">
      <div className="w-full max-w-md">
        <div className="flex items-center gap-2 mb-8">
          <div className="w-8 h-8 rounded-lg grid place-items-center" style={{ background: "#FFB000" }}><Sparkles size={16} color="#000" /></div>
          <span className="font-black tracking-[0.32em] text-sm">ASCENDRA</span>
        </div>
        <div className="asc-kicker">Account</div>
        <h1 className="asc-h2 text-4xl mt-2">{title}</h1>
        <p className="text-[var(--asc-text-dim)] mt-2 text-sm">{subtitle}</p>
        <div className="mt-8">{children}</div>
      </div>
    </div>
  );
}
