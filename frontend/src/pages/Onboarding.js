import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowLeft, ArrowRight, Briefcase, BookOpen, Clock, Gauge, Headphones, Lightbulb, Mic, MousePointerClick, Palette, Rocket, Settings2, Sparkles, Target, TrendingUp, Wand2, Wrench } from "lucide-react";
import { api } from "@/lib/api";
import { toast } from "sonner";

const STEPS = [
  {
    key: "motivation",
    title: "What brings you to Ascendra?",
    sub: "Pick the one that feels most true.",
    type: "single",
    options: [
      { value: "career", label: "Level up my career", icon: TrendingUp },
      { value: "side_hustle", label: "Start a side hustle", icon: Rocket },
      { value: "productivity", label: "Get more done in less time", icon: Gauge },
      { value: "business", label: "Automate my business", icon: Settings2 },
      { value: "creator", label: "Become an AI creator", icon: Palette },
      { value: "curiosity", label: "Just curious about AI", icon: Lightbulb },
    ],
  },
  {
    key: "experience",
    title: "How experienced are you with AI?",
    sub: "Be honest — we calibrate to where you are.",
    type: "single",
    options: [
      { value: "never", label: "I've never used AI", icon: Sparkles },
      { value: "beginner", label: "I've tried ChatGPT a few times", icon: BookOpen },
      { value: "some", label: "I use AI weekly", icon: Wand2 },
      { value: "intermediate", label: "I use AI daily", icon: Briefcase },
      { value: "expert", label: "I build with AI", icon: Wrench },
    ],
  },
  {
    key: "tools_used",
    title: "Which AI tools have you tried?",
    sub: "Multi-select. Or skip if none.",
    type: "multi",
    options: [
      { value: "chatgpt", label: "ChatGPT" },
      { value: "claude", label: "Claude" },
      { value: "gemini", label: "Gemini" },
      { value: "perplexity", label: "Perplexity" },
      { value: "midjourney", label: "Midjourney" },
      { value: "nano_banana", label: "Nano Banana" },
      { value: "none", label: "None yet" },
    ],
  },
  {
    key: "goals",
    title: "What do you want to achieve in the next 30 days?",
    sub: "Multi-select.",
    type: "multi",
    options: [
      { value: "fundamentals", label: "Learn the fundamentals", icon: BookOpen },
      { value: "build_project", label: "Build my first AI project", icon: Wrench },
      { value: "automate", label: "Automate boring tasks", icon: Settings2 },
      { value: "create_content", label: "Create content with AI", icon: Palette },
      { value: "promotion", label: "Get promoted / better job", icon: TrendingUp },
    ],
  },
  {
    key: "time_per_day",
    title: "How much time can you give us per day?",
    sub: "We'll set your daily goal based on this.",
    type: "single",
    options: [
      { value: "5", label: "5 minutes", icon: Clock },
      { value: "15", label: "15 minutes", icon: Clock },
      { value: "30", label: "30 minutes", icon: Clock },
      { value: "60", label: "1 hour or more", icon: Clock },
    ],
  },
  {
    key: "learning_style",
    title: "How do you learn best?",
    sub: "Affects the cards we surface first.",
    type: "single",
    options: [
      { value: "reading", label: "Reading", icon: BookOpen },
      { value: "audio", label: "Listening (audio cards)", icon: Headphones },
      { value: "hands_on", label: "Hands-on (playground)", icon: MousePointerClick },
      { value: "all", label: "Mix it up", icon: Mic },
    ],
  },
];

export default function OnboardingQuiz() {
  const nav = useNavigate();
  const [step, setStep] = useState(0);
  const [answers, setAnswers] = useState({ tools_used: [], goals: [] });
  const [loading, setLoading] = useState(false);
  const [plan, setPlan] = useState(null);

  // If already onboarded, fast-forward to plan view
  useEffect(() => {
    api.get("/onboarding/me").then((r) => {
      if (r.onboarded) {
        setAnswers(r.answers || {});
        setPlan(r.plan);
        setStep(STEPS.length); // jump to result view
      }
    }).catch(() => {});
  }, []);

  const cur = STEPS[step];
  const canNext = useMemo(() => {
    if (!cur) return true;
    const v = answers[cur.key];
    if (cur.type === "single") return !!v;
    if (cur.type === "multi") return Array.isArray(v) && v.length > 0;
    return true;
  }, [cur, answers]);

  const pick = (value) => {
    if (cur.type === "single") {
      setAnswers((a) => ({ ...a, [cur.key]: value }));
    } else {
      setAnswers((a) => {
        const cur_set = new Set(a[cur.key] || []);
        if (cur_set.has(value)) cur_set.delete(value); else cur_set.add(value);
        return { ...a, [cur.key]: Array.from(cur_set) };
      });
    }
  };

  const back = () => setStep((s) => Math.max(0, s - 1));
  const next = async () => {
    if (step < STEPS.length - 1) { setStep((s) => s + 1); return; }
    // Submit
    setLoading(true);
    try {
      const body = {
        motivation: answers.motivation,
        experience: answers.experience,
        tools_used: answers.tools_used || [],
        goals: answers.goals || [],
        time_per_day: answers.time_per_day,
        learning_style: answers.learning_style,
      };
      const r = await api.post("/onboarding/submit", body);
      setPlan(r.plan);
      setStep(STEPS.length);
    } catch (e) {
      toast.error(e.message || "Could not save quiz. Try again.");
    } finally {
      setLoading(false);
    }
  };

  // RESULT VIEW
  if (step >= STEPS.length) {
    return (
      <div className="min-h-screen" style={{ background: "#0A0413" }}>
        <div className="max-w-2xl mx-auto px-6 py-12">
          <div className="asc-card p-8 sm:p-10 text-center" data-testid="onboarding-result">
            <motion.div initial={{ scale: 0 }} animate={{ scale: [0, 1.2, 1] }} transition={{ duration: 0.5 }}
              className="w-20 h-20 rounded-full mx-auto grid place-items-center mb-4"
              style={{ background: "radial-gradient(circle, rgba(255,176,0,0.45), rgba(255,176,0,0.08))" }}
            ><Sparkles size={40} color="#FFB000" /></motion.div>
            <div className="text-xs tracking-widest font-black text-[#FFB000] mb-2">YOUR PERSONALIZED PLAN</div>
            <h1 className="asc-h2 text-3xl sm:text-4xl">{plan?.headline || "Welcome to Ascendra"}</h1>
            <p className="text-[var(--asc-text-dim)] mt-4 leading-relaxed">{plan?.rationale || "We picked the best paths for you."}</p>
            <div className="mt-6 p-4 rounded-xl flex items-center justify-between" style={{ background: "rgba(255,176,0,0.06)", border: "1px solid rgba(255,176,0,0.25)" }}>
              <div className="flex items-center gap-2"><Target size={14} color="#FFB000" /><span className="text-sm font-bold">Daily goal</span></div>
              <span className="text-sm font-black text-[#FFB000]">{plan?.daily_goal_target || 1} lesson{(plan?.daily_goal_target || 1) > 1 ? "s" : ""} / day</span>
            </div>
            <div className="flex gap-3 mt-6 justify-center flex-wrap">
              {plan?.first_lesson_id && (
                <button onClick={() => nav(`/lessons/${plan.first_lesson_id}`)} data-testid="onboarding-start-lesson-btn" className="asc-btn-primary">
                  Start lesson 1 <ArrowRight size={14} />
                </button>
              )}
              <button onClick={() => nav("/paths")} data-testid="onboarding-paths-btn" className="asc-btn-secondary">View all paths</button>
              <button onClick={() => nav("/dashboard")} className="asc-btn-secondary">Go to dashboard</button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen" style={{ background: "#0A0413" }}>
      {/* progress dots */}
      <div className="max-w-2xl mx-auto px-6 pt-8">
        <div className="flex items-center justify-center gap-1.5" data-testid="onboarding-progress">
          {STEPS.map((_, i) => (
            <div key={i} className="h-1.5 rounded-full transition-all" style={{
              width: i === step ? 28 : 18,
              background: i <= step ? "#FFB000" : "rgba(191,180,255,0.18)",
            }} />
          ))}
        </div>
        <div className="text-center text-xs text-[var(--asc-text-muted)] mt-2">Step {step + 1} of {STEPS.length}</div>
      </div>

      <div className="max-w-2xl mx-auto px-6 py-8">
        <AnimatePresence mode="wait">
          <motion.div key={`step-${step}`} initial={{ opacity: 0, x: 40 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -40 }} transition={{ duration: 0.22 }}>
            <h1 className="asc-h2 text-3xl sm:text-4xl text-center" data-testid="onboarding-question">{cur.title}</h1>
            <p className="text-[var(--asc-text-muted)] text-center mt-2">{cur.sub}</p>
            <div className="grid sm:grid-cols-2 gap-3 mt-8">
              {cur.options.map((o) => {
                const Icon = o.icon;
                const selected = cur.type === "single"
                  ? answers[cur.key] === o.value
                  : Array.isArray(answers[cur.key]) && answers[cur.key].includes(o.value);
                return (
                  <button
                    key={o.value}
                    type="button"
                    onClick={() => pick(o.value)}
                    data-testid={`onboarding-opt-${o.value}`}
                    className="asc-card p-4 sm:p-5 text-left transition-all hover:scale-[1.01]"
                    style={{
                      background: selected ? "rgba(255,176,0,0.08)" : undefined,
                      borderColor: selected ? "#FFB000" : undefined,
                    }}
                  >
                    <div className="flex items-center gap-3">
                      {Icon && (
                        <div className="w-9 h-9 rounded-full grid place-items-center shrink-0" style={{ background: selected ? "rgba(255,176,0,0.2)" : "rgba(191,180,255,0.06)" }}>
                          <Icon size={18} color={selected ? "#FFB000" : "#BFB4FF"} />
                        </div>
                      )}
                      <span className="font-bold text-base">{o.label}</span>
                    </div>
                  </button>
                );
              })}
            </div>
          </motion.div>
        </AnimatePresence>

        <div className="flex items-center justify-between mt-8">
          <button onClick={back} disabled={step === 0} data-testid="onboarding-back-btn" className={`asc-btn-secondary text-sm ${step === 0 ? "opacity-40 cursor-not-allowed" : ""}`}>
            <ArrowLeft size={14} /> Back
          </button>
          <button onClick={next} disabled={!canNext || loading} data-testid="onboarding-next-btn" className="asc-btn-primary disabled:opacity-50">
            {loading ? "Building your plan…" : (step === STEPS.length - 1 ? "Show my plan" : "Next")}
            {!loading && <ArrowRight size={14} />}
          </button>
        </div>
      </div>
    </div>
  );
}
