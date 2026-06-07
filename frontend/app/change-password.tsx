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
import { useAuth } from "@/src/context/AuthContext";

export default function ChangePassword() {
  const router = useRouter();
  const { user, refresh } = useAuth();
  const forced = !!user?.must_change_password;

  const [current, setCurrent] = useState("");
  const [pw1, setPw1] = useState("");
  const [pw2, setPw2] = useState("");
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const onSubmit = async () => {
    setErr(null);
    if (pw1.length < 6) { setErr("Password must be at least 6 characters."); return; }
    if (pw1 !== pw2)    { setErr("Passwords do not match."); return; }
    if (!forced && !current) { setErr("Current password is required."); return; }
    setLoading(true);
    try {
      await api.post("/auth/change-password", {
        current_password: forced ? undefined : current,
        new_password: pw1,
      });
      await refresh();
      router.replace(user?.is_admin ? "/admin" : "/(tabs)/home");
    } catch (e: any) {
      setErr(e?.message || "Could not update password.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.root}>
      <LinearGradient pointerEvents="none" colors={["rgba(255,176,0,0.18)", "transparent"]} style={styles.glow} />
      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === "ios" ? "padding" : undefined}>
        <View style={styles.wrap}>
          <View style={styles.iconWrap}><Ionicons name="lock-closed" size={28} color={C.brand} /></View>
          <Text style={styles.kicker}>{forced ? "ONE MORE STEP" : "ACCOUNT SECURITY"}</Text>
          <Text style={styles.h1}>{forced ? "Set your password" : "Change password"}</Text>
          <Text style={styles.sub}>
            {forced
              ? "Welcome to Ascendra. Please choose a new password to secure your account."
              : "Choose a new password. Use at least 6 characters."}
          </Text>

          {!forced && (
            <View style={styles.field}>
              <Text style={styles.label}>Current password</Text>
              <TextInput
                testID="cp-current"
                value={current}
                onChangeText={setCurrent}
                secureTextEntry
                placeholder="••••••••"
                placeholderTextColor={C.textMuted}
                style={styles.input}
              />
            </View>
          )}

          <View style={styles.field}>
            <Text style={styles.label}>New password</Text>
            <TextInput
              testID="cp-new"
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
              testID="cp-confirm"
              value={pw2}
              onChangeText={setPw2}
              secureTextEntry
              placeholder="Re-enter password"
              placeholderTextColor={C.textMuted}
              style={styles.input}
            />
          </View>

          {err && <Text style={styles.err} testID="cp-err">{err}</Text>}

          <Pressable testID="cp-submit" onPress={onSubmit} disabled={loading} style={[styles.btn, loading && { opacity: 0.6 }]}>
            {loading ? <ActivityIndicator color="#000" /> : (
              <>
                <Text style={styles.btnText}>Save password</Text>
                <Ionicons name="arrow-forward" size={18} color="#000" />
              </>
            )}
          </Pressable>

          {!forced && (
            <Pressable testID="cp-cancel" onPress={() => router.back()} style={{ marginTop: 16, alignItems: "center" }}>
              <Text style={{ color: C.textDim }}>Cancel</Text>
            </Pressable>
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
  iconWrap: { width: 60, height: 60, borderRadius: 30, backgroundColor: C.brandDim, alignItems: "center", justifyContent: "center", marginBottom: 16 },
  kicker: { fontSize: 11, fontWeight: "800", letterSpacing: 3, color: C.brand },
  h1: { fontSize: 30, fontWeight: "900", color: C.text, marginTop: 8, letterSpacing: -0.8 },
  sub: { fontSize: 15, color: C.textDim, marginTop: 10, marginBottom: 28, lineHeight: 22 },
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
