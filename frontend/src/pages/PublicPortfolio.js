import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Trophy, Sparkles, CheckCircle2, ArrowRight, User } from "lucide-react";
import { api } from "@/lib/api";
import SEO from "@/components/SEO";
import Loader from "@/components/Loader";

export default function PublicPortfolio() {
  const { userSlug } = useParams();
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);
  const [err, setErr] = useState(null);

  useEffect(() => {
    setLoading(true);
    api.get(`/practice/portfolio/public/${encodeURIComponent(userSlug)}`)
      .then((r) => setData(r))
      .catch((e) => setErr(e.message || "Portfolio not found"))
      .finally(() => setLoading(false));
  }, [userSlug]);

  if (loading) return <div className="min-h-screen grid place-items-center"><Loader /></div>;
  if (err) return (
    <div className="min-h-screen grid place-items-center px-6" data-testid="public-portfolio-error">
      <div className="asc-card p-10 text-center max-w-md">
        <div className="w-14 h-14 rounded-full mx-auto grid place-items-center" style={{ background: "rgba(191,180,255,0.15)" }}>
          <User size={24} color="#BFB4FF" />
        </div>
        <h1 className="asc-h2 text-2xl mt-5">Portfolio not found</h1>
        <p className="text-[var(--asc-text-dim)] mt-3">This user hasn&apos;t shared any public work yet.</p>
        <Link to="/" className="asc-btn-primary mt-6 inline-flex">Return home</Link>
      </div>
    </div>
  );

  const { user, items } = data;
  const displayName = user.name || "Ascendra learner";
  return (
    <div className="min-h-screen" data-testid="public-portfolio-page">
      <SEO
        title={`${displayName}'s AI Practice Portfolio`}
        description={`${displayName} has mastered ${items.length} AI practice challenges on Ascendra Academy.`}
        path={`/portfolio/${userSlug}`}
      />

      {/* Hero */}
      <section className="px-6 pt-14 pb-10 border-b border-[var(--asc-border)]">
        <div className="max-w-5xl mx-auto">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-[var(--asc-border-strong)] mb-5" style={{ background: "rgba(255,176,0,0.08)" }}>
            <Trophy size={14} color="#FFB000" />
            <span className="asc-label">Public Portfolio</span>
          </div>
          <div className="flex items-center gap-4">
            {user.picture ? (
              <img src={user.picture} alt={displayName} className="w-16 h-16 rounded-full border-2 border-[var(--asc-brand)]" />
            ) : (
              <div className="w-16 h-16 rounded-full grid place-items-center border-2 border-[var(--asc-brand)]" style={{ background: "rgba(255,176,0,0.15)" }}>
                <span className="text-2xl font-black text-white">{displayName[0]?.toUpperCase()}</span>
              </div>
            )}
            <div>
              <h1 className="asc-h1 text-3xl sm:text-4xl" data-testid="public-portfolio-name">{displayName}</h1>
              <p className="text-[var(--asc-text-dim)] mt-1">{items.length} mastered practice{items.length === 1 ? "" : "s"} on Ascendra Academy</p>
            </div>
          </div>
        </div>
      </section>

      {/* Items */}
      <section className="px-6 py-10">
        <div className="max-w-5xl mx-auto">
          {items.length === 0 ? (
            <div className="asc-card p-10 text-center max-w-lg mx-auto">
              <h2 className="asc-h2 text-xl">Nothing shared yet</h2>
              <p className="text-[var(--asc-text-dim)] mt-2">{displayName} hasn&apos;t made any items public.</p>
            </div>
          ) : (
            <div className="grid gap-4">
              {items.map((it) => (
                <div key={it.attempt_id} className="asc-card p-6" data-testid={`public-item-${it.attempt_id}`}>
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="flex-1 min-w-0">
                      <div className="text-xs text-[var(--asc-text-muted)] tracking-wider">
                        {it.created_at ? new Date(it.created_at).toLocaleDateString(undefined, { month: "long", day: "numeric", year: "numeric" }) : ""}
                      </div>
                      <h3 className="asc-h2 text-xl sm:text-2xl mt-1">{it.challenge_title}</h3>
                    </div>
                    <div className="flex items-center gap-2 px-3 py-1.5 rounded-full" style={{ background: "rgba(34,197,94,0.15)", border: "1px solid rgba(34,197,94,0.4)" }}>
                      <Trophy size={13} color="#22c55e" />
                      <span className="font-black text-lg" style={{ color: "#22c55e" }}>{it.score}</span>
                    </div>
                  </div>

                  <div className="mt-4 p-4 rounded-xl text-sm text-[var(--asc-text-dim)] whitespace-pre-wrap leading-relaxed" style={{ background: "rgba(191,180,255,0.04)", border: "1px solid rgba(191,180,255,0.12)" }}>
                    {it.attempt_text}
                  </div>

                  {it.strengths?.length > 0 && (
                    <div className="mt-3 p-3 rounded-lg text-xs" style={{ background: "rgba(34,197,94,0.05)" }}>
                      <div className="flex flex-wrap gap-2">
                        {it.strengths.slice(0, 2).map((s, i) => (
                          <span key={i} className="inline-flex items-center gap-1 px-2 py-1 rounded-full" style={{ background: "rgba(34,197,94,0.12)", color: "#22c55e" }}>
                            <CheckCircle2 size={10} /> {s.length > 60 ? s.slice(0, 60) + "…" : s}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Footer CTA */}
          <div className="mt-12 p-6 rounded-2xl text-center" style={{ background: "linear-gradient(135deg, rgba(255,176,0,0.06), rgba(191,180,255,0.06))", border: "1px solid var(--asc-border)" }}>
            <Sparkles size={20} color="#FFB000" className="mx-auto" />
            <h3 className="asc-h2 text-xl mt-3">Build your own portfolio</h3>
            <p className="text-[var(--asc-text-dim)] mt-2 text-sm">Master AI through hands-on practice challenges graded by AI, then showcase your best work.</p>
            <Link to="/signup" className="asc-btn-primary mt-4 inline-flex" data-testid="public-portfolio-cta">
              Start free on Ascendra <ArrowRight size={14} />
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
