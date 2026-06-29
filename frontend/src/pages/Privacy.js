import { Link } from "react-router-dom";
import { Shield, Mail } from "lucide-react";
import SEO from "@/components/SEO";

const EFFECTIVE_DATE = "January 1, 2026";
const LAST_UPDATED = "January 1, 2026";
const COMPANY = "Ascendra Academy LLC";
const CONTACT_EMAIL = "ascendraacademy@yahoo.com";
const SITE = "ascendraacademy.com";
const JURISDICTION = "State of Missouri, United States";

const SECTIONS = [
  { id: "overview", title: "1. Overview" },
  { id: "information", title: "2. Information We Collect" },
  { id: "use", title: "3. How We Use Information" },
  { id: "legal-bases", title: "4. Legal Bases (GDPR)" },
  { id: "sharing", title: "5. How We Share Information" },
  { id: "processors", title: "6. Third-Party Processors" },
  { id: "cookies", title: "7. Cookies & Tracking" },
  { id: "retention", title: "8. Data Retention" },
  { id: "security", title: "9. Security" },
  { id: "rights", title: "10. Your Rights (CCPA, GDPR)" },
  { id: "children", title: "11. Children’s Privacy" },
  { id: "international", title: "12. International Transfers" },
  { id: "changes", title: "13. Changes to This Policy" },
  { id: "contact", title: "14. Contact Us" },
];

export default function Privacy() {
  return (
    <div data-testid="privacy-page" className="min-h-screen">
      <SEO
        title="Privacy Policy — Ascendra Academy"
        description="How Ascendra Academy collects, uses, and protects your personal information. CCPA & GDPR compliant. Learn about your data rights and how to exercise them."
        path="/privacy"
      />

      {/* Hero */}
      <section className="px-6 pt-16 pb-10 border-b border-[var(--asc-border)]">
        <div className="max-w-4xl mx-auto">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-[var(--asc-border-strong)] mb-5" style={{ background: "rgba(124,58,237,0.12)" }}>
            <Shield size={14} color="#BFB4FF" />
            <span className="asc-label">Legal</span>
          </div>
          <h1 className="asc-h1 text-4xl sm:text-5xl" data-testid="privacy-heading">Privacy Policy</h1>
          <p className="text-[var(--asc-text-dim)] mt-4 text-base max-w-2xl leading-relaxed">
            Your privacy matters. This policy explains what information {COMPANY} collects from
            {" "}{SITE}, how we use it, who we share it with, and the rights you have over it.
          </p>
          <div className="flex flex-wrap gap-x-6 gap-y-1 mt-5 text-xs text-[var(--asc-text-muted)]">
            <span><b className="text-white/80">Effective:</b> {EFFECTIVE_DATE}</span>
            <span><b className="text-white/80">Last updated:</b> {LAST_UPDATED}</span>
          </div>
        </div>
      </section>

      <section className="px-6 py-12">
        <div className="max-w-4xl mx-auto grid lg:grid-cols-[220px_1fr] gap-10">
          <nav className="hidden lg:block sticky top-24 self-start text-sm" data-testid="privacy-toc">
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
            <Block id="overview" title="1. Overview">
              <p>
                {COMPANY} (“Ascendra,” “we,” “us,” “our”) operates the website at {SITE} and the related
                AI-learning Services. This Privacy Policy describes how we collect, use, disclose, and protect
                personal information when you visit, register for, or use the Services.
              </p>
              <p>
                By using the Services, you consent to the practices described here. If you do not agree, please do
                not use the Services.
              </p>
            </Block>

            <Block id="information" title="2. Information We Collect">
              <p>We collect the following categories of personal information:</p>
              <ul>
                <li>
                  <b className="text-white">Account information.</b> Name (optional), email address, password
                  (stored hashed), and your selected subscription tier.
                </li>
                <li>
                  <b className="text-white">Onboarding & quiz responses.</b> Goals, experience level, learning
                  preferences, and other answers you submit through the onboarding quiz or learning-path generator.
                </li>
                <li>
                  <b className="text-white">Learning activity.</b> Lessons viewed, progress, streaks, XP, quiz
                  answers, tutor conversations, and certificates earned.
                </li>
                <li>
                  <b className="text-white">Payment information.</b> We do <i>not</i> store full payment card data.
                  Stripe, Inc. processes payments on our behalf and provides us with a transaction ID, last 4 digits
                  of your card, billing country, and subscription status.
                </li>
                <li>
                  <b className="text-white">Device & usage data.</b> IP address (truncated for analytics), browser
                  type, operating system, referring/exit pages, pages viewed, timestamps, and similar diagnostic
                  data collected automatically through our pageview tracker.
                </li>
                <li>
                  <b className="text-white">Communications.</b> Messages you send us (e.g., support emails) and your
                  preferences for receiving marketing or transactional email.
                </li>
              </ul>
            </Block>

            <Block id="use" title="3. How We Use Information">
              <p>We use personal information to:</p>
              <ul>
                <li>Provide, operate, and maintain the Services, including delivering personalized lessons.</li>
                <li>Process subscriptions, payments, renewals, and cancellations through Stripe.</li>
                <li>Generate AI-powered learning content, tutor responses, and learning paths using third-party AI providers (see Section 6).</li>
                <li>Send transactional email (account confirmations, receipts, password resets, lesson reminders) via Resend.</li>
                <li>Send marketing email about new features or content, when you have opted in. You can unsubscribe at any time.</li>
                <li>Improve, troubleshoot, and analyze the Services through aggregated usage statistics.</li>
                <li>Detect, prevent, and respond to fraud, abuse, or security incidents.</li>
                <li>Comply with legal obligations and enforce our Terms of Service.</li>
              </ul>
            </Block>

            <Block id="legal-bases" title="4. Legal Bases (for EU/UK users)">
              <p>If you are in the EU, UK, or EEA, our legal bases for processing your personal information are:</p>
              <ul>
                <li><b className="text-white">Contract:</b> to provide the Services you have requested.</li>
                <li><b className="text-white">Consent:</b> for marketing email and optional analytics; you may withdraw consent at any time.</li>
                <li><b className="text-white">Legitimate interests:</b> to improve our Services, prevent fraud, and protect our rights.</li>
                <li><b className="text-white">Legal obligation:</b> to comply with applicable laws (e.g., tax, accounting).</li>
              </ul>
            </Block>

            <Block id="sharing" title="5. How We Share Information">
              <p>We do <b className="text-white">not</b> sell your personal information. We share information only:</p>
              <ul>
                <li>With trusted third-party processors that operate the Services on our behalf (Section 6).</li>
                <li>When required by law, subpoena, or other legal process, or to respond to lawful government requests.</li>
                <li>To investigate, prevent, or take action regarding suspected fraud, security threats, or violations of our Terms.</li>
                <li>In connection with a merger, acquisition, financing, or sale of business assets, with appropriate confidentiality protections.</li>
                <li>With your consent or at your direction.</li>
              </ul>
            </Block>

            <Block id="processors" title="6. Third-Party Processors">
              <p>We rely on the following processors to operate the Services. Each is bound by its own privacy practices:</p>
              <ul>
                <li><b className="text-white">Stripe, Inc.</b> — Payment processing & subscription management.</li>
                <li><b className="text-white">Resend</b> — Transactional and marketing email delivery.</li>
                <li><b className="text-white">Anthropic PBC</b> — Claude AI for tutor and lesson generation.</li>
                <li><b className="text-white">OpenAI, L.L.C.</b> — GPT models and text-to-speech narration.</li>
                <li><b className="text-white">Google LLC</b> — Gemini models for select content generation.</li>
                <li><b className="text-white">MongoDB Atlas</b> — Encrypted cloud database hosting.</li>
                <li><b className="text-white">Hosting provider</b> — Cloud infrastructure for the application.</li>
              </ul>
              <p>
                AI prompts and quiz responses may be sent to AI providers to generate responses. We do not
                authorize these providers to use your prompts to train their models when commercially-available
                no-training endpoints are in use.
              </p>
            </Block>

            <Block id="cookies" title="7. Cookies & Tracking">
              <p>
                We use first-party cookies and local storage to keep you signed in, remember your preferences
                (such as quiz progress), and measure usage. We do not currently use third-party advertising or
                cross-site tracking cookies.
              </p>
              <p>
                Most browsers allow you to refuse or delete cookies. Note that disabling cookies may impair the
                Services (for example, you may be signed out automatically).
              </p>
            </Block>

            <Block id="retention" title="8. Data Retention">
              <p>We retain personal information for as long as your account is active or as needed to provide the
              Services. After account deletion, we retain limited records (e.g., billing history) for up to seven
              (7) years to comply with tax, accounting, and legal obligations. Backups containing personal
              information are securely overwritten on a rolling schedule.</p>
            </Block>

            <Block id="security" title="9. Security">
              <p>
                We employ industry-standard administrative, technical, and physical safeguards to protect your
                information, including TLS encryption in transit, encrypted-at-rest databases, hashed passwords,
                least-privilege access controls, and restricted API keys. No method of transmission or storage is
                100% secure, however, and we cannot guarantee absolute security.
              </p>
            </Block>

            <Block id="rights" title="10. Your Rights (CCPA, GDPR & similar laws)">
              <p>Depending on where you live, you may have the right to:</p>
              <ul>
                <li><b className="text-white">Access</b> the personal information we hold about you.</li>
                <li><b className="text-white">Correct</b> inaccurate or incomplete information.</li>
                <li><b className="text-white">Delete</b> your personal information (“right to be forgotten”).</li>
                <li><b className="text-white">Port</b> your data in a portable, machine-readable format.</li>
                <li><b className="text-white">Object to</b> or <b className="text-white">restrict</b> certain processing.</li>
                <li><b className="text-white">Opt out</b> of marketing email at any time via the unsubscribe link or by contacting us.</li>
                <li><b className="text-white">Withdraw consent</b> where we rely on consent as the legal basis.</li>
                <li><b className="text-white">Not be discriminated against</b> for exercising your CCPA rights.</li>
              </ul>
              <p>
                To exercise these rights, email{" "}
                <a className="text-[var(--asc-brand)] hover:underline" href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</a>{" "}
                with the subject line “Privacy Request.” We will respond within 30 days (45 days for CCPA requests
                where additional time is needed, with notice). We may need to verify your identity before fulfilling
                a request.
              </p>
              <p>
                <b className="text-white">“Do Not Sell or Share My Personal Information” (California residents):</b>{" "}
                We do not sell personal information and do not share it for cross-context behavioral advertising.
              </p>
            </Block>

            <Block id="children" title="11. Children’s Privacy">
              <p>
                The Services are not directed to children under 13. We do not knowingly collect personal
                information from anyone under 13. If you believe a child under 13 has provided us with personal
                information, contact us at {CONTACT_EMAIL} and we will promptly delete it.
              </p>
            </Block>

            <Block id="international" title="12. International Transfers">
              <p>
                {COMPANY} is based in the {JURISDICTION}. If you access the Services from outside the United
                States, your information will be transferred to, stored, and processed in the U.S. By using the
                Services, you consent to these transfers. Where required, we use appropriate safeguards (such as
                Standard Contractual Clauses) for cross-border transfers.
              </p>
            </Block>

            <Block id="changes" title="13. Changes to This Policy">
              <p>
                We may update this Privacy Policy from time to time. Material changes will be communicated by
                email or via a prominent notice on the Services. The “Last updated” date at the top of this page
                will always reflect the most recent revision. Continued use of the Services after changes become
                effective constitutes acceptance.
              </p>
            </Block>

            <Block id="contact" title="14. Contact Us">
              <p>Questions, concerns, or requests about your data? Reach out:</p>
              <div className="asc-card p-5 mt-3 flex items-start gap-3" data-testid="privacy-contact-card">
                <Mail size={18} className="mt-0.5" color="#BFB4FF" />
                <div className="text-sm">
                  <div className="font-bold text-white">{COMPANY}</div>
                  <a href={`mailto:${CONTACT_EMAIL}`} className="text-[var(--asc-brand)] hover:underline" data-testid="privacy-contact-email">
                    {CONTACT_EMAIL}
                  </a>
                  <div className="text-[var(--asc-text-muted)] text-xs mt-1">{JURISDICTION}</div>
                </div>
              </div>
            </Block>

            <div className="pt-8 border-t border-[var(--asc-border)] text-xs text-[var(--asc-text-muted)]">
              See also: <Link to="/terms" className="text-[var(--asc-brand)] hover:underline">Terms of Service</Link>
              {" "}·{" "}
              <Link to="/no-refunds" className="text-[var(--asc-brand)] hover:underline">No Refunds Policy</Link>
            </div>
          </article>
        </div>
      </section>
    </div>
  );
}

function Block({ id, title, children }) {
  return (
    <section id={id} data-testid={`privacy-section-${id}`} className="scroll-mt-24">
      <h2 className="asc-h2 text-2xl sm:text-3xl mb-4">{title}</h2>
      <div className="space-y-4 text-[var(--asc-text-dim)] leading-relaxed text-[15px]">
        {children}
      </div>
    </section>
  );
}
