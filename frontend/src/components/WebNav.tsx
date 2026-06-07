// Persistent Ascendra top nav — appears on web for every screen so the brand
// identity feels consistent with the landing page. On native mobile we hide it
// so each screen's native back/header takes over.
import { View, Text, StyleSheet, Pressable, Platform, useWindowDimensions } from "react-native";
import { useRouter, usePathname } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { C, RADIUS } from "@/src/theme";
import { useAuth } from "@/src/context/AuthContext";

export function WebNav({ variant = "auto" }: { variant?: "auto" | "marketing" | "app" }) {
  const router = useRouter();
  const pathname = usePathname() || "";
  const { width } = useWindowDimensions();
  const { user } = useAuth();
  const compact = width < 720;

  // Only render on web — preserves native UX on real devices
  if (Platform.OS !== "web") return null;
  // Hide on landing (which already has its own nav baked in)
  if (pathname === "/landing" || pathname === "/") return null;

  const isAuthed = !!user;

  const goHome = () => router.push(isAuthed ? "/(tabs)/home" : "/landing");
  const onCTA  = () => router.push(isAuthed ? "/(tabs)/home" : "/onboarding");
  const onSignIn = () => router.push("/login");

  return (
    <View style={styles.bar}>
      <View style={styles.inner}>
        {/* Brand */}
        <Pressable testID="webnav-brand" onPress={goHome} style={styles.brandRow}>
          <View style={styles.brandLogo}>
            <Ionicons name="sparkles" size={14} color="#000" />
          </View>
          <Text style={styles.brandText}>ASCENDRA</Text>
        </Pressable>

        {/* Right side */}
        <View style={styles.rightRow}>
          {!compact && (
            <Pressable onPress={() => router.push("/landing")} style={styles.linkBtn}>
              <Text style={styles.link}>Home</Text>
            </Pressable>
          )}
          {!compact && (
            <Pressable onPress={() => router.push("/pricing")} style={styles.linkBtn}>
              <Text style={styles.link}>Pricing</Text>
            </Pressable>
          )}
          {isAuthed ? (
            <>
              {!compact && (
                <Pressable onPress={() => router.push("/(tabs)/tutor")} style={styles.linkBtn}>
                  <Text style={styles.link}>AI Tutor</Text>
                </Pressable>
              )}
              <Pressable testID="webnav-app" onPress={onCTA} style={styles.cta}>
                <Text style={styles.ctaText}>{compact ? "App" : "Open app"}</Text>
              </Pressable>
            </>
          ) : (
            <>
              <Pressable testID="webnav-signin" onPress={onSignIn} style={styles.linkBtn}>
                <Text style={styles.link}>Sign in</Text>
              </Pressable>
              <Pressable testID="webnav-cta" onPress={onCTA} style={styles.cta}>
                <Text style={styles.ctaText}>{compact ? "Start" : "Start free"}</Text>
              </Pressable>
            </>
          )}
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  bar: {
    width: "100%",
    backgroundColor: "rgba(10, 4, 19, 0.92)",
    borderBottomWidth: 1,
    borderBottomColor: C.border,
    // @ts-ignore web-only fields
    backdropFilter: "saturate(180%) blur(8px)",
    // @ts-ignore
    WebkitBackdropFilter: "saturate(180%) blur(8px)",
    zIndex: 100,
  },
  inner: {
    width: "100%",
    maxWidth: 1200,
    marginHorizontal: "auto",
    paddingHorizontal: 20,
    paddingVertical: 14,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  brandRow: { flexDirection: "row", alignItems: "center", gap: 10 },
  brandLogo: {
    width: 24, height: 24, borderRadius: 6, backgroundColor: C.brand,
    alignItems: "center", justifyContent: "center",
  },
  brandText: { color: C.text, fontWeight: "900", fontSize: 13, letterSpacing: 4 },
  rightRow: { flexDirection: "row", alignItems: "center", gap: 8 },
  linkBtn: { paddingHorizontal: 10, paddingVertical: 6 },
  link: { color: C.textDim, fontSize: 14, fontWeight: "600" },
  cta: {
    backgroundColor: C.brand,
    paddingHorizontal: 16, paddingVertical: 9,
    borderRadius: RADIUS.pill,
    marginLeft: 4,
  },
  ctaText: { color: "#000", fontWeight: "800", fontSize: 13, letterSpacing: 0.3 },
});

// Optional gold-tinted glow background reused across screens so they feel
// connected to the landing hero.
export function BrandGlow() {
  return (
    <View pointerEvents="none" style={glowStyles.wrap}>
      <View style={glowStyles.gold} />
      <View style={glowStyles.violet} />
    </View>
  );
}

const glowStyles = StyleSheet.create({
  wrap: {
    position: "absolute",
    top: 0, left: 0, right: 0, height: 480,
    overflow: "hidden",
    zIndex: -1,
  },
  gold: {
    position: "absolute",
    top: -180, right: -120, width: 460, height: 460, borderRadius: 460,
    backgroundColor: "rgba(255,176,0,0.12)",
    // @ts-ignore
    filter: "blur(80px)",
  },
  violet: {
    position: "absolute",
    top: -120, left: -160, width: 520, height: 520, borderRadius: 520,
    backgroundColor: "rgba(124,58,237,0.18)",
    // @ts-ignore
    filter: "blur(90px)",
  },
});
