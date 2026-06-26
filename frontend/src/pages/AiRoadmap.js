import { Link } from "react-router-dom";
import { Helmet } from "react-helmet-async";
import { Sparkles, ArrowRight, Compass, BookOpen, Rocket, Target, Trophy } from "lucide-react";

const PHASES = [
  { icon: Compass, title: "Phase 1 — Foundation", body: "Learn how modern AI actually thinks. What's a model, what's a prompt, how 'tokens' work. Skip the buzzwords. 3 hours total." },
  { icon: BookOpen, title: "Phase 2 — Prompt Fluency", body: "Master the Role → Context → Task → Constraints → Output structure that 10x's your results. Memorize 8 patterns and you're 90% of the way there." },
  { icon: Rocket, title: "Phase 3 — Tool Stack", body: "Pick your stack: GPT-5.2 for chat, Claude for nuance, Gemini for research, Nano Banana for images. Knowing what to use when is the meta-skill." },
  { icon: Target, title: "Phase 4 — Apply Daily", body: "Build the habit. Use AI for 1 real task a day — email triage, meeting notes, code review, content draft. Skill comes from reps." },
  { icon: Trophy, title: "Phase 5 — Compound", body: "Stack workflows. The same patterns that wrote your email can run your marketing, your support inbox, your research. This is where AI stops being a tool and starts being leverage." },
];

const STUCK_POINTS = [
  "Watching 100 YouTube videos and still not using AI for real work",
  "Getting good prompts on Day 1, then forgetting them by Day 7",
  "Switching tools every week because each new one feels 'better'",
  "Confusing 'AI knowledge' with 'AI skill' (you learn skill by shipping)",
];

export default function AiRoadmap() {
  return (
    <div className="max-w-3xl mx-auto px-5 sm:px-8 py-16" data-testid="ai-roadmap-page">
      <Helmet>
        <title>The AI Roadmap — From Curious to Capable in 5 Phases | Ascendra</title>
        <meta name="description" content="The exact 5-phase path Ascendra Academy walks every learner through. Skip the YouTube graveyard. Free resource." />
        <link rel="canonical" href="https://repo-to-site-2.preview.emergentagent.com/resources/ai-roadmap" />
      </Helmet>

      <div className="asc-kicker">FREE RESOURCE</div>
      <h1 className="asc-h1 text-5xl mt-2">The AI Roadmap</h1>
      <p className="text-xl text-[var(--asc-text-dim)] mt-3">From curious to capable in 5 phases. The exact path we walk every Ascendra learner through.</p>

      <div className="asc-card p-6 mt-8">
        <div className="asc-kicker mb-2 flex items-center gap-2"><Sparkles size={14} /> Why most people get stuck</div>
        <ul className="space-y-2 text-[var(--asc-text-dim)] text-sm">
          {STUCK_POINTS.map((s, i) => <li key={i} className="flex items-start gap-2"><span className="text-[var(--asc-warn)] mt-1">•</span>{s}</li>)}
        </ul>
      </div>

      <div className="space-y-4 mt-10">
        {PHASES.map(({ icon: Icon, title, body }, i) => (
          <div key={i} className="asc-card p-6 flex items-start gap-4">
            <div className="shrink-0 w-12 h-12 rounded-2xl grid place-items-center" style={{ background: "rgba(255,176,0,0.15)", border: "1px solid rgba(255,176,0,0.4)" }}>
              <Icon size={20} color="#FFB000" />
            </div>
            <div>
              <h3 className="asc-h2 text-xl">{title}</h3>
              <p className="text-[var(--asc-text-dim)] text-sm mt-2 leading-relaxed">{body}</p>
            </div>
          </div>
        ))}
      </div>

      <div className="asc-card p-8 mt-10 text-center" style={{ background: "linear-gradient(135deg, rgba(255,176,0,0.08), rgba(124,58,237,0.10))", border: "1px solid rgba(255,176,0,0.35)" }}>
        <h2 className="asc-h2 text-2xl">Want guidance through every phase?</h2>
        <p className="text-[var(--asc-text-dim)] mt-2 max-w-xl mx-auto">Ascendra Academy is your guide. Interactive lessons, quizzes, an AI tutor, and a real path you can actually finish.</p>
        <Link to="/signup" className="asc-btn-primary mt-5" data-testid="roadmap-cta-signup">Start free <ArrowRight size={14} /></Link>
      </div>
    </div>
  );
}
