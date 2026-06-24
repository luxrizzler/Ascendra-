import { Link, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import { Sparkles, ArrowRight, Rocket, TrendingUp, Compass, Users, CheckCircle2, Infinity as InfinityIcon, Sun } from "lucide-react";
import { api } from "@/lib/api";

const HERO_IMG = "https://customer-assets.emergentagent.com/job_ai-business-academy-2/artifacts/c1jkvwwp_4185C05A-6A9A-42F7-A146-9109CF6F03DD.png";

const PILLARS = [
  { icon: Sparkles, title: "AI-Personalized", body: "Learning paths tailored to your goals, pace, and style." },
  { icon: Rocket, title: "Real-World Skills", body: "Practical knowledge for real impact. Not theory." },
  { icon: TrendingUp, title: "Track & Grow", body: "See your progress. Celebrate your wins. Build the streak." },
  { icon: Users, title: "Expert Guidance", body: "Learn from industry leaders and your AI tutor, 24/7." },
];

const SYMBOLISM = [
  { icon: TrendingUp, title: "Rise", body: "Ascending to your highest potential." },
  { icon: Sun, title: "Light", body: "Knowledge that illuminates." },
  { icon: InfinityIcon, title: "Transformation", body: "Continuous growth and becoming." },
  { icon: Compass, title: "Guidance", body: "AI-powered guidance every step." },
];

const MODELS = ["GPT-5.2", "Claude 4.5", "Gemini 3", "Nano Banana", "Sora 2", "ElevenLabs", "Perplexity", "Midjourney", "Veo 3", "Whisper", "Cursor", "Suno"];

export default function Landing() {
  const nav = useNavigate();
  const [tiers, setTiers] = useState([]);

  useEffect(() => {
    api.get("/pricing").then((r) => setTiers(r.tiers)).catch(() => {});
  }, []);

  return (
    <div data-testid="landing-page">
      {/* HERO */}
      <section className="relative overflow-hidden">
        <div className="max-w-7xl mx-auto px-6 py-12 lg:py-20 grid lg:grid-cols-2 gap-10 items-center">
          {/* Left — brand image */}
          <div className="relative aspect-[4/5] sm:aspect-[5/4] lg:aspect-auto lg:h-[640px] rounded-3xl overflow-hidden order-2 lg:order-1" style={{ background: "#0A0413" }}>
            <img src={HERO_IMG} alt="Ascendra brand" className="absolute inset-0 w-full h-full object-cover" />
            <div className="absolute inset-0 pointer-events-none" style={{ background: "linear-gradient(120deg, rgba(10,4,19,0) 50%, rgba(10,4,19,0.85) 100%)" }} />
          </div>

          {/* Right — copy */}
          <div className="order-1 lg:order-2">
            <div className="asc-kicker">AI-Powered Learning · Boundless Growth</div>
            <h1 className="asc-h1 text-5xl sm:text-6xl lg:text-7xl mt-6">
              Ready to <span className="asc-gradient-text italic">rise today?</span>
            </h1>
            <p className="text-[var(--asc-text-dim)] text-lg mt-6 max-w-xl leading-relaxed">
              The AI learning partner that walks beside you — from your first prompt to your first launch.
              Beginner to advanced, taught through every model that matters in 2026.
            </p>
            <div className="flex flex-wrap gap-3 mt-8">
              <button onClick={() => nav("/signup")} className="asc-btn-primary text-base" data-testid="hero-cta-btn">
                Begin your ascent <ArrowRight size={18} />
              </button>
              <button onClick={() => nav("/pricing")} className="asc-btn-secondary text-base" data-testid="hero-pricing-btn">See pricing</button>
            </div>
            <div className="mt-8 flex items-center gap-4 text-xs text-[var(--asc-text-muted)]">
              <div className="flex items-center gap-1.5"><CheckCircle2 size={14} className="text-[var(--asc-success)]" /> Free to start</div>
              <div className="flex items-center gap-1.5"><CheckCircle2 size={14} className="text-[var(--asc-success)]" /> No card required</div>
              <div className="flex items-center gap-1.5"><CheckCircle2 size={14} className="text-[var(--asc-success)]" /> Cancel anytime</div>
            </div>
          </div>
        </div>
      </section>

      {/* MISSION */}
      <section className="px-6 py-16">
        <div className="max-w-4xl mx-auto relative overflow-hidden rounded-3xl border border-[var(--asc-border-strong)] p-10 sm:p-14"
          style={{ background: "linear-gradient(135deg, rgba(124,58,237,0.18), rgba(255,176,0,0.06))" }}>
          <div className="asc-kicker">Our Mission</div>
          <p className="asc-h2 text-2xl sm:text-4xl mt-5">
            To <span className="text-[var(--asc-brand)]">empower</span> every learner to{' '}
            <span className="text-[var(--asc-brand)] italic">rise beyond limits</span>{' '}
            through AI-driven education and human potential.
          </p>
        </div>
      </section>

      {/* MODELS MARQUEE */}
      <section className="border-y border-[var(--asc-border)] py-10" style={{ background: "#1A1F3D" }}>
        <div className="asc-label text-center mb-5">Covering the models that matter</div>
        <div className="overflow-hidden">
          <div className="marquee-track flex gap-3 w-max">
            {[...MODELS, ...MODELS].map((m, i) => (
              <span key={i} className="px-4 py-2 rounded-full border border-[var(--asc-border-strong)] text-sm text-[var(--asc-text-dim)] font-bold" style={{ background: "#0A0413" }}>{m}</span>
            ))}
          </div>
        </div>
      </section>

      {/* PILLARS */}
      <Section kicker="Built for your rise" title="Everything you need to ascend.">
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5">
          {PILLARS.map(({ icon: Icon, title, body }) => (
            <div key={title} className="asc-card p-6">
              <div className="w-12 h-12 rounded-xl grid place-items-center mb-4" style={{ background: "rgba(255,176,0,0.12)", border: "1px solid rgba(255,176,0,0.35)" }}>
                <Icon size={22} color="#FFB000" />
              </div>
              <div className="asc-kicker mb-1">{title}</div>
              <p className="text-[var(--asc-text-dim)] text-sm leading-relaxed">{body}</p>
            </div>
          ))}
        </div>
      </Section>

      {/* SYMBOLISM */}
      <Section kicker="The name means" title="Rise. Light. Transformation. Guidance.">
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5">
          {SYMBOLISM.map(({ icon: Icon, title, body }) => (
            <div key={title} className="asc-card p-6">
              <div className="w-12 h-12 rounded-full grid place-items-center mb-4" style={{ background: "rgba(124,58,237,0.15)", border: "1px solid rgba(191,180,255,0.35)" }}>
                <Icon size={24} color="#FFB000" />
              </div>
              <h3 className="asc-h2 text-lg mb-1">{title}</h3>
              <p className="text-[var(--asc-text-dim)] text-sm leading-relaxed">{body}</p>
            </div>
          ))}
        </div>
      </Section>

      {/* PRICING TEASER */}
      <Section kicker="Pricing" title="Start free. Rise on your terms.">
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {tiers.map((t) => (
            <div key={t.id} data-testid={`landing-tier-${t.id}`} className={`asc-card p-7 relative ${t.highlight ? "border-[var(--asc-brand)]" : ""}`}
              style={t.highlight ? { borderColor: "#FFB000", background: "rgba(255,176,0,0.04)" } : {}}>
              {t.highlight && (
                <div className="absolute -top-2.5 left-6 px-2.5 py-1 rounded-full text-[10px] font-black tracking-wider" style={{ background: "#FFB000", color: "#000" }}>MOST POPULAR</div>
              )}
              <div className="asc-h2 text-2xl">{t.name}</div>
              <div className="flex items-end gap-1 mt-2">
                <span className="text-4xl font-black">${t.price_monthly}</span>
                <span className="text-[var(--asc-text-dim)] text-sm pb-2">/mo</span>
              </div>
              <p className="text-[var(--asc-text-dim)] text-sm mt-2">{t.blurb}</p>
              <ul className="mt-5 space-y-2">
                {t.features.slice(0, 5).map((f, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-[var(--asc-text-dim)]">
                    <CheckCircle2 size={16} className={t.highlight ? "text-[var(--asc-brand)] mt-0.5" : "text-[var(--asc-lavender)] mt-0.5"} /> {f}
                  </li>
                ))}
              </ul>
              <button onClick={() => nav("/signup")} data-testid={`landing-cta-${t.id}`} className={`w-full mt-6 py-3 rounded-xl font-bold ${t.highlight ? "" : "border"}`} style={t.highlight ? { background: "#FFB000", color: "#000" } : { background: "#1F183A", color: "#fff", borderColor: "rgba(191,180,255,0.28)" }}>
                Choose {t.name}
              </button>
            </div>
          ))}
        </div>
        <div className="text-center mt-6 text-sm text-[var(--asc-text-muted)]">
          <Link to="/pricing" className="text-[var(--asc-brand)] hover:underline">See all features & annual pricing →</Link>
        </div>
      </Section>

      {/* FINAL CTA */}
      <section className="relative px-6 py-20 mx-6 my-16 rounded-3xl overflow-hidden border border-[var(--asc-border-strong)]" style={{ background: "linear-gradient(135deg, rgba(124,58,237,0.18), rgba(255,176,0,0.06))" }}>
        <div className="max-w-3xl mx-auto text-center">
          <div className="asc-kicker">Your ascent begins now</div>
          <div className="mt-4 flex flex-wrap justify-center items-center gap-3 sm:gap-5">
            {["LEARN.", "GROW.", "TRANSFORM."].map((w) => (
              <span key={w} className="text-2xl sm:text-3xl font-black tracking-wider">{w}</span>
            ))}
            <span className="text-2xl sm:text-3xl font-black tracking-wider asc-gradient-text italic">ASCEND.</span>
          </div>
          <p className="text-[var(--asc-text-dim)] mt-5">Free to start. No card required.</p>
          <button onClick={() => nav("/signup")} data-testid="final-cta-btn" className="asc-btn-primary mt-6 text-base">Begin your ascent <ArrowRight size={18} /></button>
        </div>
      </section>
    </div>
  );
}

function Section({ kicker, title, children }) {
  return (
    <section className="px-6 py-16 lg:py-24">
      <div className="max-w-7xl mx-auto">
        <div className="asc-kicker">{kicker}</div>
        <h2 className="asc-h2 text-3xl sm:text-5xl mt-3 mb-10 max-w-3xl">{title}</h2>
        {children}
      </div>
    </section>
  );
}
