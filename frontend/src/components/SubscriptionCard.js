import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import {
  CreditCard, RefreshCw, AlertTriangle, RotateCw, Award, ArrowRight,
  Calendar, CheckCircle2, ExternalLink, Sparkles, ShieldCheck,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { formatDate } from "@/lib/utils";

// Visual config per state — uses tokens (not raw colors)
const STATE_THEME = {
  ACTIVE_RENEWING:  { color: "#34D399", label: "ACTIVE",        icon: ShieldCheck },
  ACTIVE_CANCELING: { color: "#FFB000", label: "CANCELING",     icon: AlertTriangle },
  PAST_DUE:         { color: "#FB7185", label: "PAYMENT FAILED", icon: AlertTriangle },
  LAPSED:           { color: "#BFB4FF", label: "LAPSED",        icon: RotateCw },
  FREE_NEVER_PAID:  { color: "#FFB000", label: "FREE TIER",     icon: Sparkles },
};

const TIER_LABEL = {
  ascender:   "Ascender",
  pathfinder: "Pathfinder",
  sage:       "Sage",
  business:   "Business",
};

/**
 * SubscriptionCard — smart card showing the user's billing state with the
 * correct CTA. Used on the Dashboard and Profile pages.
 *
 * Props:
 *   - compact (bool)  : when true, render a smaller variant (Dashboard)
 *   - autoLoad (bool) : default true; loads /api/billing/status on mount
 */
export default function SubscriptionCard({ compact = false, autoLoad = true }) {
  const { user, refresh: refreshUser } = useAuth();
  const nav = useNavigate();
  const [status, setStatus] = useState(null);
  const [busy, setBusy] = useState(null); // "portal" | "resume" | null

  const load = async () => {
    try {
      const s = await api.get("/billing/status");
      setStatus(s);
    } catch (e) {
      // Don't toast on failure — card simply won't render. Auth pages may not
      // have a logged-in user. Silent failure is correct.
      console.debug("billing/status load failed:", e?.message);
    }
  };
  useEffect(() => { if (autoLoad) load(); }, [autoLoad]); // eslint-disable-line react-hooks/exhaustive-deps

  const openPortal = async () => {
    setBusy("portal");
    try {
      const r = await api.post("/billing/portal", { return_url: window.location.href });
      if (r?.url) {
        window.location.assign(r.url);
      } else {
        toast.error("Portal session could not be created.");
      }
    } catch (e) {
      toast.error(e.message || "Could not open billing portal");
    } finally {
      setBusy(null);
    }
  };

  const resume = async () => {
    setBusy("resume");
    try {
      const r = await api.post("/billing/resume");
      toast.success(r.message || "Subscription resumed.");
      await load();
      if (refreshUser) refreshUser();
    } catch (e) {
      toast.error(e.message || "Could not resume subscription");
    } finally {
      setBusy(null);
    }
  };

  if (!user || !status) return null;

  const theme = STATE_THEME[status.state] || STATE_THEME.FREE_NEVER_PAID;
  const Icon = theme.icon;
  const tierLabel = TIER_LABEL[status.tier] || "Free";
  const intervalLabel = status.interval === "annual" ? "/yr" : status.interval === "monthly" ? "/mo" : "";

  // Common header section
  const header = (
    <div className="flex items-center justify-between gap-3">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl grid place-items-center shrink-0"
              style={{ background: `${theme.color}22`, border: `1px solid ${theme.color}55` }}>
          <Icon size={18} color={theme.color} />
        </div>
        <div>
          <div className="asc-label">Subscription</div>
          <div className="font-bold text-lg">
            {status.tier === "free" ? "Free Tier" : tierLabel}
            {status.amount_usd ? <span className="text-sm text-[var(--asc-text-muted)] font-normal ml-1">· ${status.amount_usd}{intervalLabel}</span> : null}
          </div>
        </div>
      </div>
      <span className="px-2 py-1 rounded-full text-[10px] font-black tracking-wider"
             style={{ background: `${theme.color}22`, color: theme.color }}
             data-testid="subscription-state-pill">
        {theme.label}
      </span>
    </div>
  );

  // State-specific bodies
  let body = null;
  let actions = null;

  if (status.state === "ACTIVE_RENEWING") {
    body = (
      <p className="text-sm text-[var(--asc-text-dim)] mt-2">
        <Calendar size={12} className="inline -mt-0.5 mr-1" />
        Renews automatically on <strong className="text-white">{formatDate(status.renews_at)}</strong>.
      </p>
    );
    actions = (
      <Button onClick={openPortal} disabled={busy === "portal"} className="asc-btn-secondary" data-testid="sub-manage-btn">
        <CreditCard size={14} className="mr-1" />
        {busy === "portal" ? "Opening…" : "Manage billing"}
      </Button>
    );
  } else if (status.state === "ACTIVE_CANCELING") {
    body = (
      <div className="mt-2">
        <p className="text-sm" style={{ color: "#FFB000" }}>
          <AlertTriangle size={12} className="inline -mt-0.5 mr-1" />
          Your subscription ends on <strong>{formatDate(status.ends_at)}</strong> — after that you&apos;ll lose access to paid paths.
        </p>
        <p className="text-xs text-[var(--asc-text-muted)] mt-2">
          Tap <strong className="text-white">Resume</strong> to keep your plan running uninterrupted.
        </p>
      </div>
    );
    actions = (
      <div className="flex gap-2 flex-wrap">
        <Button
          onClick={resume}
          disabled={busy === "resume"}
          className="asc-btn-primary"
          data-testid="sub-resume-btn"
          style={{ background: "linear-gradient(135deg, #FFB000, #FF6B35)" }}
        >
          <RotateCw size={14} className={`mr-1 ${busy === "resume" ? "animate-spin" : ""}`} />
          {busy === "resume" ? "Resuming…" : "Resume subscription"}
        </Button>
        <Button onClick={openPortal} disabled={busy === "portal"} className="asc-btn-secondary" data-testid="sub-manage-btn">
          <CreditCard size={14} className="mr-1" />
          Manage
        </Button>
      </div>
    );
  } else if (status.state === "PAST_DUE") {
    body = (
      <div className="mt-2">
        <p className="text-sm" style={{ color: "#FB7185" }}>
          <AlertTriangle size={12} className="inline -mt-0.5 mr-1" />
          Your last payment failed. Update your card to keep access — Stripe will retry automatically once you do.
        </p>
      </div>
    );
    actions = (
      <Button
        onClick={openPortal}
        disabled={busy === "portal"}
        className="asc-btn-primary"
        data-testid="sub-update-payment-btn"
        style={{ background: "linear-gradient(135deg, #FB7185, #FFB000)" }}
      >
        <CreditCard size={14} className="mr-1" />
        {busy === "portal" ? "Opening…" : "Update payment method"}
      </Button>
    );
  } else if (status.state === "LAPSED") {
    body = (
      <div className="mt-2 space-y-3">
        <p className="text-sm text-[var(--asc-text-dim)]">
          Your previous subscription ended. You&apos;re on the free tier now — paid paths are locked, but everything else (and your progress) is intact.
        </p>
        {status.certificates_count > 0 && (
          <div className="asc-card p-3 flex items-center gap-2 text-sm"
                style={{ background: "rgba(52,211,153,0.08)", borderColor: "rgba(52,211,153,0.4)" }}
                data-testid="lapsed-certs-reassure">
            <Award size={16} className="text-[#34D399] shrink-0" />
            <div>
              <strong className="text-white">Your {status.certificates_count} certificate{status.certificates_count === 1 ? "" : "s"} {status.certificates_count === 1 ? "is" : "are"} safe.</strong>{" "}
              You earned {status.certificates_count === 1 ? "it" : "them"} — {status.certificates_count === 1 ? "it" : "they"} stay{status.certificates_count === 1 ? "s" : ""} yours forever, regardless of your plan.
              {" "}
              <Link to="/profile" className="underline text-[#34D399]" data-testid="lapsed-view-certs-link">View →</Link>
            </div>
          </div>
        )}
      </div>
    );
    actions = (
      <div className="flex gap-2 flex-wrap">
        <Button
          onClick={() => nav("/pricing")}
          className="asc-btn-primary"
          data-testid="sub-reactivate-btn"
          style={{ background: "linear-gradient(135deg, #FFB000, #FF6B35)" }}
        >
          <RotateCw size={14} className="mr-1" />
          Reactivate plan
        </Button>
        {status.can_open_portal && (
          <Button onClick={openPortal} disabled={busy === "portal"} className="asc-btn-secondary" data-testid="sub-history-btn">
            <CreditCard size={14} className="mr-1" />
            Billing history
          </Button>
        )}
      </div>
    );
  } else {
    // FREE_NEVER_PAID
    body = (
      <p className="text-sm text-[var(--asc-text-dim)] mt-2">
        Unlock every path, weekly flagship courses, and unlimited custom path generation. Cancel anytime.
      </p>
    );
    actions = (
      <Button
        onClick={() => nav("/pricing")}
        className="asc-btn-primary"
        data-testid="sub-upgrade-btn"
        style={{ background: "linear-gradient(135deg, #FFB000, #FF6B35)" }}
      >
        <Sparkles size={14} className="mr-1" />
        View plans
        <ArrowRight size={14} className="ml-1" />
      </Button>
    );
  }

  return (
    <div className={`asc-card ${compact ? "p-4" : "p-6"}`} data-testid="subscription-card">
      {header}
      {body}
      <div className="mt-4">{actions}</div>
    </div>
  );
}
