import { useEffect, useMemo, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useNavigate } from "react-router-dom";
import {
  ArrowLeft, ArrowRight, Briefcase, BookOpen, Clock, Gauge, Headphones,
  Lightbulb, Mic, MousePointerClick, Palette, Rocket, Settings2, Sparkles,
  Target, TrendingUp, Wand2, Wrench, Mail, X,
} from "lucide-react";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";

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
    title: "What do you want to achieve in 30 days?",
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
      { value: "5",  label: "5 minutes",       icon: Clock },
      { value: "15", label: "15 minutes",      icon: Clock },
      { value: "30", label: "30 minutes",      icon: Clock },
      { value: "60", label: "1 hour or more",  icon: Clock },
    ],
  },
  {
    key: "learning_style",
    title: "How do you learn best?",
    sub: "Affects the cards we surface first.",
    type: "single",
    options: [
      { value: "reading",   label: "Reading",                 icon: BookOpen },
      { value: "audio",     label: "Listening (audio cards)", icon: Headphones },
      { value: "hands_on",  label: "Hands-on (playground)",   icon: MousePointerClick },
      { value: "all",       label: "Mix it up",               icon: Mic },
    ],
  },
];

/**
 * OnboardingModal — modal version of the onboarding quiz.
 *
 * Two modes:
 *   - anonymous=true  → public lead-gen. After last step, ask for email,
 *                       call /api/onboarding/anonymous, show plan + CTA to signup.
 *   - anonymous=false → authenticated user. Calls /api/onboarding/submit,
 *                       shows plan + CTAs to start lesson / paths / dashboard.
 *
 * Props:
 *   - open        : controlled visibility (bool)
 *   - onOpenChange: callback
 *   - anonymous   : (bool)
 *   - source      : optional tag (e.g. "landing_popup")
 *   - onComplete  : callback fired after successful submit (passes the plan)
 */
export default function OnboardingModal({
  open, onOpenChange,
  anonymous = false, source = "modal",
  onComplete,
}) {
  const nav = useNavigate();
  const [step, setStep] = useState(0);
  const [answers, setAnswers] = useState({ tools_used: [], goals: [] });
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [plan, setPlan] = useState(null);
  const [alreadyRegistered, setAlreadyRegistered] = useState(false);

  // Anonymous flow has an extra email step before the result.
  const TOTAL_STEPS = STEPS.length + (anonymous ? 1 : 0);
  const isEmailStep = anonymous && step === STEPS.length;
  const isResultStep = step >= TOTAL_STEPS;
  const cur = step < STEPS.length ? STEPS[step] : null;

  // Reset on close
  useEffect(() => {
    if (!open) {
      // Reset after fade-out
      setTimeout(() => {
        setStep(0);
        setAnswers({ tools_used: [], goals: [] });
        setEmail("");
        setPlan(null);
        setAlreadyRegistered(false);
      }, 250);
    }
  }, [open]);

  const canNext = useMemo(() => {
    if (isEmailStep) {
      // Basic email pattern
      return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim());
    }
    if (!cur) return true;
    const v = answers[cur.key];
    if (cur.type === "single") return !!v;
    if (cur.type === "multi") return Array.isArray(v) && v.length > 0;
    return true;
  }, [cur, answers, isEmailStep, email]);

  const pick = (value) => {
    if (!cur) return;
    if (cur.type === "single") {
      setAnswers((a) => ({ ...a, [cur.key]: value }));
    } else {
      setAnswers((a) => {
        const s = new Set(a[cur.key] || []);
        if (s.has(value)) s.delete(value); else s.add(value);
        return { ...a, [cur.key]: Array.from(s) };
      });
    }
  };

  const back = () => setStep((s) => Math.max(0, s - 1));

  const next = async () => {
    if (step < STEPS.length - 1) { setStep((s) => s + 1); return; }
    if (anonymous && !isEmailStep) { setStep(STEPS.length); return; }
    // Submit
    setLoading(true);
    try {
      const payload = {
        motivation: answers.motivation,
        experience: answers.experience,
        tools_used: answers.tools_used || [],
        goals: answers.goals || [],
        time_per_day: answers.time_per_day,
        learning_style: answers.learning_style,
      };
      if (anonymous) {
        payload.email = email.trim();
        payload.source = source;
        const r = await api.post("/onboarding/anonymous", payload);
        if (r.already_registered) {
          setAlreadyRegistered(true);
          toast.info(r.message || "You already have an account. Sign in to view your plan.");
        }
        setPlan(r.plan || null);
      } else {
        const r = await api.post("/onboarding/submit", payload);
        setPlan(r.plan || null);
      }
      setStep(TOTAL_STEPS); // result
      if (onComplete) onComplete(plan);
    } catch (e) {
      toast.error(e.message || "Could not save quiz. Try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className="max-w-2xl p-0 overflow-hidden"
        data-testid="onboarding-modal"
        style={{ background: "#15102B" }}
      >
        {/* Progress bar */}
        {!isResultStep && (
          <div className="px-6 pt-6">
            <div className="flex items-center justify-center gap-1.5" data-testid="onboarding-progress">
              {Array.from({ length: TOTAL_STEPS }).map((_, i) => (
                <div key={i} className="h-1.5 rounded-full transition-all" style={{
                  width: i === step ? 28 : 18,
                  background: i <= step ? "#FFB000" : "rgba(191,180,255,0.18)",
                }} />
              ))}
            </div>
            <div className="text-center text-xs text-[var(--asc-text-muted)] mt-2">
              Step {Math.min(step + 1, TOTAL_STEPS)} of {TOTAL_STEPS}
            </div>
          </div>
        )}

        <div className="px-6 py-6 max-h-[80vh] overflow-y-auto">
          <AnimatePresence mode="wait">
            {isResultStep ? (
              <ResultView
                key="result"
                plan={plan}
                anonymous={anonymous}
                alreadyRegistered={alreadyRegistered}
                email={email}
                onClose={() => onOpenChange(false)}
                nav={nav}
              />
            ) : isEmailStep ? (
              <EmailStep key="email-step" email={email} setEmail={setEmail} />
            ) : (
              <motion.div
                key={`step-${step}`}
                initial={{ opacity: 0, x: 32 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -32 }}
                transition={{ duration: 0.2 }}
              >
                <h2 className="asc-h2 text-2xl sm:text-3xl text-center" data-testid="onboarding-question">
                  {cur.title}
                </h2>
                <p className="text-[var(--asc-text-muted)] text-center text-sm mt-2">{cur.sub}</p>
                <div className="grid sm:grid-cols-2 gap-3 mt-6">
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
                        className="asc-card p-4 text-left transition-all hover:scale-[1.01]"
                        style={{
                          background: selected ? "rgba(255,176,0,0.10)" : undefined,
                          borderColor: selected ? "#FFB000" : undefined,
                        }}
                      >
                        <div className="flex items-center gap-3">
                          {Icon && (
                            <div className="w-9 h-9 rounded-full grid place-items-center shrink-0" style={{ background: selected ? "rgba(255,176,0,0.22)" : "rgba(191,180,255,0.06)" }}>
                              <Icon size={16} color={selected ? "#FFB000" : "#BFB4FF"} />
                            </div>
                          )}
                          <span className="font-bold text-sm sm:text-base">{o.label}</span>
                        </div>
                      </button>
                    );
                  })}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Footer / nav buttons */}
        {!isResultStep && (
          <div className="flex items-center justify-between px-6 pb-6 pt-2 border-t" style={{ borderColor: "rgba(191,180,255,0.1)" }}>
            <button
              onClick={back}
              disabled={step === 0}
              data-testid="onboarding-back-btn"
              className={`asc-btn-secondary text-sm ${step === 0 ? "opacity-40 cursor-not-allowed" : ""}`}
            >
              <ArrowLeft size={14} /> Back
            </button>
            <button
              onClick={next}
              disabled={!canNext || loading}
              data-testid="onboarding-next-btn"
              className="asc-btn-primary disabled:opacity-50"
            >
              {loading
                ? "Building your plan…"
                : (isEmailStep
                    ? "Show my plan"
                    : (step === STEPS.length - 1 && !anonymous
                        ? "Show my plan"
                        : "Next"))}
              {!loading && <ArrowRight size={14} />}
            </button>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}


function EmailStep({ email, setEmail }) {
  return (
    <motion.div
      key="email-step"
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -12 }}
      transition={{ duration: 0.22 }}
      className="text-center"
      data-testid="onboarding-email-step"
    >
      <div className="w-14 h-14 rounded-full grid place-items-center mx-auto mb-4"
            style={{ background: "rgba(255,176,0,0.18)" }}>
        <Mail size={24} color="#FFB000" />
      </div>
      <h2 className="asc-h2 text-2xl sm:text-3xl">Where should we send your plan?</h2>
      <p className="text-[var(--asc-text-muted)] text-sm mt-2 max-w-md mx-auto">
        We&apos;ll email your personalized AI learning plan so you can come back to it anytime.
        No spam — we&apos;ll only send the plan and the occasional tip.
      </p>
      <div className="mt-6 max-w-md mx-auto">
        <Input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="you@email.com"
          className="asc-input text-center"
          autoFocus
          data-testid="onboarding-email-input"
        />
      </div>
    </motion.div>
  );
}


function ResultView({ plan, anonymous, alreadyRegistered, email, onClose, nav }) {
  return (
    <motion.div
      key="result"
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      transition={{ duration: 0.25 }}
      className="text-center"
      data-testid="onboarding-result"
    >
      <motion.div
        initial={{ scale: 0 }}
        animate={{ scale: [0, 1.2, 1] }}
        transition={{ duration: 0.45 }}
        className="w-20 h-20 rounded-full mx-auto grid place-items-center mb-4"
        style={{ background: "radial-gradient(circle, rgba(255,176,0,0.45), rgba(255,176,0,0.08))" }}
      >
        <Sparkles size={36} color="#FFB000" />
      </motion.div>
      <div className="text-xs tracking-widest font-black text-[#FFB000] mb-2">YOUR PERSONALIZED PLAN</div>
      <h2 className="asc-h2 text-2xl sm:text-3xl">{plan?.headline || "Welcome to Ascendra"}</h2>
      <p className="text-[var(--asc-text-dim)] text-sm sm:text-base mt-3 leading-relaxed max-w-lg mx-auto">
        {plan?.rationale || "We picked the best paths to get you climbing immediately."}
      </p>

      <div className="mt-6 p-4 rounded-xl flex items-center justify-between max-w-md mx-auto"
            style={{ background: "rgba(255,176,0,0.06)", border: "1px solid rgba(255,176,0,0.25)" }}>
        <div className="flex items-center gap-2">
          <Target size={14} color="#FFB000" />
          <span className="text-sm font-bold">Daily goal</span>
        </div>
        <span className="text-sm font-black text-[#FFB000]">
          {plan?.daily_goal_target || 1} lesson{(plan?.daily_goal_target || 1) > 1 ? "s" : ""} / day
        </span>
      </div>

      <div className="flex gap-3 mt-7 justify-center flex-wrap">
        {anonymous ? (
          alreadyRegistered ? (
            <>
              <button
                onClick={() => nav("/login")}
                className="asc-btn-primary"
                data-testid="onboarding-login-btn"
              >
                Sign in to start <ArrowRight size={14} />
              </button>
              <button onClick={onClose} className="asc-btn-secondary" data-testid="onboarding-close-btn">
                Close
              </button>
            </>
          ) : (
            <>
              <button
                onClick={() => nav(`/signup?prefill=${encodeURIComponent(email)}`)}
                className="asc-btn-primary"
                data-testid="onboarding-signup-btn"
                style={{ background: "linear-gradient(135deg, #FFB000, #FF6B35)" }}
              >
                <Sparkles size={14} /> Create free account
              </button>
              <button onClick={onClose} className="asc-btn-secondary" data-testid="onboarding-close-btn">
                Maybe later
              </button>
            </>
          )
        ) : (
          <>
            {plan?.first_lesson_id && (
              <button
                onClick={() => { nav(`/lessons/${plan.first_lesson_id}`); onClose(); }}
                className="asc-btn-primary"
                data-testid="onboarding-start-lesson-btn"
              >
                Start lesson 1 <ArrowRight size={14} />
              </button>
            )}
            <button
              onClick={() => { nav("/paths"); onClose(); }}
              className="asc-btn-secondary"
              data-testid="onboarding-paths-btn"
            >
              View all paths
            </button>
            <button onClick={onClose} className="asc-btn-secondary" data-testid="onboarding-dashboard-btn">
              Go to dashboard
            </button>
          </>
        )}
      </div>
      {anonymous && !alreadyRegistered && (
        <p className="text-xs text-[var(--asc-text-muted)] mt-5 max-w-sm mx-auto">
          We just emailed your plan to <strong className="text-white">{email}</strong>. When you sign up, your plan is already waiting for you — no need to retake the quiz.
        </p>
      )}
    </motion.div>
  );
}
