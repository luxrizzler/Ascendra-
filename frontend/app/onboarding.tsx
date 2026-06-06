import { useMemo, useState } from "react";
import {
  View, Text, StyleSheet, Pressable, ScrollView, TextInput, KeyboardAvoidingView, Platform, ActivityIndicator,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useRouter } from "expo-router";
import { LinearGradient } from "expo-linear-gradient";
import { Ionicons } from "@expo/vector-icons";
import { C, RADIUS } from "@/src/theme";
import { useAuth } from "@/src/context/AuthContext";
import { startGoogleAuthMobile, startGoogleAuthWeb } from "@/src/auth/google";
import { storage } from "@/src/utils/storage";
import { api } from "@/src/api";

const TOTAL_STEPS = 6; // welcome + 4 quiz + signup

const GOALS = [
  { id: "career",       title: "Grow my career",     blurb: "Get more done & stand out at work.", icon: "trending-up" },
  { id: "business",     title: "Build a business",   blurb: "Use AI to launch & scale a venture.", icon: "rocket-outline" },
  { id: "creator",      title: "Create content",     blurb: "Make videos, images, and writing.",  icon: "sparkles-outline" },
  { id: "productivity", title: "Get more time back", blurb: "Automate the boring stuff.",         icon: "flash-outline" },
];

const LEVELS = [
  { id: "beginner",  title: "Total beginner",   blurb: "I've barely used ChatGPT.",          icon: "sparkles" },
  { id: "some",      title: "I dabble",         blurb: "I use AI tools occasionally.",       icon: "compass-outline" },
  { id: "advanced",  title: "Power user",       blurb: "I want pro-level workflows.",        icon: "flame" },
];

const TIMES = [
  { id: "5",  title: "5 min/day",  blurb: "Quick daily nudge",   icon: "leaf-outline" },
  { id: "15", title: "15 min/day", blurb: "Most popular choice", icon: "flash-outline", hot: true },
  { id: "30", title: "30 min/day", blurb: "Serious progress",    icon: "rocket-outline" },
  { id: "60", title: "60+ min/day", blurb: "Going all in",       icon: "trophy-outline" },
];

const FOCUS = [
  { id: "text",   title: "Writing & ideation",     icon: "create-outline" },
  { id: "image",  title: "Image generation",       icon: "image-outline" },
  { id: "video",  title: "Video / Sora",           icon: "videocam-outline" },
  { id: "voice",  title: "Voice / audio",          icon: "mic-outline" },
  { id: "code",   title: "Coding with AI",         icon: "code-slash-outline" },
  { id: "agents", title: "Automations / agents",   icon: "git-network-outline" },
];

// Mirrors backend /api/auth/me/quiz logic so we can preview the rec live.
function recommendPath(goal: string | null, exp: string | null, focus: string | null) {
  if (exp === "beginner") return "fundamentals";
  const f: Record<string, string> = {
    image: "creators", video: "creators", voice: "creators",
    code: "code-with-ai", agents: "automation", text: "prompt-mastery",
  };
  if (focus && f[focus]) return f[focus];
  const g: Record<string, string> = {
    business: "business", creator: "creators", productivity: "productivity", career: "prompt-mastery",
  };
  return (goal && g[goal]) || "fundamentals";
}

const PATH_LABELS: Record<string, { title: string; tagline: string; color: string }> = {
  "fundamentals":      { title: "AI Fundamentals",            tagline: "Your launchpad. Master the basics in a week.",        color: "#FFB000" },
  "business":          { title: "Build a Business with AI",   tagline: "Idea → MVP → revenue, AI-first.",                     color: "#FF6B35" },
  "creators":          { title: "AI for Creators",            tagline: "Make scroll-stopping content with Nano Banana + Sora.", color: "#BFB4FF" },
  "productivity":      { title: "AI for Productivity",        tagline: "Reclaim hours every week. Automate the boring stuff.", color: "#34D399" },
  "prompt-mastery":    { title: "Prompt Engineering Mastery", tagline: "Pro-level prompts. Better outputs from every model.",  color: "#7C3AED" },
  "automation":        { title: "AI Automation Stack",        tagline: "Agents + MCP. Build software that runs your work.",    color: "#10A37F" },
  "code-with-ai":      { title: "Code With AI",               tagline: "Cursor + Claude Code. Ship 10x faster.",              color: "#4285F4" },
};

export default function Onboarding() {
  const router = useRouter();
  const { signup, loginWithGoogleToken } = useAuth();
  const [step, setStep] = useState(0);
  const [goal, setGoal] = useState<string | null>(null);
  const [exp, setExp] = useState<string | null>(null);
  const [time, setTime] = useState<string | null>(null);
  const [focus, setFocus] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const recommendedId = useMemo(() => recommendPath(goal, exp, focus), [goal, exp, focus]);
  const recommended = PATH_LABELS[recommendedId] || PATH_LABELS["fundamentals"];

  const persistQuiz = async () => {
    try {
      await api.put("/auth/me/quiz", {
        goal: goal || undefined,
        experience: exp || undefined,
        time_per_day: time || undefined,
        focus: focus || undefined,
      });
    } catch {
      // non-blocking; user data still saved at signup
    }
  };

  const onCreate = async () => {
    setError(null);
    if (!email.includes("@") || password.length < 6) {
      setError("Use a valid email and a password of at least 6 chars.");
      return;
    }
    setLoading(true);
    try {
      await signup(email.trim(), password, name.trim() || undefined, goal || undefined);
      await persistQuiz();
      router.replace("/(tabs)/home");
    } catch (e: any) {
      setError(e.message || "Sign up failed");
    } finally {
      setLoading(false);
    }
  };

  const onGoogle = async () => {
    setError(null);
    setGoogleLoading(true);
    try {
      // Stash quiz answers so /auth callback can persist them after redirect
      if (goal) await storage.setItem("ascendra_pending_goal", goal);
      await storage.setItem("ascendra_pending_quiz", JSON.stringify({
        goal, experience: exp, time_per_day: time, focus,
      }));
      if (Platform.OS === "web") {
        startGoogleAuthWeb();
        return;
      }
      const sid = await startGoogleAuthMobile();
      if (!sid) { setGoogleLoading(false); return; }
      const { exchangeSessionIdForToken } = await import("@/src/auth/google");
      const data = await exchangeSessionIdForToken(sid);
      await loginWithGoogleToken(data.session_token, goal || undefined);
      await persistQuiz();
      router.replace("/(tabs)/home");
    } catch (e: any) {
      setError(e?.message || "Google sign-in failed");
      setGoogleLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.root} edges={["top", "bottom"]}>
      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === "ios" ? "padding" : undefined}>
        <View style={styles.progressRow}>
          {Array.from({ length: TOTAL_STEPS }, (_, i) => (
            <View key={i} style={[styles.progressBar, i <= step && { backgroundColor: C.brand }]} />
          ))}
        </View>

        {step > 0 && step < 5 && (
          <Pressable testID="onboarding-back" onPress={() => setStep((s) => s - 1)} style={styles.backBtn}>
            <Ionicons name="chevron-back" size={22} color={C.textDim} />
            <Text style={styles.backText}>Back</Text>
          </Pressable>
        )}

        <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
          {step === 0 && (
            <View>
              <Text style={styles.kicker}>ASCENDRA</Text>
              <Text style={styles.hero}>Ready to rise{"\n"}today?</Text>
              <Text style={styles.sub}>
                Beginner to advanced. Hands-on lessons covering every model that matters in 2026 —
                GPT-5.2, Claude 4.5, Gemini 3, Nano Banana, Sora 2 & more.
              </Text>

              <View style={styles.bullets}>
                <Bullet icon="library-outline" text="10 learning paths. 100+ lessons." />
                <Bullet icon="chatbubbles-outline" text="AI Tutor in your pocket." />
                <Bullet icon="ribbon-outline" text="Earn certificates as you level up." />
              </View>

              <Pressable testID="onboarding-continue-btn" style={styles.primaryBtn} onPress={() => setStep(1)}>
                <Text style={styles.primaryBtnText}>Take the 30-second quiz</Text>
                <Ionicons name="arrow-forward" size={18} color="#000" />
              </Pressable>
              <Pressable testID="onboarding-login-link" onPress={() => router.push("/login")} style={{ paddingVertical: 16, alignItems: "center" }}>
                <Text style={styles.linkText}>I already have an account</Text>
              </Pressable>
            </View>
          )}

          {step === 1 && (
            <QuizStep
              stepLabel="QUESTION 1 OF 4"
              title="What brought you here?"
              subtitle="We'll tailor your first path. Pick one."
              options={GOALS}
              selectedId={goal}
              onSelect={setGoal}
              onNext={() => setStep(2)}
              testIDPrefix="goal"
            />
          )}

          {step === 2 && (
            <QuizStep
              stepLabel="QUESTION 2 OF 4"
              title="What's your AI level?"
              subtitle="No judgment — we meet you where you are."
              options={LEVELS}
              selectedId={exp}
              onSelect={setExp}
              onNext={() => setStep(3)}
              testIDPrefix="experience"
            />
          )}

          {step === 3 && (
            <QuizStep
              stepLabel="QUESTION 3 OF 4"
              title="How much time can you give it?"
              subtitle="Be honest — small daily wins compound."
              options={TIMES}
              selectedId={time}
              onSelect={setTime}
              onNext={() => setStep(4)}
              testIDPrefix="time"
            />
          )}

          {step === 4 && (
            <QuizStep
              stepLabel="QUESTION 4 OF 4"
              title="What pulls you in most?"
              subtitle="We'll skip what doesn't matter to you."
              options={FOCUS}
              selectedId={focus}
              onSelect={setFocus}
              onNext={() => setStep(5)}
              testIDPrefix="focus"
              compact
            />
          )}

          {step === 5 && (
            <View>
              <Text style={styles.kicker}>WE&apos;VE GOT YOUR PATH</Text>

              {/* Recommendation card */}
              <View testID="recommendation-card" style={[styles.recCard, { borderColor: recommended.color }]}>
                <LinearGradient
                  colors={[recommended.color + "33", "transparent"]}
                  style={StyleSheet.absoluteFillObject as any}
                />
                <View style={[styles.recBadge, { backgroundColor: recommended.color }]}>
                  <Ionicons name="star" size={12} color="#000" />
                  <Text style={styles.recBadgeText}>RECOMMENDED FOR YOU</Text>
                </View>
                <Text style={styles.recTitle}>{recommended.title}</Text>
                <Text style={styles.recSub}>{recommended.tagline}</Text>
                <View style={styles.recMeta}>
                  <View style={styles.metaPill}><Ionicons name="time-outline" size={12} color={C.textDim} /><Text style={styles.metaPillText}>{time || "15"} min/day</Text></View>
                  <View style={styles.metaPill}><Ionicons name="trending-up" size={12} color={C.textDim} /><Text style={styles.metaPillText}>{exp || "Beginner"}</Text></View>
                </View>
              </View>

              <Text style={styles.h1}>Create your account{"\n"}to start</Text>
              <Text style={styles.sub}>We&apos;ll save your progress, XP & certificates.</Text>
              <View style={{ height: 20 }} />

              <Field label="Name (optional)" value={name} onChangeText={setName} placeholder="Alex" testID="signup-name" />
              <Field label="Email" value={email} onChangeText={setEmail} placeholder="you@email.com" keyboardType="email-address" autoCapitalize="none" testID="signup-email" />
              <Field label="Password" value={password} onChangeText={setPassword} placeholder="6+ characters" secureTextEntry testID="signup-password" />

              {error && <Text style={styles.error} testID="signup-error">{error}</Text>}

              <Pressable testID="signup-submit-btn" style={[styles.primaryBtn, loading && { opacity: 0.6 }]} onPress={onCreate} disabled={loading}>
                {loading ? <ActivityIndicator color="#000" /> : <>
                  <Text style={styles.primaryBtnText}>Start my path</Text>
                  <Ionicons name="arrow-forward" size={18} color="#000" />
                </>}
              </Pressable>

              <View style={styles.dividerRow}>
                <View style={styles.dividerLine} />
                <Text style={styles.dividerText}>OR</Text>
                <View style={styles.dividerLine} />
              </View>

              <Pressable
                testID="signup-google-btn"
                onPress={onGoogle}
                disabled={googleLoading}
                style={[styles.googleBtn, googleLoading && { opacity: 0.6 }]}
              >
                {googleLoading ? (
                  <ActivityIndicator color={C.text} />
                ) : (
                  <>
                    <Ionicons name="logo-google" size={18} color={C.text} />
                    <Text style={styles.googleBtnText}>Continue with Google</Text>
                  </>
                )}
              </Pressable>

              <Pressable onPress={() => router.push("/login")} style={{ paddingVertical: 16, alignItems: "center" }}>
                <Text style={styles.linkText}>I already have an account</Text>
              </Pressable>
            </View>
          )}
        </ScrollView>
      </KeyboardAvoidingView>
      <LinearGradient
        pointerEvents="none"
        colors={["rgba(255,176,0,0.18)", "transparent"]}
        style={styles.glow}
      />
    </SafeAreaView>
  );
}

function QuizStep(props: {
  stepLabel: string;
  title: string;
  subtitle: string;
  options: any[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onNext: () => void;
  testIDPrefix: string;
  compact?: boolean;
}) {
  return (
    <View>
      <Text style={styles.kicker}>{props.stepLabel}</Text>
      <Text style={styles.h1}>{props.title}</Text>
      <Text style={styles.sub}>{props.subtitle}</Text>
      <View style={{ height: 24 }} />
      <View style={props.compact ? styles.gridWrap : undefined}>
        {props.options.map((opt) => {
          const selected = props.selectedId === opt.id;
          return (
            <Pressable
              key={opt.id}
              testID={`${props.testIDPrefix}-${opt.id}`}
              onPress={() => props.onSelect(opt.id)}
              style={[
                props.compact ? styles.gridCard : styles.goalCard,
                selected && styles.goalCardSelected,
              ]}
            >
              {!props.compact && (
                <View style={[styles.goalIcon, selected && { backgroundColor: C.brand }]}>
                  <Ionicons name={opt.icon as any} size={22} color={selected ? "#000" : C.brand} />
                </View>
              )}
              {props.compact && (
                <View style={[styles.gridIcon, selected && { backgroundColor: C.brand }]}>
                  <Ionicons name={opt.icon as any} size={20} color={selected ? "#000" : C.brand} />
                </View>
              )}
              <View style={{ flex: 1 }}>
                <Text style={styles.goalTitle}>{opt.title}</Text>
                {opt.blurb && <Text style={styles.goalBlurb}>{opt.blurb}</Text>}
              </View>
              {opt.hot && (
                <View style={styles.hotBadge}>
                  <Text style={styles.hotText}>POPULAR</Text>
                </View>
              )}
              {selected && <Ionicons name="checkmark-circle" size={22} color={C.brand} />}
            </Pressable>
          );
        })}
      </View>
      <Pressable
        testID={`${props.testIDPrefix}-next-btn`}
        style={[styles.primaryBtn, !props.selectedId && styles.primaryBtnDisabled]}
        disabled={!props.selectedId}
        onPress={props.onNext}
      >
        <Text style={styles.primaryBtnText}>Continue</Text>
        <Ionicons name="arrow-forward" size={18} color="#000" />
      </Pressable>
    </View>
  );
}

function Bullet({ icon, text }: { icon: any; text: string }) {
  return (
    <View style={styles.bulletRow}>
      <View style={styles.bulletIcon}><Ionicons name={icon} size={18} color={C.brand} /></View>
      <Text style={styles.bulletText}>{text}</Text>
    </View>
  );
}

function Field(props: any) {
  return (
    <View style={{ marginBottom: 14 }}>
      <Text style={styles.label}>{props.label}</Text>
      <TextInput
        {...props}
        placeholderTextColor={C.textMuted}
        style={styles.input}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  scroll: { padding: 24, paddingBottom: 60 },
  progressRow: { flexDirection: "row", gap: 6, paddingHorizontal: 24, paddingTop: 8 },
  progressBar: { flex: 1, height: 4, borderRadius: 2, backgroundColor: C.surface2 },
  backBtn: { flexDirection: "row", alignItems: "center", gap: 4, paddingHorizontal: 20, paddingTop: 14, paddingBottom: 4 },
  backText: { color: C.textDim, fontSize: 13, fontWeight: "600" },
  kicker: { fontSize: 11, fontWeight: "800", letterSpacing: 3, color: C.brand, marginBottom: 16, marginTop: 24 },
  hero: { fontSize: 44, fontWeight: "900", color: C.text, letterSpacing: -1.5, lineHeight: 48 },
  h1: { fontSize: 30, fontWeight: "800", color: C.text, letterSpacing: -0.8 },
  sub: { fontSize: 16, color: C.textDim, lineHeight: 24, marginTop: 16 },
  bullets: { marginTop: 32, marginBottom: 40, gap: 14 },
  bulletRow: { flexDirection: "row", alignItems: "center", gap: 12 },
  bulletIcon: { width: 32, height: 32, borderRadius: 16, alignItems: "center", justifyContent: "center", backgroundColor: C.brandDim },
  bulletText: { color: C.text, fontSize: 15, flex: 1 },
  primaryBtn: {
    backgroundColor: C.brand, paddingVertical: 16, borderRadius: RADIUS.lg,
    alignItems: "center", flexDirection: "row", justifyContent: "center", gap: 8, marginTop: 8,
  },
  primaryBtnDisabled: { opacity: 0.4 },
  primaryBtnText: { color: "#000", fontWeight: "800", fontSize: 16 },
  linkText: { color: C.textDim, fontSize: 14 },
  goalCard: {
    flexDirection: "row", alignItems: "center", gap: 14, backgroundColor: C.surface,
    padding: 16, borderRadius: RADIUS.lg, marginBottom: 10, borderWidth: 1, borderColor: C.border,
  },
  goalCardSelected: { borderColor: C.brand, backgroundColor: "rgba(255,176,0,0.06)" },
  goalIcon: { width: 44, height: 44, borderRadius: 12, backgroundColor: C.brandDim, alignItems: "center", justifyContent: "center" },
  goalTitle: { color: C.text, fontWeight: "700", fontSize: 16 },
  goalBlurb: { color: C.textDim, fontSize: 13, marginTop: 2 },
  gridWrap: { flexDirection: "row", flexWrap: "wrap", gap: 10, marginBottom: 6 },
  gridCard: {
    flexBasis: "48%", flexGrow: 1,
    flexDirection: "row", alignItems: "center", gap: 10,
    backgroundColor: C.surface, padding: 14, borderRadius: RADIUS.lg,
    borderWidth: 1, borderColor: C.border, marginBottom: 4,
  },
  gridIcon: { width: 34, height: 34, borderRadius: 10, backgroundColor: C.brandDim, alignItems: "center", justifyContent: "center" },
  hotBadge: { backgroundColor: C.coral, paddingHorizontal: 6, paddingVertical: 2, borderRadius: RADIUS.pill, marginRight: 4 },
  hotText: { color: "#fff", fontSize: 9, fontWeight: "900", letterSpacing: 1 },
  label: { color: C.textMuted, fontSize: 11, fontWeight: "700", letterSpacing: 1.5, marginBottom: 8, textTransform: "uppercase" },
  input: {
    backgroundColor: C.surface, borderWidth: 1, borderColor: C.border, color: C.text,
    paddingHorizontal: 16, paddingVertical: 14, borderRadius: RADIUS.md, fontSize: 16,
  },
  error: { color: C.danger, marginBottom: 12, fontSize: 14 },
  glow: { position: "absolute", top: 0, left: 0, right: 0, height: 320, zIndex: -1 },
  dividerRow: { flexDirection: "row", alignItems: "center", gap: 12, marginTop: 18, marginBottom: 14 },
  dividerLine: { flex: 1, height: 1, backgroundColor: C.border },
  dividerText: { color: C.textMuted, fontSize: 11, fontWeight: "700", letterSpacing: 2 },
  googleBtn: {
    flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 10,
    paddingVertical: 14, borderRadius: RADIUS.lg, backgroundColor: C.surface,
    borderWidth: 1, borderColor: C.borderStrong,
  },
  googleBtnText: { color: C.text, fontWeight: "700", fontSize: 15 },
  recCard: {
    padding: 18, borderRadius: RADIUS.xl, borderWidth: 1, marginBottom: 20,
    backgroundColor: C.surface, overflow: "hidden",
  },
  recBadge: {
    flexDirection: "row", alignItems: "center", gap: 4, alignSelf: "flex-start",
    paddingHorizontal: 8, paddingVertical: 4, borderRadius: RADIUS.pill, marginBottom: 12,
  },
  recBadgeText: { color: "#000", fontWeight: "900", fontSize: 9, letterSpacing: 1 },
  recTitle: { color: C.text, fontSize: 22, fontWeight: "900", letterSpacing: -0.5 },
  recSub: { color: C.textDim, fontSize: 13, marginTop: 6, lineHeight: 18 },
  recMeta: { flexDirection: "row", gap: 8, marginTop: 14 },
  metaPill: { flexDirection: "row", alignItems: "center", gap: 4, backgroundColor: C.surface2, paddingHorizontal: 10, paddingVertical: 5, borderRadius: RADIUS.pill },
  metaPillText: { color: C.textDim, fontSize: 11, fontWeight: "700", textTransform: "capitalize" },
});
