import { Link } from "react-router-dom";
import { AlertTriangle, XCircle, CheckCircle2, Mail } from "lucide-react";
import SEO from "@/components/SEO";

const EFFECTIVE_DATE = "January 1, 2026";
const LAST_UPDATED = "January 1, 2026";
const COMPANY = "Ascendra Academy LLC";
const CONTACT_EMAIL = "ascendraacademy@yahoo.com";
const JURISDICTION = "State of Missouri, United States";

export default function NoRefunds() {
  return (
    <div data-testid="no-refunds-page" className="min-h-screen">
      <SEO
        title="No Refunds Policy — Ascendra Academy"
        description="All sales on Ascendra Academy are final. Read our no-refunds policy, cancellation terms, and how to manage your subscription."
        path="/no-refunds"
      />

      <section className="px-6 pt-16 pb-10 border-b border-[var(--asc-border)]">
        <div className="max-w-4xl mx-auto">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-[var(--asc-border-strong)] mb-5" style={{ background: "rgba(255,176,0,0.08)" }}>
            <AlertTriangle size={14} color="#FFB000" />
            <span className="asc-label">Billing Policy</span>
          </div>
          <h1 className="asc-h1 text-4xl sm:text-5xl" data-testid="no-refunds-heading">All Sales Final — No Refunds</h1>
          <p className="text-[var(--asc-text-dim)] mt-4 text-base max-w-2xl leading-relaxed">
            Please read this policy carefully before subscribing. By purchasing any subscription from
            {" "}{COMPANY}, you agree to the terms below.
          </p>
          <div className="flex flex-wrap gap-x-6 gap-y-1 mt-5 text-xs text-[var(--asc-text-muted)]">
            <span><b className="text-white/80">Effective:</b> {EFFECTIVE_DATE}</span>
            <span><b className="text-white/80">Last updated:</b> {LAST_UPDATED}</span>
          </div>
        </div>
      </section>

      <section className="px-6 py-12">
        <div className="max-w-3xl mx-auto space-y-10">
          {/* Headline statement */}
          <div className="asc-card p-7 border-2" style={{ borderColor: "rgba(255,176,0,0.5)", background: "rgba(255,176,0,0.04)" }}>
            <div className="flex items-start gap-4">
              <AlertTriangle size={28} color="#FFB000" className="flex-shrink-0 mt-1" />
              <div>
                <h2 className="asc-h2 text-2xl mb-3">Our policy in one line</h2>
                <p className="text-[var(--asc-text-dim)] leading-relaxed text-base">
                  <b className="text-white">All sales are final.</b> {COMPANY} does not offer refunds, credits, or
                  exchanges for any subscription fee or renewal charge — for any reason — once payment has been
                  processed.
                </p>
              </div>
            </div>
          </div>

          <Block title="What this means">
            <ul>
              <li>Initial subscription payments are non-refundable.</li>
              <li>Renewal charges (monthly or annual) are non-refundable.</li>
              <li>Unused subscription time after cancellation is non-refundable.</li>
              <li>Partial-month or partial-year billing is not prorated for refund.</li>
              <li>Refunds are not issued for change of mind, lack of use, or dissatisfaction.</li>
              <li>Refunds are not issued if you forget to cancel before a renewal date.</li>
            </ul>
          </Block>

          <Block title="What you can do instead">
            <div className="grid sm:grid-cols-2 gap-4">
              <div className="asc-card p-5">
                <CheckCircle2 size={20} color="#BFB4FF" className="mb-3" />
                <div className="font-bold text-white mb-1">Cancel anytime</div>
                <p className="text-sm text-[var(--asc-text-dim)] leading-relaxed">
                  Open your dashboard and cancel your subscription in seconds. You’ll keep access through the end
                  of your current billing period — then revert to free.
                </p>
              </div>
              <div className="asc-card p-5">
                <CheckCircle2 size={20} color="#BFB4FF" className="mb-3" />
                <div className="font-bold text-white mb-1">Keep your certificates</div>
                <p className="text-sm text-[var(--asc-text-dim)] leading-relaxed">
                  Any certificates you earned during your paid time remain accessible in your account forever,
                  even after you cancel or downgrade.
                </p>
              </div>
              <div className="asc-card p-5">
                <CheckCircle2 size={20} color="#BFB4FF" className="mb-3" />
                <div className="font-bold text-white mb-1">Pause is not required</div>
                <p className="text-sm text-[var(--asc-text-dim)] leading-relaxed">
                  Cancel without losing earned progress — you can resubscribe later at any time and pick up
                  exactly where you left off.
                </p>
              </div>
              <div className="asc-card p-5">
                <XCircle size={20} color="#FFB000" className="mb-3" />
                <div className="font-bold text-white mb-1">Disputes & chargebacks</div>
                <p className="text-sm text-[var(--asc-text-dim)] leading-relaxed">
                  Disputing a legitimate charge may result in account suspension. Please contact us first at{" "}
                  <a href={`mailto:${CONTACT_EMAIL}`} className="text-[var(--asc-brand)] hover:underline">{CONTACT_EMAIL}</a>.
                </p>
              </div>
            </div>
          </Block>

          <Block title="Why this policy exists">
            <p>
              Our subscriptions provide immediate, unlimited access to digital content, AI-generated lessons,
              and an AI tutor that incurs real per-query costs the moment you log in. Because the value is
              delivered the instant payment clears, we operate on an all-sales-final basis — the same way many
              digital education and SaaS products do.
            </p>
            <p>
              You can review all features before subscribing on our{" "}
              <Link to="/pricing" className="text-[var(--asc-brand)] hover:underline">pricing page</Link>.
            </p>
          </Block>

          <Block title="Legal disclosures">
            <p>
              To the extent permitted by law, this policy waives any statutory right of withdrawal or refund for
              digital content that begins delivery immediately upon purchase. This policy applies regardless of
              the payment method used.
            </p>
            <p>
              This policy is governed by the laws of the {JURISDICTION} and is incorporated by reference into
              our{" "}
              <Link to="/terms" className="text-[var(--asc-brand)] hover:underline">Terms of Service</Link>.
            </p>
          </Block>

          <Block title="Questions before you buy?">
            <div className="asc-card p-5 flex items-start gap-3" data-testid="no-refunds-contact-card">
              <Mail size={18} className="mt-0.5" color="#FFB000" />
              <div className="text-sm">
                <div className="font-bold text-white">Reach out before subscribing</div>
                <a href={`mailto:${CONTACT_EMAIL}`} className="text-[var(--asc-brand)] hover:underline" data-testid="no-refunds-contact-email">
                  {CONTACT_EMAIL}
                </a>
                <div className="text-[var(--asc-text-muted)] text-xs mt-1">We typically reply within 1–2 business days.</div>
              </div>
            </div>
          </Block>

          <div className="pt-8 border-t border-[var(--asc-border)] text-xs text-[var(--asc-text-muted)] text-center">
            See also:{" "}
            <Link to="/terms" className="text-[var(--asc-brand)] hover:underline">Terms of Service</Link>{" "}·{" "}
            <Link to="/privacy" className="text-[var(--asc-brand)] hover:underline">Privacy Policy</Link>
          </div>
        </div>
      </section>
    </div>
  );
}

function Block({ title, children }) {
  return (
    <section data-testid={`no-refunds-block-${title.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`} className="asc-prose">
      <h2 className="asc-h2 text-2xl mb-4">{title}</h2>
      <div className="space-y-4 text-[var(--asc-text-dim)] leading-relaxed text-[15px]">
        {children}
      </div>
    </section>
  );
}
