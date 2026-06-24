import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { ArrowRight, ArrowLeft, Briefcase, Rocket, Camera, Zap, Sparkles, CheckCircle2, ImageIcon, Video, Mic, Code2, Bot, MessagesSquare } from "lucide-react";
import { toast } from "sonner";

const STEPS = [
  {
    id: "goal",
    title: "What's your goal with AI?",
    subtitle: "We'll personalize your learning path.",
    options: [
      { value: "career", label: "Advance my career", icon: Briefcase, hint: "Get promoted, switch roles, earn more." },
      { value: "business", label: "Start a business", icon: Rocket, hint: "Ship an AI product or SaaS." },
      { value: "creator", label: "Create content", icon: Camera, hint: "Make stunning content 10x faster." },
      { value: "productivity", label: "Boost productivity", icon: Zap, hint: "Get hours back every day." },
    ],
  },
  {
    id: "experience",
    title: "How much AI experience do you have?",
    subtitle: "Honesty unlocks the best path.",
    options: [
      { value: "beginner", label: "Beginner", hint: "I've barely used ChatGPT." },
      { value: "some", label: "Some experience", hint: "I use AI weekly. Want to go deeper." },
      { value: "advanced", label: "Advanced", hint: "Already building with AI. Want to master it." },
    ],
  },
  {
    id: "time_per_day",
    title: "How much time can you commit daily?",
    subtitle: "Even 5 minutes compounds fast.",
    options: [
      { value: "5", label: "5 minutes", hint: "A lesson a day." },
      { value: "15", label: "15 minutes", hint: "Recommended pace." },
      { value: "30", label: "30 minutes", hint: "Serious learner." },
      { value: "60", label: "60+ minutes", hint: "All-in." },
    ],
  },
  {
    id: "focus",
    title: "Which AI superpower interests you most?",
    subtitle: "Pick one to start. You can explore others later.",
    options: [
      { value: "text", label: "Text & writing", icon: MessagesSquare },
      { value: "image", label: "Image generation", icon: ImageIcon },
      { value: "video", label: "AI video", icon: Video },
      { value: "voice", label: "Voice & audio", icon: Mic },
      { value: "code", label: "Coding with AI", icon: Code2 },
      { value: "agents", label: "AI agents & automation", icon: Bot },
    ],
  },
];

export default function Onboarding() {
  const nav = useNavigate();
  const { refresh } = useAuth();
  const [step, setStep] = useState(0);
  const [answers, setAnswers] = useState({});
  const [busy, setBusy] = useState(false);

  const cur = STEPS[step];
  const total = STEPS.length;

  const pick = async (val) => {
    const next = { ...answers, [cur.id]: val };
    setAnswers(next);
    if (step < total - 1) {
      setStep(step + 1);
      return;
    }
    // submit
    setBusy(true);
    try {
      const r = await api.put("/auth/me/quiz", next);
      await refresh();
      toast.success("Path personalized");
      nav(`/paths/${r.recommended_path_id}`);
    } catch (err) {
      toast.error(err.message || "Could not save quiz");
    } finally {
      setBusy(false);
    }
  };

  const back = () => step > 0 && setStep(step - 1);
  const skip = () => nav("/dashboard");

  return (
    <div className="min-h-[80vh] px-5 py-10" data-testid="onboarding-page">
      <div className="max-w-3xl mx-auto">
        {/* Progress */}
        <div className="flex items-center gap-2 mb-8">
          {STEPS.map((_, i) => (
            <div key={i} className="flex-1 h-1.5 rounded-full" style={{ background: i <= step ? "#FFB000" : "rgba(191,180,255,0.15)" }} />
          ))}
        </div>

        <div className="flex items-center justify-between mb-4">
          <div className="asc-kicker">Step {step + 1} of {total}</div>
          <button onClick={skip} className="text-sm text-[var(--asc-text-muted)] hover:text-white" data-testid="onb-skip-btn">Skip</button>
        </div>
        <h1 className="asc-h2 text-3xl sm:text-4xl">{cur.title}</h1>
        <p className="text-[var(--asc-text-dim)] mt-2">{cur.subtitle}</p>

        <div className="grid sm:grid-cols-2 gap-3 mt-8">
          {cur.options.map((o) => {
            const Icon = o.icon || Sparkles;
            const selected = answers[cur.id] === o.value;
            return (
              <button
                key={o.value}
                onClick={() => pick(o.value)}
                disabled={busy}
                data-testid={`onb-option-${cur.id}-${o.value}`}
                className={`asc-card p-5 text-left transition-all ${selected ? "border-[var(--asc-brand)]" : ""}`}
                style={selected ? { borderColor: "#FFB000", background: "rgba(255,176,0,0.06)" } : {}}>
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl grid place-items-center" style={{ background: selected ? "#FFB000" : "rgba(124,58,237,0.15)" }}>
                    <Icon size={20} color={selected ? "#000" : "#BFB4FF"} />
                  </div>
                  <div className="font-bold text-base flex-1">{o.label}</div>
                  {selected && <CheckCircle2 size={20} className="text-[var(--asc-brand)]" />}
                </div>
                {o.hint && <div className="text-sm text-[var(--asc-text-dim)] mt-2">{o.hint}</div>}
              </button>
            );
          })}
        </div>

        <div className="flex items-center justify-between mt-8">
          <button onClick={back} disabled={step === 0} className={`asc-btn-secondary text-sm ${step === 0 ? "opacity-40 cursor-not-allowed" : ""}`} data-testid="onb-back-btn">
            <ArrowLeft size={14} /> Back
          </button>
          <div className="text-xs text-[var(--asc-text-muted)]">{step === total - 1 ? "Pick one to finish" : "Pick one to continue"}<ArrowRight size={12} className="inline ml-1" /></div>
        </div>
      </div>
    </div>
  );
}
