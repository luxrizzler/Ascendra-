import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import Loader from "@/components/Loader";
import TierBadge from "@/components/TierBadge";
import { formatDate } from "@/lib/utils";
import { Trophy, KeyRound, Shield, Mail, ArrowRight, LogOut } from "lucide-react";
import { toast } from "sonner";

export default function Profile() {
  const { user, logout, refresh } = useAuth();
  const [certs, setCerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [params] = useSearchParams();
  const forceChange = params.get("force_change") === "1" || user?.must_change_password;

  // change password form
  const [cur, setCur] = useState("");
  const [pw, setPw] = useState("");
  const [pw2, setPw2] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.get("/certificates").then((r) => setCerts(r.certificates)).finally(() => setLoading(false));
  }, []);

  const changePassword = async (e) => {
    e.preventDefault();
    if (pw !== pw2) { toast.error("Passwords don't match"); return; }
    if (pw.length < 6) { toast.error("Password must be 6+ chars"); return; }
    setBusy(true);
    try {
      const body = { new_password: pw };
      if (!forceChange) body.current_password = cur;
      await api.post("/auth/change-password", body);
      setCur(""); setPw(""); setPw2("");
      await refresh();
      toast.success("Password updated");
    } catch (err) {
      toast.error(err.message || "Could not update password");
    } finally {
      setBusy(false);
    }
  };

  if (loading || !user) return <Loader />;

  return (
    <div className="max-w-5xl mx-auto px-5 sm:px-8 py-10" data-testid="profile-page">
      <div className="asc-kicker">Your account</div>
      <h1 className="asc-h2 text-4xl mt-2">Profile</h1>

      <div className="asc-card p-6 mt-6">
        <div className="flex items-center gap-4">
          {user.picture ? (
            <img src={user.picture} alt="" className="w-16 h-16 rounded-full" />
          ) : (
            <div className="w-16 h-16 rounded-full grid place-items-center text-2xl font-black" style={{ background: "#7C3AED" }}>
              {(user.name || user.email)[0].toUpperCase()}
            </div>
          )}
          <div className="flex-1">
            <div className="font-bold text-lg">{user.name || "Ascendra Learner"}</div>
            <div className="text-sm text-[var(--asc-text-dim)] flex items-center gap-1.5"><Mail size={13} /> {user.email}</div>
            <div className="mt-2 flex items-center gap-2">
              <TierBadge tier={user.tier} />
              {user.is_admin && <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full font-black" style={{ background: "#FF6B35", color: "#fff" }}><Shield size={10} className="inline mr-1" />Admin</span>}
              <span className="text-xs text-[var(--asc-text-muted)]">Joined {formatDate(user.created_at)}</span>
            </div>
          </div>
          <button onClick={logout} className="asc-btn-secondary text-sm" data-testid="profile-logout-btn"><LogOut size={14} /> Sign out</button>
        </div>
      </div>

      {forceChange && (
        <div className="asc-card p-5 mt-5 border-[var(--asc-brand)]" style={{ borderColor: "#FFB000", background: "rgba(255,176,0,0.06)" }}>
          <div className="font-bold text-[var(--asc-brand)]">Please set a new password</div>
          <div className="text-sm text-[var(--asc-text-dim)] mt-1">For security, you must change your temporary password before continuing.</div>
        </div>
      )}

      <section className="grid md:grid-cols-2 gap-5 mt-6">
        <div className="asc-card p-6">
          <div className="flex items-center gap-2 mb-4"><KeyRound size={16} /> <h2 className="font-bold">Change password</h2></div>
          <form onSubmit={changePassword} className="space-y-3" data-testid="change-password-form">
            {!forceChange && (
              <input className="asc-input" type="password" placeholder="Current password" value={cur} onChange={(e) => setCur(e.target.value)} data-testid="profile-current-pw" />
            )}
            <input className="asc-input" type="password" placeholder="New password (6+ chars)" value={pw} onChange={(e) => setPw(e.target.value)} data-testid="profile-new-pw" />
            <input className="asc-input" type="password" placeholder="Confirm new password" value={pw2} onChange={(e) => setPw2(e.target.value)} data-testid="profile-new-pw2" />
            <button type="submit" disabled={busy} className="asc-btn-primary w-full justify-center" data-testid="profile-change-submit">{busy ? "Updating…" : "Update password"}</button>
          </form>
        </div>

        <div className="asc-card p-6">
          <div className="flex items-center gap-2 mb-4"><Trophy size={16} className="text-[var(--asc-brand)]" /> <h2 className="font-bold">Certificates ({certs.length})</h2></div>
          {certs.length === 0 ? (
            <div className="text-sm text-[var(--asc-text-dim)]">Complete a learning path to earn your first certificate.</div>
          ) : (
            <div className="space-y-2">
              {certs.map((c) => (
                <Link key={c.id} to={`/certificate/${c.id}`} className="flex items-center gap-3 p-3 rounded-xl" style={{ background: "#1F183A", border: "1px solid rgba(191,180,255,0.1)" }} data-testid={`profile-cert-${c.id}`}>
                  <div className="w-10 h-10 rounded-lg grid place-items-center" style={{ background: `${c.path_color}28` }}><Trophy size={18} color={c.path_color} /></div>
                  <div className="flex-1 min-w-0">
                    <div className="font-bold truncate">{c.path_title}</div>
                    <div className="text-xs text-[var(--asc-text-muted)]">Serial {c.serial} · {formatDate(c.issued_at)}</div>
                  </div>
                  <ArrowRight size={16} />
                </Link>
              ))}
            </div>
          )}
        </div>
      </section>

      {user.tier !== "free" && (
        <div className="asc-card p-6 mt-5">
          <div className="flex items-center justify-between gap-4 flex-wrap">
            <div>
              <h2 className="font-bold">Subscription</h2>
              <div className="text-sm text-[var(--asc-text-dim)] mt-1">
                You're on <span className="font-black uppercase" style={{ color: "#FFB000" }}>{user.tier}</span> ({user.subscription_interval || "monthly"})
                {user.tier_expires_at && <> · renews {formatDate(user.tier_expires_at)}</>}
              </div>
            </div>
            <Link to="/pricing" className="asc-btn-secondary text-sm">Manage plan</Link>
          </div>
        </div>
      )}
    </div>
  );
}
