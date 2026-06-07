// Shared web footer — appears below every web page (excluding landing,
// which has its own larger footer baked in).
import { View, Text, StyleSheet, Pressable, Platform, useWindowDimensions } from "react-native";
import { useRouter, usePathname } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { C } from "@/src/theme";

export function WebFooter() {
  const router = useRouter();
  const pathname = usePathname() || "";
  const { width } = useWindowDimensions();
  const compact = width < 720;

  if (Platform.OS !== "web") return null;
  // Landing already has its own custom footer; skip there
  if (pathname === "/landing" || pathname === "/") return null;

  return (
    <View style={styles.footer}>
      <View style={[styles.inner, compact && { flexDirection: "column", gap: 18 }]}>
        <View style={styles.brandRow}>
          <View style={styles.brandLogo}><Ionicons name="sparkles" size={12} color="#000" /></View>
          <View>
            <Text style={styles.brandText}>ASCENDRA</Text>
            <Text style={styles.tagline}>AI-powered learning · Boundless growth</Text>
          </View>
        </View>

        <View style={[styles.linksRow, compact && { flexWrap: "wrap", justifyContent: "flex-start" }]}>
          <Pressable onPress={() => router.push("/landing")} style={styles.linkBtn}>
            <Text style={styles.link}>Home</Text>
          </Pressable>
          <Pressable onPress={() => router.push("/pricing")} style={styles.linkBtn}>
            <Text style={styles.link}>Pricing</Text>
          </Pressable>
          <Pressable onPress={() => router.push("/onboarding")} style={styles.linkBtn}>
            <Text style={styles.link}>Start free</Text>
          </Pressable>
          <Pressable onPress={() => router.push("/login")} style={styles.linkBtn}>
            <Text style={styles.link}>Sign in</Text>
          </Pressable>
        </View>
      </View>
      <Text style={styles.copy}>© 2026 Ascendra Academy · The path is yours to climb.</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  footer: {
    width: "100%",
    paddingTop: 28, paddingBottom: 22,
    paddingHorizontal: 20,
    borderTopWidth: 1, borderTopColor: C.border,
    backgroundColor: "rgba(10, 4, 19, 0.7)",
    marginTop: 40,
  },
  inner: {
    width: "100%", maxWidth: 1200, marginHorizontal: "auto",
    flexDirection: "row", alignItems: "center", justifyContent: "space-between",
  },
  brandRow: { flexDirection: "row", alignItems: "center", gap: 12 },
  brandLogo: {
    width: 22, height: 22, borderRadius: 5, backgroundColor: C.brand,
    alignItems: "center", justifyContent: "center",
  },
  brandText: { color: C.text, fontWeight: "900", fontSize: 12, letterSpacing: 4 },
  tagline: { color: C.textMuted, fontSize: 10, fontStyle: "italic", marginTop: 2 },
  linksRow: { flexDirection: "row", alignItems: "center", gap: 4 },
  linkBtn: { paddingHorizontal: 10, paddingVertical: 4 },
  link: { color: C.textDim, fontSize: 13, fontWeight: "500" },
  copy: { color: C.textMuted, fontSize: 10, textAlign: "center", marginTop: 18 },
});
