// Web-only OAuth landing route. The Emergent auth server redirects here with
// either `#session_id=...` or `?session_id=...` in the URL.
import { useEffect, useState } from "react";
import { View, Text, StyleSheet, Pressable, ActivityIndicator } from "react-native";
import { useRouter, Stack } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { C, RADIUS } from "@/src/theme";
import { useAuth } from "@/src/context/AuthContext";
import { parseSessionId, exchangeSessionIdForToken } from "@/src/auth/google";
import { storage } from "@/src/utils/storage";

const PENDING_GOAL_KEY = "lume_pending_goal";

export default function AuthCallback() {
  const router = useRouter();
  const { loginWithGoogleToken } = useAuth();
  const [status, setStatus] = useState<"loading" | "error">("loading");
  const [err, setErr] = useState<string>("");

  useEffect(() => {
    (async () => {
      try {
        if (typeof window === "undefined") {
          setStatus("error");
          setErr("Auth flow not supported in this environment.");
          return;
        }
        const full = window.location.href;
        const sid = parseSessionId(full);
        if (!sid) {
          setStatus("error");
          setErr("Missing session_id in callback URL.");
          return;
        }
        // Clean URL fragment immediately
        window.history.replaceState(null, "", window.location.pathname);

        const data = await exchangeSessionIdForToken(sid);
        const pendingGoal = await storage.getItem(PENDING_GOAL_KEY, "");
        await loginWithGoogleToken(data.session_token, pendingGoal || undefined);
        if (pendingGoal) await storage.removeItem(PENDING_GOAL_KEY);
        router.replace("/(tabs)/home");
      } catch (e: any) {
        setStatus("error");
        setErr(e?.message || "Authentication failed.");
      }
    })();
  }, [loginWithGoogleToken, router]);

  return (
    <View style={styles.root}>
      <Stack.Screen options={{ headerShown: false }} />
      {status === "loading" ? (
        <>
          <ActivityIndicator color={C.brand} size="large" />
          <Text style={styles.title}>Finishing sign-in…</Text>
          <Text style={styles.sub}>Welcome back. One sec.</Text>
        </>
      ) : (
        <>
          <Ionicons name="alert-circle-outline" size={56} color={C.danger} />
          <Text style={styles.title}>We couldn&apos;t sign you in</Text>
          <Text style={styles.sub}>{err}</Text>
          <Pressable testID="auth-error-back" onPress={() => router.replace("/onboarding")} style={styles.btn}>
            <Text style={styles.btnText}>Try again</Text>
          </Pressable>
        </>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg, alignItems: "center", justifyContent: "center", padding: 24, gap: 14 },
  title: { color: C.text, fontWeight: "900", fontSize: 24, marginTop: 8 },
  sub: { color: C.textDim, fontSize: 14, textAlign: "center" },
  btn: { backgroundColor: C.brand, paddingHorizontal: 28, paddingVertical: 14, borderRadius: RADIUS.lg, marginTop: 16 },
  btnText: { color: "#000", fontWeight: "800", fontSize: 15 },
});
