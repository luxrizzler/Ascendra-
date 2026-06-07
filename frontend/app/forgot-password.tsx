import { useState } from "react";
import {
  View, Text, StyleSheet, TextInput, Pressable, KeyboardAvoidingView, Platform, ActivityIndicator,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useRouter } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { LinearGradient } from "expo-linear-gradient";
import { C, RADIUS } from "@/src/theme";
import { api } from "@/src/api";

export default function ForgotPassword() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const onSubmit = async () => {
    setErr(null);
    if (!email.includes("@")) { setErr("Enter a valid email address."); return; }
    setLoading(true);
    try {
      await api.post("/auth/forgot-password", { email: email.trim().toLowerCase() });
      setSent(true);
    } catch (e: any) {
      setErr(e?.message || "Could not send reset email.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.root}>
      <LinearGradient pointerEvents="none" colors={["rgba(255,176,0,0.18)", "transparent"]} style={styles.glow} />
      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === "ios" ? "padding" : undefined}>
        <Pressable testID="fp-back" onPress={() => router.replace("/login")} style={styles.back}>
          <Ionicons name="chevron-back" size={22} color={C.textDim} />
          <Text style={styles.backText}>Back to sign in</Text>
        </Pressable>

        <View style={styles.wrap}>
          {!sent ? (
            <>
              <View style={styles.iconWrap}><Ionicons name="mail" size={28} color={C.brand} /></View>
              <Text style={styles.kicker}>FORGOT PASSWORD</Text>
              <Text style={styles.h1}>Let&apos;s get you{"\n"}back in</Text>
              <Text style={styles.sub}>
                Enter the email tied to your Ascendra account. We&apos;ll send you a magic link to reset your password.
              </Text>

              <View style={styles.field}>
                <Text style={styles.label}>Email</Text>
                <TextInput
                  testID="fp-email"
                  value={email}
                  onChangeText={setEmail}
                  placeholder="you@email.com"
                  placeholderTextColor={C.textMuted}
                  keyboardType="email-address"
                  autoCapitalize="none"
                  style={styles.input}
                />
              </View>

              {err && <Text style={styles.err} testID="fp-err">{err}</Text>}

              <Pressable testID="fp-submit" onPress={onSubmit} disabled={loading} style={[styles.btn, loading && { opacity: 0.6 }]}>
                {loading ? <ActivityIndicator color="#000" /> : (
                  <>
                    <Text style={styles.btnText}>Send reset link</Text>
                    <Ionicons name="paper-plane" size={16} color="#000" />
                  </>
                )}
              </Pressable>
            </>
          ) : (
            <View testID="fp-sent">
              <View style={[styles.iconWrap, { backgroundColor: C.brand }]}>
                <Ionicons name="checkmark" size={28} color="#000" />
              </View>
              <Text style={styles.kicker}>CHECK YOUR INBOX</Text>
              <Text style={styles.h1}>Reset link{"\n"}sent ✨</Text>
              <Text style={styles.sub}>
                If an account exists for <Text style={{ color: C.text, fontWeight: "700" }}>{email}</Text>,
                you&apos;ll get an email with a one-click reset link in the next minute.
                It expires in <Text style={{ color: C.text, fontWeight: "700" }}>1 hour</Text>.
              </Text>
              <Text style={styles.note}>
                Didn&apos;t see it? Check your spam folder, or come back here and try again.
              </Text>
              <Pressable testID="fp-back-login" onPress={() => router.replace("/login")} style={styles.btn}>
                <Text style={styles.btnText}>Back to sign in</Text>
                <Ionicons name="arrow-forward" size={16} color="#000" />
              </Pressable>
            </View>
          )}
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  glow: { position: "absolute", top: 0, left: 0, right: 0, height: 320 },
  back: { flexDirection: "row", alignItems: "center", paddingHorizontal: 16, paddingTop: 6, gap: 4 },
  backText: { color: C.textDim, fontSize: 13, fontWeight: "600" },
  wrap: { padding: 24, flex: 1, justifyContent: "center", maxWidth: 480, width: "100%", alignSelf: "center" },
  iconWrap: { width: 60, height: 60, borderRadius: 30, backgroundColor: C.brandDim, alignItems: "center", justifyContent: "center", marginBottom: 18 },
  kicker: { fontSize: 11, fontWeight: "800", letterSpacing: 3, color: C.brand },
  h1: { fontSize: 34, fontWeight: "900", color: C.text, marginTop: 8, letterSpacing: -0.8, lineHeight: 40 },
  sub: { fontSize: 15, color: C.textDim, marginTop: 16, marginBottom: 28, lineHeight: 22 },
  note: { fontSize: 12, color: C.textMuted, marginBottom: 24, lineHeight: 18 },
  field: { marginBottom: 14 },
  label: { color: C.textMuted, fontSize: 11, fontWeight: "700", letterSpacing: 1.5, marginBottom: 8, textTransform: "uppercase" },
  input: {
    backgroundColor: C.surface, borderWidth: 1, borderColor: C.border, color: C.text,
    paddingHorizontal: 16, paddingVertical: 14, borderRadius: RADIUS.md, fontSize: 16,
  },
  err: { color: C.danger, marginBottom: 12, fontSize: 14 },
  btn: {
    backgroundColor: C.brand, paddingVertical: 16, borderRadius: RADIUS.lg,
    alignItems: "center", flexDirection: "row", justifyContent: "center", gap: 8, marginTop: 8,
  },
  btnText: { color: "#000", fontWeight: "800", fontSize: 16 },
});
