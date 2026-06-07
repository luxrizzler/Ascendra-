import { useEffect, useState } from "react";
import {
  View, Text, StyleSheet, TextInput, Pressable, KeyboardAvoidingView, Platform, ActivityIndicator,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useRouter, useLocalSearchParams } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { LinearGradient } from "expo-linear-gradient";
import { C, RADIUS } from "@/src/theme";
import { api } from "@/src/api";

export default function ResetPassword() {
  const router = useRouter();
  const params = useLocalSearchParams<{ token?: string }>();
  const [token, setToken] = useState<string>("");
  const [pw1, setPw1] = useState("");
  const [pw2, setPw2] = useState("");
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    // Pull token from query params (web) or URL fragment
    let t = (params?.token as string) || "";
    if (!t && Platform.OS === "web" && typeof window !== "undefined") {
      const u = new URL(window.location.href);
      t = u.searchParams.get("token") || "";
    }
    setToken(t);
  }, [params]);

  const onSubmit = async () => {
    setErr(null);
    if (!token) { setErr("Reset link missing. Please use the link from your email."); return; }
    if (pw1.length < 6) { setErr("Password must be at least 6 characters."); return; }
    if (pw1 !== pw2)    { setErr("Passwords do not match."); return; }
    setLoading(true);
    try {
      await api.post("/auth/reset-password", { token, new_password: pw1 });
      setDone(true);
    } catch (e: any) {
      setErr(e?.message || "Could not reset password.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.root}>
      <LinearGradient pointerEvents="none" colors={["rgba(255,176,0,0.18)", "transparent"]} style={styles.glow} />
      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === "ios" ? "padding" : undefined}>
        <View style={styles.wrap}>
          {!done ? (
            <>
              <View style={styles.iconWrap}><Ionicons name="lock-closed" size={28} color={C.brand} /></View>
              <Text style={styles.kicker}>NEW PASSWORD</Text>
              <Text style={styles.h1}>Choose a new{"\n"}password</Text>
              <Text style={styles.sub}>
                Pick something at least 6 characters. We&apos;ll sign you in right after.
              </Text>

              <View style={styles.field}>
                <Text style={styles.label}>New password</Text>
                <TextInput
                  testID="rp-new"
                  value={pw1}
                  onChangeText={setPw1}
                  secureTextEntry
                  placeholder="6+ characters"
                  placeholderTextColor={C.textMuted}
                  style={styles.input}
                />
              </View>

              <View style={styles.field}>
                <Text style={styles.label}>Confirm new password</Text>
                <TextInput
                  testID="rp-confirm"
                  value={pw2}
                  onChangeText={setPw2}
                  secureTextEntry
                  placeholder="Re-enter password"
                  placeholderTextColor={C.textMuted}
                  style={styles.input}
                />
              </View>

              {err && <Text style={styles.err} testID="rp-err">{err}</Text>}

              <Pressable testID="rp-submit" onPress={onSubmit} disabled={loading} style={[styles.btn, loading && { opacity: 0.6 }]}>
                {loading ? <ActivityIndicator color="#000" /> : (
                  <>
                    <Text style={styles.btnText}>Reset password</Text>
                    <Ionicons name="checkmark" size={18} color="#000" />
                  </>
                )}
              </Pressable>
            </>
          ) : (
            <View testID="rp-done">
              <View style={[styles.iconWrap, { backgroundColor: C.brand }]}>
                <Ionicons name="checkmark" size={28} color="#000" />
              </View>
              <Text style={styles.kicker}>ALL SET</Text>
              <Text style={styles.h1}>Password{"\n"}updated ✨</Text>
              <Text style={styles.sub}>
                You can now sign in with your new password.
              </Text>
              <Pressable testID="rp-go-login" onPress={() => router.replace("/login")} style={styles.btn}>
                <Text style={styles.btnText}>Sign in</Text>
                <Ionicons name="arrow-forward" size={18} color="#000" />
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
  wrap: { padding: 24, flex: 1, justifyContent: "center", maxWidth: 480, width: "100%", alignSelf: "center" },
  iconWrap: { width: 60, height: 60, borderRadius: 30, backgroundColor: C.brandDim, alignItems: "center", justifyContent: "center", marginBottom: 18 },
  kicker: { fontSize: 11, fontWeight: "800", letterSpacing: 3, color: C.brand },
  h1: { fontSize: 34, fontWeight: "900", color: C.text, marginTop: 8, letterSpacing: -0.8, lineHeight: 40 },
  sub: { fontSize: 15, color: C.textDim, marginTop: 16, marginBottom: 28, lineHeight: 22 },
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
