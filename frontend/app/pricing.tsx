import { useEffect, useState } from "react";
import { View, Text, StyleSheet, ScrollView, Pressable, ActivityIndicator, Platform, Linking } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useRouter, Stack } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { C, RADIUS } from "@/src/theme";
import { api, BACKEND_URL } from "@/src/api";
import { useAuth } from "@/src/context/AuthContext";

type Tier = {
  id: "free" | "pro" | "business";
  name: string; price_monthly: number; blurb: string; features: string[]; highlight?: boolean;
};

export default function Pricing() {
  const router = useRouter();
  const { user, refresh } = useAuth();
  const [tiers, setTiers] = useState<Tier[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api.get("/pricing").then((r) => setTiers(r.tiers)).finally(() => setLoading(false));
  }, []);

  const startCheckout = async (tier: "pro" | "business") => {
    if (!user) {
      router.push("/login");
      return;
    }
    setBusy(tier);
    setErr(null);
    try {
      const origin = Platform.OS === "web"
        ? (typeof window !== "undefined" ? window.location.origin : BACKEND_URL!)
        : BACKEND_URL!;
      const { url } = await api.post("/billing/checkout", { tier, origin_url: origin });
      if (Platform.OS === "web") {
        window.location.href = url;
      } else {
        await Linking.openURL(url);
      }
    } catch (e: any) {
      setErr(e.message || "Could not start checkout");
    } finally {
      setBusy(null);
      setTimeout(refresh, 800);
    }
  };

  if (loading) {
    return (
      <View style={[styles.root, { alignItems: "center", justifyContent: "center" }]}>
        <ActivityIndicator color={C.brand} />
      </View>
    );
  }

  return (
    <SafeAreaView style={styles.root}>
      <Stack.Screen options={{ headerShown: false }} />
      <View style={styles.headerRow}>
        <Pressable testID="pricing-back-btn" onPress={() => router.back()} style={styles.back}>
          <Ionicons name="chevron-back" size={24} color={C.text} />
        </Pressable>
        <Text style={styles.headerTitle}>Pricing</Text>
        <View style={{ width: 40 }} />
      </View>

      <ScrollView contentContainerStyle={styles.scroll}>
        <Text style={styles.kicker}>PLANS</Text>
        <Text style={styles.h1}>Learn AI like the top 1%.</Text>
        <Text style={styles.sub}>Cancel anytime. 7-day money-back guarantee.</Text>

        {err && <Text style={styles.error} testID="pricing-error">{err}</Text>}

        <View style={{ height: 24 }} />

        {tiers.map((t) => {
          const isCurrent = user?.tier === t.id;
          return (
            <View
              key={t.id}
              testID={`tier-card-${t.id}`}
              style={[
                styles.card,
                t.highlight && styles.cardHighlight,
                isCurrent && { borderColor: C.success },
              ]}
            >
              {t.highlight && (
                <View style={styles.badge}>
                  <Text style={styles.badgeText}>MOST POPULAR</Text>
                </View>
              )}
              {isCurrent && (
                <View style={[styles.badge, { backgroundColor: C.success }]}>
                  <Text style={[styles.badgeText, { color: "#000" }]}>CURRENT PLAN</Text>
                </View>
              )}
              <Text style={styles.tierName}>{t.name}</Text>
              <View style={styles.priceRow}>
                <Text style={styles.price}>${t.price_monthly}</Text>
                {t.price_monthly > 0 && <Text style={styles.priceUnit}>/ month</Text>}
              </View>
              <Text style={styles.blurb}>{t.blurb}</Text>

              <View style={{ height: 16 }} />
              {t.features.map((f, i) => (
                <View key={i} style={styles.featureRow}>
                  <Ionicons name="checkmark-circle" size={18} color={t.highlight ? C.brand : C.success} />
                  <Text style={styles.featureText}>{f}</Text>
                </View>
              ))}

              {t.id !== "free" && !isCurrent && (
                <Pressable
                  testID={`tier-cta-${t.id}`}
                  onPress={() => startCheckout(t.id as "pro" | "business")}
                  disabled={busy === t.id}
                  style={[
                    styles.ctaBtn,
                    t.highlight ? { backgroundColor: C.brand } : { backgroundColor: C.surface2, borderWidth: 1, borderColor: C.borderStrong },
                    busy === t.id && { opacity: 0.6 },
                  ]}
                >
                  {busy === t.id ? (
                    <ActivityIndicator color={t.highlight ? "#000" : C.text} />
                  ) : (
                    <>
                      <Text style={[styles.ctaText, t.highlight ? { color: "#000" } : { color: C.text }]}>
                        Upgrade to {t.name}
                      </Text>
                      <Ionicons name="arrow-forward" size={16} color={t.highlight ? "#000" : C.text} />
                    </>
                  )}
                </Pressable>
              )}
              {t.id === "free" && !isCurrent && (
                <View style={[styles.ctaBtn, { backgroundColor: C.surface2 }]}>
                  <Text style={[styles.ctaText, { color: C.textDim }]}>You start here</Text>
                </View>
              )}
            </View>
          );
        })}

        <View style={styles.faqBox}>
          <Text style={styles.faqTitle}>Why upgrade?</Text>
          <Text style={styles.faqText}>
            Pro unlocks all 4 paths and unlimited AI Tutor chat with Claude Sonnet 4.5. Business adds a monthly strategy call and a private community of AI-first builders.
          </Text>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  headerRow: { flexDirection: "row", alignItems: "center", paddingHorizontal: 12, paddingVertical: 8 },
  back: { width: 40, height: 40, alignItems: "center", justifyContent: "center" },
  headerTitle: { color: C.text, fontWeight: "800", fontSize: 16, flex: 1, textAlign: "center" },
  scroll: { padding: 20, paddingBottom: 60 },
  kicker: { fontSize: 11, fontWeight: "800", letterSpacing: 3, color: C.brand, marginBottom: 8 },
  h1: { color: C.text, fontSize: 32, fontWeight: "900", letterSpacing: -1 },
  sub: { color: C.textDim, fontSize: 14, marginTop: 8 },
  card: { padding: 24, backgroundColor: C.surface, borderRadius: RADIUS.xl, borderWidth: 1, borderColor: C.border, marginBottom: 14, position: "relative" },
  cardHighlight: { borderColor: C.brand, backgroundColor: "rgba(255,176,0,0.04)" },
  badge: { position: "absolute", top: -10, left: 24, backgroundColor: C.brand, paddingHorizontal: 10, paddingVertical: 4, borderRadius: RADIUS.pill },
  badgeText: { color: "#000", fontWeight: "900", fontSize: 10, letterSpacing: 1.5 },
  tierName: { color: C.text, fontWeight: "900", fontSize: 22 },
  priceRow: { flexDirection: "row", alignItems: "flex-end", gap: 6, marginTop: 8 },
  price: { color: C.text, fontWeight: "900", fontSize: 38, letterSpacing: -1.5 },
  priceUnit: { color: C.textDim, fontSize: 14, paddingBottom: 8 },
  blurb: { color: C.textDim, fontSize: 14, marginTop: 6 },
  featureRow: { flexDirection: "row", alignItems: "center", gap: 10, marginVertical: 5 },
  featureText: { color: C.textDim, fontSize: 14, flex: 1 },
  ctaBtn: {
    marginTop: 20, paddingVertical: 14, borderRadius: RADIUS.lg, alignItems: "center",
    flexDirection: "row", justifyContent: "center", gap: 8,
  },
  ctaText: { fontWeight: "800", fontSize: 15 },
  error: { color: C.danger, marginTop: 16, fontSize: 14 },
  faqBox: { marginTop: 16, padding: 18, backgroundColor: C.surface, borderRadius: RADIUS.lg, borderWidth: 1, borderColor: C.border },
  faqTitle: { color: C.text, fontWeight: "800", fontSize: 15 },
  faqText: { color: C.textDim, fontSize: 13, lineHeight: 20, marginTop: 8 },
});
