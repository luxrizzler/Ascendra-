import { useState } from "react";
import { View, Text, StyleSheet, Pressable, TextInput, ActivityIndicator, KeyboardAvoidingView, Platform, ScrollView } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useRouter } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { C, RADIUS } from "@/src/theme";
import { useAuth } from "@/src/context/AuthContext";
import { startGoogleAuthMobile, startGoogleAuthWeb, exchangeSessionIdForToken } from "@/src/auth/google";
import { api } from "@/src/api";

export default function Login() {
  const router = useRouter();
  const { login, loginWithGoogleToken } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const routeAfterLogin = async () => {
    // Re-read auth context user (refreshed by login)
    // we'll fetch /auth/me directly to know flags without race condition
    try {
      const me = await api.get("/auth/me");
      if (me?.must_change_password) {
        router.replace("/change-password");
        return;
      }
      if (me?.is_admin) {
        router.replace("/admin");
        return;
      }
    } catch {}
    router.replace("/(tabs)/home");
  };

  const onSubmit = async () => {
    setError(null);
    setLoading(true);
    try {
      await login(email.trim(), password);
      await routeAfterLogin();
    } catch (e: any) {
      setError(e.message || "Login failed");
    } finally {
      setLoading(false);
    }
  };

  const onGoogle = async () => {
    setError(null);
    setGoogleLoading(true);
    try {
      if (Platform.OS === "web") {
        startGoogleAuthWeb();
        return;
      }
      const sid = await startGoogleAuthMobile();
      if (!sid) { setGoogleLoading(false); return; }
      const data = await exchangeSessionIdForToken(sid);
      await loginWithGoogleToken(data.session_token);
      await routeAfterLogin();
    } catch (e: any) {
      setError(e?.message || "Google sign-in failed");
      setGoogleLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.root} edges={["top", "bottom"]}>
      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === "ios" ? "padding" : undefined}>
        <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
          <Pressable testID="login-back-btn" onPress={() => router.back()} style={styles.back}>
            <Ionicons name="arrow-back" size={22} color={C.text} />
          </Pressable>
          <Text style={styles.kicker}>WELCOME BACK</Text>
          <Text style={styles.h1}>Sign in</Text>
          <Text style={styles.sub}>Pick up your streak where you left off.</Text>

          <View style={{ height: 32 }} />

          <Text style={styles.label}>Email</Text>
          <TextInput
            testID="login-email"
            value={email}
            onChangeText={setEmail}
            placeholder="you@email.com"
            placeholderTextColor={C.textMuted}
            keyboardType="email-address"
            autoCapitalize="none"
            style={styles.input}
          />

          <Text style={styles.label}>Password</Text>
          <TextInput
            testID="login-password"
            value={password}
            onChangeText={setPassword}
            placeholder="••••••••"
            placeholderTextColor={C.textMuted}
            secureTextEntry
            style={styles.input}
          />

          {error && <Text style={styles.error} testID="login-error">{error}</Text>}

          <Pressable testID="login-submit-btn" style={[styles.primaryBtn, loading && { opacity: 0.6 }]} onPress={onSubmit} disabled={loading}>
            {loading ? <ActivityIndicator color="#000" /> : <>
              <Text style={styles.primaryBtnText}>Sign in</Text>
              <Ionicons name="arrow-forward" size={18} color="#000" />
            </>}
          </Pressable>

          <Pressable testID="login-forgot-link" onPress={() => router.push("/forgot-password")} style={{ paddingVertical: 14, alignItems: "center" }}>
            <Text style={styles.linkText}>Forgot password?</Text>
          </Pressable>

          <View style={styles.dividerRow}>
            <View style={styles.dividerLine} />
            <Text style={styles.dividerText}>OR</Text>
            <View style={styles.dividerLine} />
          </View>

          <Pressable
            testID="login-google-btn"
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

          <Pressable testID="login-signup-link" onPress={() => router.replace("/onboarding")} style={{ paddingVertical: 20, alignItems: "center" }}>
            <Text style={styles.linkText}>New here? <Text style={{ color: C.brand, fontWeight: "700" }}>Create an account</Text></Text>
          </Pressable>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  scroll: { padding: 24, paddingBottom: 40 },
  back: { width: 40, height: 40, alignItems: "center", justifyContent: "center", marginBottom: 16, marginLeft: -8 },
  kicker: { fontSize: 11, fontWeight: "800", letterSpacing: 3, color: C.brand, marginBottom: 12 },
  h1: { fontSize: 36, fontWeight: "900", color: C.text, letterSpacing: -1 },
  sub: { fontSize: 15, color: C.textDim, marginTop: 10 },
  label: { color: C.textMuted, fontSize: 11, fontWeight: "700", letterSpacing: 1.5, marginBottom: 8, textTransform: "uppercase", marginTop: 16 },
  input: {
    backgroundColor: C.surface, borderWidth: 1, borderColor: C.border, color: C.text,
    paddingHorizontal: 16, paddingVertical: 14, borderRadius: RADIUS.md, fontSize: 16,
  },
  primaryBtn: {
    backgroundColor: C.brand, paddingVertical: 16, borderRadius: RADIUS.lg,
    alignItems: "center", flexDirection: "row", justifyContent: "center", gap: 8, marginTop: 24,
  },
  primaryBtnText: { color: "#000", fontWeight: "800", fontSize: 16 },
  linkText: { color: C.textDim, fontSize: 14 },
  error: { color: C.danger, marginTop: 12, fontSize: 14 },
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
