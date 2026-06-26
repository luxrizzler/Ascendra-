import { useState } from "react";
import { api } from "@/lib/api";
import { Sparkles, X, CheckCircle2, Mail } from "lucide-react";
import { toast } from "sonner";

export default function LeadCaptureModal({ open, onClose, source = "landing" }) {
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);

  if (!open) return null;

  const submit = async (e) => {
    e?.preventDefault?.();
    if (!email.trim() || !email.includes("@")) {
      toast.error("Please enter a valid email");
      return;
    }
    setBusy(true);
    try {
      await api.post("/leads", { email: email.trim().toLowerCase(), name: name.trim() || undefined, source });
      setDone(true);
    } catch (err) {
      toast.error(err.message || "Could not subscribe");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 grid place-items-center p-4" style={{ background: "rgba(0,0,0,0.78)", backdropFilter: "blur(8px)" }} onClick={onClose} data-testid="lead-capture-modal">
      <div className="asc-card w-full max-w-md p-7 relative" onClick={(e) => e.stopPropagation()}>
        <button onClick={onClose} className="absolute top-4 right-4 text-[var(--asc-text-muted)] hover:text-white" data-testid="lead-modal-close-btn">
          <X size={18} />
        </button>

        {done ? (
          <div className="text-center py-4" data-testid="lead-modal-success">
            <div className="w-14 h-14 mx-auto rounded-2xl grid place-items-center mb-3" style={{ background: "rgba(52,211,153,0.18)", border: "1px solid rgba(52,211,153,0.4)" }}>
              <CheckCircle2 size={24} color="#34D399" />
            </div>
            <h2 className="asc-h2 text-2xl">Check your inbox</h2>
            <p className="text-[var(--asc-text-dim)] text-sm mt-2">Your free AI Roadmap is on its way to <strong>{email}</strong>. It should land in 30 seconds or less.</p>
            <button onClick={onClose} className="asc-btn-secondary text-sm mt-5">Close</button>
          </div>
        ) : (
          <>
            <div className="flex items-start gap-3">
              <div className="w-12 h-12 rounded-2xl grid place-items-center shrink-0" style={{ background: "rgba(255,176,0,0.18)", border: "1px solid rgba(255,176,0,0.4)" }}>
                <Sparkles size={22} color="#FFB000" />
              </div>
              <div>
                <h2 className="asc-h2 text-2xl leading-tight">Grab the AI Roadmap</h2>
                <p className="text-[var(--asc-text-dim)] text-sm mt-1">5 phases. 5 minutes to read. Free forever.</p>
              </div>
            </div>

            <form onSubmit={submit} className="mt-6 space-y-3">
              <div>
                <label className="asc-label">Your first name <span className="text-[var(--asc-text-muted)] font-normal">(optional)</span></label>
                <input
                  className="asc-input w-full mt-1"
                  placeholder="Alex"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  data-testid="lead-modal-name"
                  disabled={busy}
                />
              </div>
              <div>
                <label className="asc-label">Email</label>
                <input
                  type="email"
                  required
                  className="asc-input w-full mt-1"
                  placeholder="you@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  data-testid="lead-modal-email"
                  disabled={busy}
                  autoFocus
                />
              </div>
              <button type="submit" disabled={busy} className="asc-btn-primary w-full text-sm" data-testid="lead-modal-submit">
                {busy ? "Sending…" : (<><Mail size={14} /> Send me the roadmap</>)}
              </button>
              <p className="text-[10px] text-[var(--asc-text-muted)] text-center">We'll occasionally share value-packed lessons. Unsubscribe anytime.</p>
            </form>
          </>
        )}
      </div>
    </div>
  );
}
