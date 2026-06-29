import { Link } from "react-router-dom";
import { FileText, Mail, AlertTriangle } from "lucide-react";
import SEO from "@/components/SEO";

const EFFECTIVE_DATE = "January 1, 2026";
const LAST_UPDATED = "January 1, 2026";
const COMPANY = "Ascendra Academy LLC";
const CONTACT_EMAIL = "ascendraacademy@yahoo.com";
const SITE = "ascendraacademy.com";
const JURISDICTION = "State of Missouri, United States";

const SECTIONS = [
  { id: "acceptance", title: "1. Acceptance of Terms" },
  { id: "eligibility", title: "2. Eligibility & Accounts" },
  { id: "services", title: "3. The Services" },
  { id: "subscriptions", title: "4. Subscriptions & Billing" },
  { id: "no-refunds", title: "5. All Sales Final — No Refunds" },
  { id: "cancellation", title: "6. Cancellation & Certificate Retention" },
  { id: "ai-content", title: "7. AI-Generated Content Disclaimer" },
  { id: "user-conduct", title: "8. User Conduct & Acceptable Use" },
  { id: "ip", title: "9. Intellectual Property" },
  { id: "third-parties", title: "10. Third-Party Services" },
  { id: "termination", title: "11. Termination" },
  { id: "disclaimers", title: "12. Disclaimers" },
  { id: "liability", title: "13. Limitation of Liability" },
  { id: "indemnification", title: "14. Indemnification" },
  { id: "governing-law", title: "15. Governing Law & Disputes" },
  { id: "changes", title: "16. Changes to These Terms" },
  { id: "contact", title: "17. Contact Us" },
];

export default function Terms() {
  return (
    <div data-testid="terms-page" className="min-h-screen">
      <SEO
        title="Terms of Service — Ascendra Academy"
        description="The Terms of Service governing your use of Ascendra Academy, the AI learning platform. Read our subscription, billing, and acceptable use policies."
        path="/terms"
      />

      {/* Hero */}
      <section className="px-6 pt-16 pb-10 border-b border-[var(--asc-border)]">
        <div className="max-w-4xl mx-auto">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-[var(--asc-border-strong)] mb-5" style={{ background: "rgba(255,176,0,0.08)" }}>
            <FileText size={14} color="#FFB000" />
            <span className="asc-label">Legal</span>
          </div>
          <h1 className="asc-h1 text-4xl sm:text-5xl" data-testid="terms-heading">Terms of Service</h1>
          <p className="text-[var(--asc-text-dim)] mt-4 text-base max-w-2xl leading-relaxed">
            These terms govern your access to and use of {COMPANY} and its services at {SITE}.
            By using our services, you agree to be bound by these terms.
          </p>
          <div className="flex flex-wrap gap-x-6 gap-y-1 mt-5 text-xs text-[var(--asc-text-muted)]">
            <span><b className="text-white/80">Effective:</b> {EFFECTIVE_DATE}</span>
            <span><b className="text-white/80">Last updated:</b> {LAST_UPDATED}</span>
          </div>
        </div>
      </section>

      {/* Body */}
      <section className="px-6 py-12">
        <div className="max-w-4xl mx-auto grid lg:grid-cols-[220px_1fr] gap-10">
          {/* TOC */}
          <nav className="hidden lg:block sticky top-24 self-start text-sm" data-testid="terms-toc">
            <div className="asc-label mb-3">Contents</div>
            <ul className="space-y-2">
              {SECTIONS.map((s) => (
                <li key={s.id}>
                  <a href={`#${s.id}`} className="text-[var(--asc-text-dim)] hover:text-white transition">
                    {s.title}
                  </a>
                </li>
              ))}
            </ul>
          </nav>

          <article className="asc-prose space-y-10">
            <Block id="acceptance" title="1. Acceptance of Terms">
              <p>
                These Terms of Service (“Terms”) form a legally binding agreement between you (“you,” “user”) and
                {" "}{COMPANY} (“Ascendra,” “we,” “us,” “our”), governing your access to and use of the website at
                {" "}{SITE}, related applications, content, and services (collectively, the “Services”).
              </p>
              <p>
                By creating an account, completing a purchase, or otherwise accessing the Services, you confirm that
                you have read, understood, and agreed to be bound by these Terms and our{" "}
                <Link to="/privacy" className="text-[var(--asc-brand)] hover:underline">Privacy Policy</Link>. If you do
                not agree, do not use the Services.
              </p>
            </Block>

            <Block id="eligibility" title="2. Eligibility & Accounts">
              <p>
                You must be at least 13 years old to use the Services. Users between 13 and 17 must have permission
                from a parent or legal guardian, who agrees to be bound by these Terms on the minor’s behalf. By using
                the Services, you represent that you meet these requirements.
              </p>
              <p>
                You are responsible for: (a) maintaining the confidentiality of your login credentials, (b) all
                activities that occur under your account, and (c) promptly notifying us of any unauthorized use. We
                may suspend or terminate accounts that we reasonably believe have been compromised or used in
                violation of these Terms.
              </p>
            </Block>

            <Block id="services" title="3. The Services">
              <p>
                Ascendra provides AI-powered educational content, interactive lessons, learning paths, prompt
                libraries, an AI tutor, certificates of completion, and related features. The Services are provided
                on an “as is” and “as available” basis. We may add, modify, or remove features at any time without
                prior notice.
              </p>
            </Block>

            <Block id="subscriptions" title="4. Subscriptions & Billing">
              <p>
                Certain features require a paid subscription. By selecting a paid plan, you authorize us and our
                payment processor, Stripe, Inc., to charge the payment method on file for the listed price plus any
                applicable taxes.
              </p>
              <p>
                <b className="text-white">Auto-renewal.</b> Subscriptions automatically renew at the end of each
                billing period (monthly or annually, depending on the plan you select) at the then-current rate,
                until cancelled. You authorize recurring charges until you cancel.
              </p>
              <p>
                <b className="text-white">Price changes.</b> We may change subscription prices. Where price changes
                apply to an existing subscription, we will provide at least thirty (30) days advance notice via
                email. Continued use of the Services after a price change constitutes acceptance of the new price.
              </p>
              <p>
                <b className="text-white">Failed payments.</b> If we are unable to charge your payment method, your
                access to paid features may be suspended until payment is resolved.
              </p>
            </Block>

            <Block id="no-refunds" title="5. All Sales Final — No Refunds" highlight>
              <p className="flex items-start gap-3">
                <AlertTriangle size={20} className="flex-shrink-0 mt-0.5" color="#FFB000" />
                <span>
                  <b className="text-white">All sales are final.</b> {COMPANY} does not offer refunds, credits, or
                  exchanges for any subscription fees, renewal charges, or other payments — for any reason —
                  including but not limited to unused subscription time, change of mind, dissatisfaction with content,
                  failure to use the Services, or partial use of a billing period.
                </span>
              </p>
              <p>
                Because Services are delivered digitally and immediately upon purchase, you waive any statutory
                right to a refund where permitted by applicable law. You may cancel your subscription at any time to
                prevent future charges (see Section 6), but no refund will be issued for the current or any prior
                billing period.
              </p>
              <p>
                This no-refund policy is a material part of the consideration for the Services. If you do not agree
                with this policy, do not subscribe.
              </p>
            </Block>

            <Block id="cancellation" title="6. Cancellation & Certificate Retention">
              <p>
                You may cancel your subscription at any time from your account dashboard. Cancellation stops future
                auto-renewals. You will retain access to paid features through the end of your then-current paid
                billing period; after that, your account reverts to the free tier.
              </p>
              <p>
                <b className="text-white">Certificates earned remain yours.</b> Any certificates of completion you
                have earned before cancellation remain accessible in your account, even after you downgrade to the
                free tier or cancel your subscription.
              </p>
            </Block>

            <Block id="ai-content" title="7. AI-Generated Content Disclaimer">
              <p>
                Many lessons, summaries, prompts, and tutor responses on Ascendra are generated or augmented by
                third-party large language models (including, but not limited to, Anthropic Claude, OpenAI GPT, and
                Google Gemini). AI-generated content may contain inaccuracies, omissions, outdated information, or
                content that does not reflect our views.
              </p>
              <p>
                You should independently verify any AI-generated information before relying on it, especially for
                decisions involving health, finance, legal, professional, or safety considerations. Ascendra is an
                educational tool, not professional advice.
              </p>
            </Block>

            <Block id="user-conduct" title="8. User Conduct & Acceptable Use">
              <p>You agree not to:</p>
              <ul>
                <li>Resell, redistribute, or commercially exploit Services without our written permission.</li>
                <li>Share your account credentials with others or use another person’s account without authorization.</li>
                <li>Scrape, crawl, mass-download, or use automated systems to extract Services content.</li>
                <li>Reverse engineer, decompile, or attempt to extract the source code or prompt structures.</li>
                <li>Use the Services to generate, distribute, or amplify unlawful, harassing, or harmful content.</li>
                <li>Interfere with, disrupt, or attempt to gain unauthorized access to the Services or any related systems.</li>
                <li>Submit content that infringes any third party’s intellectual property, privacy, or other rights.</li>
              </ul>
              <p>
                We may suspend or terminate accounts that violate these rules, without notice and without refund.
              </p>
            </Block>

            <Block id="ip" title="9. Intellectual Property">
              <p>
                All Services content — including lessons, paths, prompts, designs, logos, marks, copy, and software
                — is owned by {COMPANY} or its licensors and is protected by intellectual property laws. Subject to
                your compliance with these Terms, we grant you a limited, non-exclusive, non-transferable,
                revocable license to access and use the Services for your personal, non-commercial educational
                purposes only.
              </p>
              <p>
                Certificates issued to you reflect a personal achievement and may be shared for non-commercial
                personal-branding purposes. Reselling, modifying, or impersonating Ascendra certificates is
                prohibited.
              </p>
            </Block>

            <Block id="third-parties" title="10. Third-Party Services">
              <p>
                The Services rely on third-party providers including (but not limited to) Stripe (payments), Resend
                (transactional email), Anthropic, OpenAI, and Google (AI models), and our hosting provider. Your use
                of those parts of the Services is also subject to those providers’ respective terms.
              </p>
            </Block>

            <Block id="termination" title="11. Termination">
              <p>
                We may suspend or terminate your access to the Services at any time, for any reason, including
                without limitation if we believe you have violated these Terms. Upon termination, your right to use
                the Services ceases immediately. Sections of these Terms that by their nature should survive
                termination will survive, including Sections 5 (No Refunds), 9, 12, 13, 14, and 15.
              </p>
            </Block>

            <Block id="disclaimers" title="12. Disclaimers">
              <p>
                THE SERVICES ARE PROVIDED “AS IS” AND “AS AVAILABLE,” WITHOUT WARRANTIES OF ANY KIND, WHETHER
                EXPRESS, IMPLIED, OR STATUTORY, INCLUDING WITHOUT LIMITATION WARRANTIES OF MERCHANTABILITY, FITNESS
                FOR A PARTICULAR PURPOSE, NON-INFRINGEMENT, ACCURACY, OR THAT THE SERVICES WILL BE UNINTERRUPTED OR
                ERROR-FREE. WE DO NOT WARRANT THAT AI-GENERATED OUTPUT IS ACCURATE, COMPLETE, OR FIT FOR ANY
                PARTICULAR PURPOSE.
              </p>
            </Block>

            <Block id="liability" title="13. Limitation of Liability">
              <p>
                TO THE MAXIMUM EXTENT PERMITTED BY APPLICABLE LAW, IN NO EVENT WILL {COMPANY.toUpperCase()}, ITS
                AFFILIATES, OR THEIR RESPECTIVE OFFICERS, EMPLOYEES, OR AGENTS BE LIABLE FOR ANY INDIRECT,
                INCIDENTAL, SPECIAL, CONSEQUENTIAL, EXEMPLARY, OR PUNITIVE DAMAGES, OR ANY LOSS OF PROFITS, DATA,
                GOODWILL, OR OTHER INTANGIBLE LOSSES, ARISING OUT OF OR RELATING TO YOUR USE OF THE SERVICES.
              </p>
              <p>
                OUR TOTAL AGGREGATE LIABILITY UNDER THESE TERMS WILL NOT EXCEED THE GREATER OF (A) THE AMOUNTS YOU
                PAID US IN THE TWELVE (12) MONTHS PRECEDING THE EVENT GIVING RISE TO THE CLAIM, OR (B) ONE HUNDRED
                U.S. DOLLARS ($100.00).
              </p>
            </Block>

            <Block id="indemnification" title="14. Indemnification">
              <p>
                You agree to indemnify, defend, and hold harmless {COMPANY} and its officers, directors, employees,
                and agents from any claims, damages, losses, liabilities, and expenses (including reasonable
                attorneys’ fees) arising out of or related to (a) your use or misuse of the Services, (b) your
                violation of these Terms, or (c) your violation of any rights of any third party.
              </p>
            </Block>

            <Block id="governing-law" title="15. Governing Law & Disputes">
              <p>
                These Terms are governed by the laws of the {JURISDICTION}, without regard to its conflict-of-laws
                rules. The exclusive venue for any dispute arising out of or related to these Terms or the Services
                will be the state or federal courts located in the {JURISDICTION}, and you consent to the personal
                jurisdiction of those courts.
              </p>
              <p>
                Before filing any claim, you agree to first contact us at <a className="text-[var(--asc-brand)] hover:underline" href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</a> and attempt to resolve the dispute informally for at least sixty (60) days.
              </p>
            </Block>

            <Block id="changes" title="16. Changes to These Terms">
              <p>
                We may revise these Terms from time to time. The “Last updated” date at the top of this page
                reflects the most recent revision. Material changes will be communicated by email or via a notice
                on the Services. Continued use of the Services after changes become effective constitutes acceptance
                of the revised Terms.
              </p>
            </Block>

            <Block id="contact" title="17. Contact Us">
              <p>
                Questions about these Terms? Reach out:
              </p>
              <div className="asc-card p-5 mt-3 flex items-start gap-3" data-testid="terms-contact-card">
                <Mail size={18} className="mt-0.5" color="#FFB000" />
                <div className="text-sm">
                  <div className="font-bold text-white">{COMPANY}</div>
                  <a href={`mailto:${CONTACT_EMAIL}`} className="text-[var(--asc-brand)] hover:underline" data-testid="terms-contact-email">
                    {CONTACT_EMAIL}
                  </a>
                  <div className="text-[var(--asc-text-muted)] text-xs mt-1">{JURISDICTION}</div>
                </div>
              </div>
            </Block>

            <div className="pt-8 border-t border-[var(--asc-border)] text-xs text-[var(--asc-text-muted)]">
              See also: <Link to="/privacy" className="text-[var(--asc-brand)] hover:underline">Privacy Policy</Link>
              {" "}·{" "}
              <Link to="/no-refunds" className="text-[var(--asc-brand)] hover:underline">No Refunds Policy</Link>
            </div>
          </article>
        </div>
      </section>
    </div>
  );
}

function Block({ id, title, children, highlight }) {
  return (
    <section
      id={id}
      data-testid={`terms-section-${id}`}
      className={`scroll-mt-24 ${highlight ? "asc-card p-6 border-2" : ""}`}
      style={highlight ? { borderColor: "rgba(255,176,0,0.5)", background: "rgba(255,176,0,0.04)" } : {}}
    >
      <h2 className="asc-h2 text-2xl sm:text-3xl mb-4">{title}</h2>
      <div className="space-y-4 text-[var(--asc-text-dim)] leading-relaxed text-[15px]">
        {children}
      </div>
    </section>
  );
}
