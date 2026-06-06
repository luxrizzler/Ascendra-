import { useEffect, useState } from "react";
import { View, Text, StyleSheet, Pressable, ActivityIndicator } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useLocalSearchParams, useRouter, Stack } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { C, RADIUS } from "@/src/theme";
import { api } from "@/src/api";
import { useAuth } from "@/src/context/AuthContext";

export default function CheckoutSuccess() {
  const { session_id } = useLocalSearchParams<{ session_id?: string }>();
  const router = useRouter();
  const { refresh } = useAuth();
  const [status, setStatus] = useState<"checking" | "paid" | "pending" | "error">("checking");
  const [tier, setTier] = useState<string | null>(null);
  const [attempts, setAttempts] = useState(0);

  useEffect(() => {
    if (!session_id) {
      setStatus("error");
      return;
    }
    let stopped = false;
    const poll = async () => {
      try {
        const r = await api.get(`/billing/status/${session_id}`);
        setTier(r.tier);
        if (r.status === "paid") {
          setStatus("paid");
          await refresh();
          return;
        }
        if (attempts < 8 && !stopped) {
          setTimeout(() => setAttempts((a) => a + 1), 1500);
        } else {
          setStatus("pending");
        }
      } catch {
        setStatus("error");
      }
    };
    poll();
    return () => { stopped = true; };
  }, [session_id, attempts, refresh]);

  return (
    <SafeAreaView style={styles.root}>
      <Stack.Screen options={{ headerShown: false }} />
      <View style={styles.wrap}>
        {status === "checking" && (
          <>
            <ActivityIndicator color={C.brand} size="large" />
            <Text style={styles.title}>Confirming your payment…</Text>
            <Text style={styles.sub}>Hold tight — just a sec.</Text>
          </>
        )}
        {status === "paid" && (
          <>
            <View style={styles.iconWrap}>
              <Ionicons name="checkmark-circle" size={88} color={C.success} />
            </View>
            <Text style={styles.title}>Welcome to {tier?.toUpperCase()}!</Text>
            <Text style={styles.sub}>Everything is unlocked. Let&apos;s build.</Text>
            <Pressable testID="success-continue-btn" onPress={() => router.replace("/(tabs)/home")} style={styles.primaryBtn}>
              <Text style={styles.primaryBtnText}>Start learning</Text>
              <Ionicons name="arrow-forward" size={18} color="#000" />
            </Pressable>
          </>
        )}
        {status === "pending" && (
          <>
            <Ionicons name="time-outline" size={64} color={C.brand} />
            <Text style={styles.title}>Almost there</Text>
            <Text style={styles.sub}>Your payment is processing. We&apos;ll unlock features as soon as it clears.</Text>
            <Pressable onPress={() => router.replace("/(tabs)/home")} style={styles.primaryBtn}>
              <Text style={styles.primaryBtnText}>Go to home</Text>
            </Pressable>
          </>
        )}
        {status === "error" && (
          <>
            <Ionicons name="alert-circle-outline" size={64} color={C.danger} />
            <Text style={styles.title}>Something went wrong</Text>
            <Text style={styles.sub}>We couldn&apos;t confirm your session. Try again from the pricing screen.</Text>
            <Pressable onPress={() => router.replace("/pricing")} style={styles.primaryBtn}>
              <Text style={styles.primaryBtnText}>Back to pricing</Text>
            </Pressable>
          </>
        )}
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  wrap: { flex: 1, alignItems: "center", justifyContent: "center", padding: 24, gap: 14 },
  iconWrap: { marginBottom: 8 },
  title: { color: C.text, fontWeight: "900", fontSize: 28, letterSpacing: -0.8, textAlign: "center" },
  sub: { color: C.textDim, fontSize: 15, textAlign: "center", marginTop: 4 },
  primaryBtn: {
    marginTop: 24, backgroundColor: C.brand, paddingHorizontal: 28, paddingVertical: 14,
    borderRadius: RADIUS.lg, flexDirection: "row", alignItems: "center", gap: 8,
  },
  primaryBtnText: { color: "#000", fontWeight: "800", fontSize: 16 },
});
