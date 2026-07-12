import { useEffect, useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import Loader from "@/components/Loader";
import TierBadge from "@/components/TierBadge";
import { CheckCircle2, ArrowRight, Zap, Sparkles } from "lucide-react";
import { toast } from "sonner";
import SEO from "@/components/SEO";

export default function Pricing() {
  const { user, refresh } = useAuth();
  const nav = useNavigate();
  const [tiers, setTiers] = useState([]);
  const [interval, setIntervalKind] = useState("annual");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(null);

  useEffect(() => {
    api.get("/pricing").then((r) => setTiers(r.tiers)).finally(() => setLoading(false));
  }, []);

  const startCheckout = async (tier, intv = interval) => {
    if (!user) { nav("/login?next=/pricing"); return; }
    setBusy(`${tier}-${intv}`);
    try {
      const origin = window.location.origin;
      const { url } = await api.post("/billing/checkout", { tier, interval: intv, origin_url: origin });
      window.location.href = url;
    } catch (err) {
      toast.error(err.message || "Could not start checkout");
      setBusy(null);
      setTimeout(refresh, 600);
    }
  };

  if (loading) return <Loader />;

  return (
    <div className="max-w-7xl mx-auto px-5 sm:px-8 py-10" data-testid="pricing-page">
      <SEO
        title="Pricing — AI learning plans starting at $9.99/mo"
        description="Ascender ($9.99/mo), Pathfinder ($19.99/mo), Sage ($29.99/mo), or Business ($149/mo — founding rate $99/mo for the first 25 businesses). Cancel anytime. 7-day money-back guarantee."
        path="/pricing"
      />
      <div className="asc-kicker">Plans</div>
      <h1 className="asc-h2 text-4xl sm:text-5xl mt-2">Learn AI like the top 1%.</h1>
      <p className="text-[var(--asc-text-dim)] mt-2 max-w-2xl">Cancel anytime in one click from your profile. 7-day money-back guarantee.</p>

      <div className="text-xs text-[var(--asc-text-muted)] mt-3 max-w-2xl leading-relaxed">
        Monthly &amp; annual plans <strong className="text-[var(--asc-text-dim)]">automatically renew</strong> at the end of each billing period using the payment method on file. You can cancel anytime from <span className="text-[var(--asc-brand)]">Profile → Manage billing</span> — access continues until the period ends. The $2.99 7-day trial is a single one-time charge and does NOT auto-renew.
      </div>

      {/* Interval toggle */}
      <div className="inline-flex items-center gap-1 mt-6 p-1 rounded-full border border-[var(--asc-border)]" style={{ background: "#15102B" }}>
        <button onClick={() => setIntervalKind("monthly")} data-testid="pricing-monthly-toggle" className="px-4 py-2 rounded-full text-sm font-bold transition" style={interval === "monthly" ? { background: "#FFB000", color: "#000" } : { color: "#C8C5E6" }}>Monthly</button>
        <button onClick={() => setIntervalKind("annual")} data-testid="pricing-annual-toggle" className="px-4 py-2 rounded-full text-sm font-bold transition flex items-center gap-1.5" style={interval === "annual" ? { background: "#FFB000", color: "#000" } : { color: "#C8C5E6" }}>
          Annual <span className="text-[10px] font-black px-1.5 py-0.5 rounded-full" style={{ background: "#000", color: "#FFB000" }}>SAVE 17%</span>
        </button>
      </div>

      <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4 mt-8">
        {tiers.map((t) => {
          const isCurrent = user?.tier === t.id;
          const isBusiness = t.id === "business";
          // Business tier uses effective_price_* (founding while seats remain, else standard).
          const stdMonthly = t.price_monthly;
          const stdAnnual = t.price_annual;
          const effMonthly = t.effective_price_monthly ?? stdMonthly;
          const effAnnual = t.effective_price_annual ?? stdAnnual;
          const price = interval === "annual" ? effAnnual : effMonthly;
          const monthEq = interval === "annual" ? (effAnnual / 12).toFixed(2) : null;
          const hasFoundingPromo = isBusiness && t.founding_active
            && (t.founding_price_monthly && t.founding_price_monthly < stdMonthly);
          return (
            <div key={t.id} data-testid={`pricing-tier-${t.id}`} className="asc-card p-6 relative"
              style={t.highlight ? { borderColor: "#FFB000", background: "rgba(255,176,0,0.04)" }
                    : isBusiness ? { borderColor: "#3B82F6", background: "rgba(59,130,246,0.04)" }
                    : isCurrent ? { borderColor: "#34D399" } : {}}>
              {t.highlight && <div className="absolute -top-2.5 left-6 px-2.5 py-1 rounded-full text-[10px] font-black tracking-wider" style={{ background: "#FFB000", color: "#000" }}>MOST POPULAR</div>}
              {isBusiness && hasFoundingPromo && (
                <div className="absolute -top-2.5 left-6 px-2.5 py-1 rounded-full text-[10px] font-black tracking-wider" style={{ background: "#3B82F6", color: "#fff" }} data-testid="pricing-business-founding-badge">
                  FOUNDING · {t.founding_seats_remaining}/{t.founding_seats_total} SEATS LEFT
                </div>
              )}
              {isBusiness && !hasFoundingPromo && (
                <div className="absolute -top-2.5 left-6 px-2.5 py-1 rounded-full text-[10px] font-black tracking-wider" style={{ background: "#3B82F6", color: "#fff" }}>
                  FOR TEAMS
                </div>
              )}
              {isCurrent && <div className="absolute -top-2.5 right-6 px-2.5 py-1 rounded-full text-[10px] font-black tracking-wider" style={{ background: "#34D399", color: "#000" }}>CURRENT</div>}

              <div className="asc-h2 text-2xl">{t.name}</div>
              <div className="flex items-end gap-1 mt-2 flex-wrap">
                {hasFoundingPromo && (
                  <span className="text-2xl text-[var(--asc-text-muted)] line-through pb-1" data-testid={`pricing-standard-price-${t.id}`}>
                    ${interval === "annual" ? (stdAnnual / 12).toFixed(0) : stdMonthly}
                  </span>
                )}
                <span className="text-5xl font-black" data-testid={`pricing-amount-${t.id}`}>
                  ${interval === "annual" ? monthEq : price}
                </span>
                <span className="text-[var(--asc-text-dim)] text-sm pb-2">/ mo</span>
              </div>
              {interval === "annual" ? (
                <div className="text-xs text-[var(--asc-success)] font-bold" data-testid={`pricing-annual-note-${t.id}`}>
                  Billed annually (${effAnnual}/yr){!isBusiness && " — 2 months free"}
                </div>
              ) : (
                <div className="text-xs text-[var(--asc-text-muted)]" data-testid={`pricing-monthly-note-${t.id}`}>
                  or ${effAnnual}/yr{!isBusiness && " — save 17%"}
                </div>
              )}
              {hasFoundingPromo && (
                <div className="text-[10px] mt-1 leading-relaxed" style={{ color: "#93C5FD" }} data-testid="pricing-founding-note">
                  Founding offer for the first {t.founding_seats_total} businesses. After {t.founding_seats_total} seats fill, standard rate is ${stdMonthly}/mo.
                </div>
              )}
              <p className="text-[var(--asc-text-dim)] text-sm mt-2">{t.blurb}</p>
              <ul className="mt-5 space-y-2">
                {t.features.map((f, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-[var(--asc-text-dim)]"><CheckCircle2 size={16} className={t.highlight ? "text-[var(--asc-brand)] mt-0.5 shrink-0" : isBusiness ? "text-[#3B82F6] mt-0.5 shrink-0" : "text-[var(--asc-success)] mt-0.5 shrink-0"} /> {f}</li>
                ))}
              </ul>
              {!isCurrent && (
                <button onClick={() => startCheckout(t.id)} disabled={busy === `${t.id}-${interval}`} data-testid={`pricing-cta-${t.id}`}
                  className="w-full mt-6 py-3 rounded-xl font-bold flex items-center justify-center gap-2 transition"
                  style={t.highlight ? { background: "#FFB000", color: "#000" }
                        : isBusiness ? { background: "#3B82F6", color: "#fff" }
                        : { background: "#1F183A", color: "#fff", border: "1px solid rgba(191,180,255,0.28)" }}>
                  {busy === `${t.id}-${interval}` ? "Loading…" : (interval === "annual" ? `Get ${t.name} annually` : `Choose ${t.name}`)}
                  {!busy && <ArrowRight size={16} />}
                </button>
              )}
              {t.id === "sage" && !user?.has_used_trial && (
                <button onClick={() => startCheckout("sage", "trial")} disabled={busy === "sage-trial"}
                  data-testid="pricing-trial-cta"
                  className="w-full mt-2 py-3 rounded-xl font-bold flex items-center justify-center gap-2 border"
                  style={{ background: "rgba(255,176,0,0.08)", color: "#FFB000", borderColor: "#FFB000" }}>
                  <Zap size={14} /> Try Sage for 7 days · just $2.99
                </button>
              )}
              {isCurrent && (
                <div className="w-full mt-6 py-3 rounded-xl font-bold text-center" style={{ background: "#1F183A", color: "#C8C5E6" }}>You&apos;re on this plan</div>
              )}
            </div>
          );
        })}
      </div>

      <div className="asc-card p-6 mt-8">
        <div className="flex items-center gap-2 mb-2"><Sparkles size={16} className="text-[var(--asc-brand)]" /> <span className="font-bold">Why upgrade?</span></div>
        <p className="text-[var(--asc-text-dim)] text-sm leading-relaxed">Pathfinder unlocks all 7 specialty paths and unlimited AI Tutor chat with Claude Sonnet 4.5. Sage adds 3 exclusive founder/strategy paths and priority response.</p>
      </div>
    </div>
  );
}
