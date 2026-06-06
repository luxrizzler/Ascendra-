import { useState } from "react";
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

const GOALS = [
  { id: "career",       title: "Grow my career",     blurb: "Get more done & stand out at work.", icon: "trending-up" },
  { id: "business",     title: "Build a business",   blurb: "Use AI to launch & scale a venture.", icon: "rocket-outline" },
  { id: "creator",      title: "Create content",     blurb: "Make videos, images, and writing.",  icon: "sparkles-outline" },
  { id: "productivity", title: "Get more time back", blurb: "Automate the boring stuff.",         icon: "flash-outline" },
];

export default function Onboarding() {
  const router = useRouter();
  const { signup, loginWithGoogleToken } = useAuth();
  const [step, setStep] = useState(0);
  const [goal, setGoal] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onCreate = async () => {
    setError(null);
    if (!email.includes("@") || password.length < 6) {
      setError("Use a valid email and a password of at least 6 chars.");
      return;
    }
    setLoading(true);
    try {
      await signup(email.trim(), password, name.trim() || undefined, goal || undefined);
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
      // Stash goal so /auth callback can pass it through after redirect
      if (goal) await storage.setItem("ascendra_pending_goal", goal);
      if (Platform.OS === "web") {
        startGoogleAuthWeb(); // full page redirect
        return;
      }
      const sid = await startGoogleAuthMobile();
      if (!sid) {
        setGoogleLoading(false);
        return;
      }
      const { exchangeSessionIdForToken } = await import("@/src/auth/google");
      const data = await exchangeSessionIdForToken(sid);
      await loginWithGoogleToken(data.session_token, goal || undefined);
      router.replace("/(tabs)/home");
    } catch (e: any) {
      setError(e?.message || "Google sign-in failed");
      setGoogleLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.root} edges={["top", "bottom"]}>
      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === "ios" ? "padding" : undefined}
      >
        <View style={styles.progressRow}>
          {[0, 1, 2].map((i) => (
            <View key={i} style={[styles.progressBar, i <= step && { backgroundColor: C.brand }]} />
          ))}
        </View>

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
                <Bullet icon="library-outline" text="4 learning paths. 36+ lessons." />
                <Bullet icon="chatbubbles-outline" text="AI Tutor in your pocket." />
                <Bullet icon="rocket-outline" text="Build a real business with AI." />
              </View>

              <Pressable testID="onboarding-continue-btn" style={styles.primaryBtn} onPress={() => setStep(1)}>
                <Text style={styles.primaryBtnText}>Get started</Text>
                <Ionicons name="arrow-forward" size={18} color="#000" />
              </Pressable>
              <Pressable testID="onboarding-login-link" onPress={() => router.push("/login")} style={{ paddingVertical: 16, alignItems: "center" }}>
                <Text style={styles.linkText}>I already have an account</Text>
              </Pressable>
            </View>
          )}

          {step === 1 && (
            <View>
              <Text style={styles.kicker}>STEP 1 OF 2</Text>
              <Text style={styles.h1}>What brought you here?</Text>
              <Text style={styles.sub}>We&apos;ll tailor your first path. Pick one.</Text>
              <View style={{ height: 24 }} />
              {GOALS.map((g) => {
                const selected = goal === g.id;
                return (
                  <Pressable
                    key={g.id}
                    testID={`goal-${g.id}`}
                    onPress={() => setGoal(g.id)}
                    style={[styles.goalCard, selected && styles.goalCardSelected]}
                  >
                    <View style={[styles.goalIcon, selected && { backgroundColor: C.brand }]}>
                      <Ionicons name={g.icon as any} size={22} color={selected ? "#000" : C.brand} />
                    </View>
                    <View style={{ flex: 1 }}>
                      <Text style={styles.goalTitle}>{g.title}</Text>
                      <Text style={styles.goalBlurb}>{g.blurb}</Text>
                    </View>
                    {selected && <Ionicons name="checkmark-circle" size={22} color={C.brand} />}
                  </Pressable>
                );
              })}
              <Pressable
                testID="goals-next-btn"
                style={[styles.primaryBtn, !goal && styles.primaryBtnDisabled]}
                disabled={!goal}
                onPress={() => setStep(2)}
              >
                <Text style={styles.primaryBtnText}>Continue</Text>
                <Ionicons name="arrow-forward" size={18} color="#000" />
              </Pressable>
            </View>
          )}

          {step === 2 && (
            <View>
              <Text style={styles.kicker}>STEP 2 OF 2</Text>
              <Text style={styles.h1}>Create your account</Text>
              <Text style={styles.sub}>Save your progress and earn XP.</Text>
              <View style={{ height: 20 }} />

              <Field label="Name (optional)" value={name} onChangeText={setName} placeholder="Alex" testID="signup-name" />
              <Field label="Email" value={email} onChangeText={setEmail} placeholder="you@email.com" keyboardType="email-address" autoCapitalize="none" testID="signup-email" />
              <Field label="Password" value={password} onChangeText={setPassword} placeholder="6+ characters" secureTextEntry testID="signup-password" />

              {error && <Text style={styles.error} testID="signup-error">{error}</Text>}

              <Pressable testID="signup-submit-btn" style={[styles.primaryBtn, loading && { opacity: 0.6 }]} onPress={onCreate} disabled={loading}>
                {loading ? <ActivityIndicator color="#000" /> : <>
                  <Text style={styles.primaryBtnText}>Start learning</Text>
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
});
