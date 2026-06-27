import { useEffect, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { Helmet } from "react-helmet-async";
import { api } from "@/lib/api";
import Loader from "@/components/Loader";
import { ArrowRight, CheckCircle2, AlertTriangle, Lightbulb, Wrench, HelpCircle, Sparkles, ChevronRight } from "lucide-react";

export default function LearnHub() {
  const { modelSlug, useCaseSlug } = useParams();
  const nav = useNavigate();
  const [page, setPage] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    const url = useCaseSlug ? `/seo/page/${modelSlug}/${useCaseSlug}` : `/seo/page/${modelSlug}`;
    api.get(url)
      .then((r) => setPage(r))
      .catch((e) => setError(e.message || "Page not found"))
      .finally(() => setLoading(false));
  }, [modelSlug, useCaseSlug]);

  if (loading) {
    return <div className="max-w-4xl mx-auto px-5 sm:px-8 py-20"><Loader label="Loading..." /></div>;
  }

  if (error || !page) {
    return (
      <div className="max-w-3xl mx-auto px-5 sm:px-8 py-20 text-center" data-testid="learn-hub-notfound">
        <h1 className="asc-h1 text-3xl">We haven’t covered this yet</h1>
        <p className="text-[var(--asc-text-dim)] mt-3">This guide is still being written. Browse our published guides or jump into the curriculum.</p>
        <div className="flex justify-center gap-3 mt-6">
          <button onClick={() => nav("/")} className="asc-btn-secondary">Back home</button>
          <button onClick={() => nav("/pricing")} className="asc-btn-primary">See pricing</button>
        </div>
      </div>
    );
  }

  const _origin = typeof window !== "undefined" ? window.location.origin.replace(/\/$/, "") : "";
  const canonical = useCaseSlug
    ? `${_origin}/learn/${modelSlug}/${useCaseSlug}`
    : `${_origin}/learn/${modelSlug}`;

  // JSON-LD structured data
  const faqLd = (page.faqs && page.faqs.length) ? {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    "mainEntity": page.faqs.map((f) => ({
      "@type": "Question",
      "name": f.q,
      "acceptedAnswer": { "@type": "Answer", "text": f.a },
    })),
  } : null;

  const breadcrumbLd = {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    "itemListElement": [
      { "@type": "ListItem", "position": 1, "name": "Home", "item": _origin },
      { "@type": "ListItem", "position": 2, "name": "Learn", "item": `${_origin}/learn` },
      { "@type": "ListItem", "position": 3, "name": page.model_name, "item": `${_origin}/learn/${modelSlug}` },
      ...(useCaseSlug ? [{ "@type": "ListItem", "position": 4, "name": page.use_case_name || useCaseSlug, "item": canonical }] : []),
    ],
  };

  return (
    <div className="min-h-screen" data-testid="learn-hub-page">
      <Helmet>
        <title>{page.meta_title || page.title}</title>
        <meta name="description" content={page.meta_description || page.subtitle} />
        <link rel="canonical" href={canonical} />
        <meta property="og:title" content={page.meta_title || page.title} />
        <meta property="og:description" content={page.meta_description || page.subtitle} />
        <meta property="og:url" content={canonical} />
        <meta property="og:type" content="article" />
        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:title" content={page.meta_title || page.title} />
        <meta name="twitter:description" content={page.meta_description || page.subtitle} />
        {faqLd && <script type="application/ld+json">{JSON.stringify(faqLd)}</script>}
        <script type="application/ld+json">{JSON.stringify(breadcrumbLd)}</script>
      </Helmet>

      {/* Hero */}
      <section className="max-w-4xl mx-auto px-5 sm:px-8 pt-16 pb-10">
        <div className="asc-kicker" data-testid="learn-hub-eyebrow">{page.hero_eyebrow || (useCaseSlug ? "Use-case playbook" : "AI model guide")}</div>
        <h1 className="asc-h1 text-5xl sm:text-6xl mt-2 leading-tight">{page.title}</h1>
        {page.subtitle && <p className="text-xl text-[var(--asc-text-dim)] mt-4 max-w-3xl">{page.subtitle}</p>}
        <div className="flex flex-wrap items-center gap-3 mt-7">
          <Link to="/signup" className="asc-btn-primary text-sm" data-testid="learn-hub-cta-primary">Start learning free <ArrowRight size={14} /></Link>
          <Link to="/pricing" className="asc-btn-secondary text-sm" data-testid="learn-hub-cta-secondary">See pricing</Link>
        </div>
      </section>

      {/* Intro */}
      <section className="max-w-4xl mx-auto px-5 sm:px-8 py-6">
        <p className="text-lg leading-relaxed text-[var(--asc-text-dim)]">{page.intro_md}</p>
      </section>

      {/* TL;DR (hub only) */}
      {page.tldr?.length > 0 && (
        <section className="max-w-4xl mx-auto px-5 sm:px-8 py-6">
          <div className="asc-card p-6">
            <div className="asc-kicker mb-3 flex items-center gap-2"><Sparkles size={14} /> TL;DR</div>
            <ul className="space-y-2">
              {page.tldr.map((t, i) => (
                <li key={i} className="flex items-start gap-2 text-[var(--asc-text-dim)]"><CheckCircle2 size={16} className="text-[var(--asc-brand)] mt-1 shrink-0" /><span>{t}</span></li>
              ))}
            </ul>
          </div>
        </section>
      )}

      {/* Hub-only sections */}
      {page.kind === "hub" && (
        <>
          {page.what_it_is && (
            <Section title="What it is">
              <p className="text-[var(--asc-text-dim)] leading-relaxed">{page.what_it_is}</p>
            </Section>
          )}
          <div className="grid md:grid-cols-2 gap-5 max-w-4xl mx-auto px-5 sm:px-8 py-6">
            {page.what_its_good_at?.length > 0 && (
              <div className="asc-card p-6">
                <div className="asc-kicker mb-2">Strengths</div>
                <ul className="space-y-2">{page.what_its_good_at.map((s, i) => <li key={i} className="flex items-start gap-2 text-sm text-[var(--asc-text-dim)]"><CheckCircle2 size={14} className="text-[var(--asc-success)] mt-1 shrink-0" />{s}</li>)}</ul>
              </div>
            )}
            {page.what_it_struggles_with?.length > 0 && (
              <div className="asc-card p-6">
                <div className="asc-kicker mb-2">Honest weaknesses</div>
                <ul className="space-y-2">{page.what_it_struggles_with.map((s, i) => <li key={i} className="flex items-start gap-2 text-sm text-[var(--asc-text-dim)]"><AlertTriangle size={14} className="text-[var(--asc-warn)] mt-1 shrink-0" />{s}</li>)}</ul>
              </div>
            )}
          </div>
          {page.best_for_personas?.length > 0 && (
            <Section title="Who gets the most value">
              <ul className="space-y-2">{page.best_for_personas.map((p, i) => <li key={i} className="flex items-start gap-2 text-[var(--asc-text-dim)]"><ChevronRight size={16} className="text-[var(--asc-brand)] mt-1" />{p}</li>)}</ul>
            </Section>
          )}
          {page.comparison && (
            <Section title="How it compares"><p className="text-[var(--asc-text-dim)] leading-relaxed">{page.comparison}</p></Section>
          )}
          {page.use_cases?.length > 0 && (
            <Section title="Popular use cases">
              <div className="grid sm:grid-cols-2 gap-2">
                {page.use_cases.map((u, i) => <div key={i} className="asc-card p-4 text-sm text-[var(--asc-text-dim)]">{u}</div>)}
              </div>
            </Section>
          )}
          {page.getting_started && (
            <Section title="Getting started"><p className="text-[var(--asc-text-dim)] leading-relaxed">{page.getting_started}</p></Section>
          )}
        </>
      )}

      {/* Use-case-only sections */}
      {page.kind === "use_case" && (
        <>
          {page.why_this_model && (
            <Section title={`Why ${page.model_name}`}>
              <p className="text-[var(--asc-text-dim)] leading-relaxed">{page.why_this_model}</p>
            </Section>
          )}
          {page.step_by_step?.length > 0 && (
            <Section title="Step-by-step playbook">
              <ol className="space-y-4 counter-reset:step">
                {page.step_by_step.map((step, i) => (
                  <li key={i} className="asc-card p-5 flex gap-4">
                    <div className="shrink-0 w-9 h-9 rounded-full grid place-items-center text-sm font-black" style={{ background: "rgba(255,176,0,0.18)", color: "#FFB000", border: "1px solid rgba(255,176,0,0.5)" }}>{i + 1}</div>
                    <div>
                      <div className="asc-h2 text-lg">{step.title}</div>
                      <p className="text-sm text-[var(--asc-text-dim)] mt-1 leading-relaxed">{step.body}</p>
                    </div>
                  </li>
                ))}
              </ol>
            </Section>
          )}
          {page.prompts?.length > 0 && (
            <Section title="Copy-pastable prompts">
              <div className="space-y-2">
                {page.prompts.map((p, i) => (
                  <pre key={i} className="asc-card p-4 text-sm text-[var(--asc-text-dim)] whitespace-pre-wrap font-mono leading-relaxed">{p}</pre>
                ))}
              </div>
            </Section>
          )}
          {page.pro_tips?.length > 0 && (
            <Section title="Pro tips">
              <ul className="space-y-2">{page.pro_tips.map((t, i) => <li key={i} className="flex items-start gap-2 text-[var(--asc-text-dim)]"><Lightbulb size={16} className="text-[var(--asc-brand)] mt-1" />{t}</li>)}</ul>
            </Section>
          )}
          {page.common_mistakes?.length > 0 && (
            <Section title="Common mistakes">
              <ul className="space-y-2">{page.common_mistakes.map((m, i) => <li key={i} className="flex items-start gap-2 text-[var(--asc-text-dim)]"><AlertTriangle size={16} className="text-[var(--asc-warn)] mt-1" />{m}</li>)}</ul>
            </Section>
          )}
          {page.tools_to_combine?.length > 0 && (
            <Section title="Pair it with">
              <ul className="space-y-2">{page.tools_to_combine.map((t, i) => <li key={i} className="flex items-start gap-2 text-[var(--asc-text-dim)]"><Wrench size={16} className="text-[var(--asc-lavender)] mt-1" />{t}</li>)}</ul>
            </Section>
          )}
        </>
      )}

      {/* FAQs */}
      {page.faqs?.length > 0 && (
        <Section title="FAQs">
          <div className="space-y-3">
            {page.faqs.map((f, i) => (
              <details key={i} className="asc-card p-5 group" data-testid={`learn-hub-faq-${i}`}>
                <summary className="cursor-pointer flex items-start justify-between gap-3 list-none">
                  <div className="flex items-start gap-2">
                    <HelpCircle size={16} className="text-[var(--asc-brand)] mt-1 shrink-0" />
                    <span className="font-bold">{f.q}</span>
                  </div>
                  <ChevronRight size={16} className="text-[var(--asc-text-muted)] transition group-open:rotate-90 shrink-0 mt-1" />
                </summary>
                <p className="text-sm text-[var(--asc-text-dim)] mt-3 leading-relaxed">{f.a}</p>
              </details>
            ))}
          </div>
        </Section>
      )}

      {/* Final CTA */}
      <section className="max-w-4xl mx-auto px-5 sm:px-8 py-12">
        <div className="asc-card p-10 text-center" style={{ background: "linear-gradient(135deg, rgba(255,176,0,0.08), rgba(124,58,237,0.10))", border: "1px solid rgba(255,176,0,0.35)" }}>
          <h2 className="asc-h2 text-3xl">{page.cta_headline || "Ready to actually master this?"}</h2>
          <p className="text-[var(--asc-text-dim)] mt-3 max-w-xl mx-auto">{page.cta_body || "Ascendra Academy walks you through every AI model with interactive lessons, quizzes, and a personal AI tutor."}</p>
          <div className="flex justify-center gap-3 mt-6">
            <Link to="/signup" className="asc-btn-primary" data-testid="learn-hub-cta-final">Start free <ArrowRight size={14} /></Link>
            <Link to="/pricing" className="asc-btn-secondary">See pricing</Link>
          </div>
        </div>
      </section>
    </div>
  );
}

function Section({ title, children }) {
  return (
    <section className="max-w-4xl mx-auto px-5 sm:px-8 py-6">
      <h2 className="asc-h2 text-2xl mb-4">{title}</h2>
      {children}
    </section>
  );
}
