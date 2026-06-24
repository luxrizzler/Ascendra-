import { useEffect, useState } from "react";
import { Link, useSearchParams, useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { CheckCircle2, Loader2, ArrowRight, Sparkles } from "lucide-react";

export default function CheckoutSuccess() {
  const [params] = useSearchParams();
  const { refresh } = useAuth();
  const sid = params.get("session_id");
  const [status, setStatus] = useState("polling");
  const [tier, setTier] = useState(null);
  const [tries, setTries] = useState(0);
  const nav = useNavigate();

  useEffect(() => {
    if (!sid) { setStatus("error"); return; }
    let cancelled = false;
    const poll = async () => {
      try {
        const r = await api.get(`/billing/status/${sid}`);
        if (cancelled) return;
        if (r.status === "paid") {
          setStatus("paid");
          setTier(r.tier);
          await refresh();
          return;
        }
      } catch {}
      if (tries < 30 && !cancelled) {
        setTimeout(() => setTries((t) => t + 1), 2000);
      } else if (!cancelled) {
        setStatus("timeout");
      }
    };
    poll();
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sid, tries]);

  return (
    <div className="min-h-[70vh] grid place-items-center px-5 py-10" data-testid="checkout-success-page">
      <div className="asc-card p-8 max-w-md w-full text-center">
        {status === "polling" && (
          <>
            <div className="w-16 h-16 rounded-full grid place-items-center mx-auto" style={{ background: "rgba(255,176,0,0.15)" }}>
              <Loader2 size={28} className="animate-spin text-[var(--asc-brand)]" />
            </div>
            <h1 className="asc-h2 text-2xl mt-4">Confirming your purchase…</h1>
            <p className="text-[var(--asc-text-dim)] mt-2 text-sm">This usually takes a few seconds.</p>
          </>
        )}
        {status === "paid" && (
          <>
            <div className="w-16 h-16 rounded-full grid place-items-center mx-auto" style={{ background: "rgba(52,211,153,0.18)" }}>
              <CheckCircle2 size={32} className="text-[var(--asc-success)]" />
            </div>
            <div className="asc-kicker mt-4">Welcome to {tier?.toUpperCase()}</div>
            <h1 className="asc-h2 text-3xl mt-2 flex items-center justify-center gap-2"><Sparkles size={22} className="text-[var(--asc-brand)]" /> You're in.</h1>
            <p className="text-[var(--asc-text-dim)] mt-2">Your tier is now active. Time to learn.</p>
            <div className="flex gap-3 mt-6 justify-center">
              <Link to="/dashboard" className="asc-btn-primary">Go to dashboard <ArrowRight size={14} /></Link>
              <Link to="/paths" className="asc-btn-secondary">Browse paths</Link>
            </div>
          </>
        )}
        {status === "timeout" && (
          <>
            <h1 className="asc-h2 text-2xl">Still processing…</h1>
            <p className="text-[var(--asc-text-dim)] mt-2 text-sm">Your payment may still come through. Check your profile in a moment.</p>
            <Link to="/profile" className="asc-btn-primary mt-5 inline-flex">Go to profile</Link>
          </>
        )}
        {status === "error" && (
          <>
            <h1 className="asc-h2 text-2xl">Missing session</h1>
            <Link to="/pricing" className="asc-btn-primary mt-5 inline-flex">Back to pricing</Link>
          </>
        )}
      </div>
    </div>
  );
}
