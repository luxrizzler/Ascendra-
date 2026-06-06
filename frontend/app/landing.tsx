// Ascendra landing page — full-bleed brand hero artwork.
// The hero image already contains the wordmark + tagline; we just frame it.
import { useEffect, useState } from "react";
import {
  View, Text, StyleSheet, ScrollView, Pressable, Image, useWindowDimensions, Platform,
} from "react-native";
import { useRouter, Stack } from "expo-router";
import { LinearGradient } from "expo-linear-gradient";
import { Ionicons } from "@expo/vector-icons";
import { C, RADIUS } from "@/src/theme";
import { api } from "@/src/api";

const HERO_IMG =
  "https://customer-assets.emergentagent.com/job_ai-business-academy-2/artifacts/c1jkvwwp_4185C05A-6A9A-42F7-A146-9109CF6F03DD.png";
const BRAND_BOARD_IMG =
  "https://customer-assets.emergentagent.com/job_ai-business-academy-2/artifacts/4t1z9aty_5283CA9A-0F48-41D7-918A-E177AC8EC40A.png";

const SYMBOLISM = [
  { icon: "trending-up",  title: "Rise",          body: "Ascending to your highest potential." },
  { icon: "sunny",        title: "Light",         body: "Knowledge that illuminates." },
  { icon: "infinite",     title: "Transformation",body: "Continuous growth and becoming." },
  { icon: "compass",      title: "Guidance",      body: "AI-powered guidance every step." },
];

const PILLARS = [
  { icon: "sparkles",   title: "AI-Personalized",  body: "Learning paths tailored to your goals, pace, and style." },
  { icon: "rocket",     title: "Real-World Skills",body: "Practical knowledge for real impact. Not theory." },
  { icon: "trending-up",title: "Track & Grow",     body: "See your progress. Celebrate your wins. Build the streak." },
  { icon: "people",     title: "Expert Guidance",  body: "Learn from industry leaders and your AI tutor, 24/7." },
];

export default function Landing() {
  const router = useRouter();
  const { width } = useWindowDimensions();
  const isDesktop = width >= 900;
  const [tiers, setTiers] = useState<any[]>([]);

  useEffect(() => {
    api.get("/pricing").then((r) => setTiers(r.tiers)).catch(() => {});
  }, []);

  const onCTA = () => router.push("/onboarding");
  const onSignIn = () => router.push("/login");

  return (
    <View style={styles.root}>
      <Stack.Screen options={{ headerShown: false, title: "Ascendra" }} />

      {/* Nav */}
      <View style={styles.nav}>
        <View style={styles.navInner}>
          <View style={styles.brandRow}>
            <View style={styles.brandLogo}><Ionicons name="sparkles" size={14} color="#000" /></View>
            <Text style={styles.brandText}>ASCENDRA</Text>
          </View>
          <View style={{ flexDirection: "row", alignItems: "center", gap: 16 }}>
            <Pressable testID="nav-signin-btn" onPress={onSignIn}>
              <Text style={styles.navLink}>Sign in</Text>
            </Pressable>
            <Pressable testID="nav-cta-btn" onPress={onCTA} style={styles.navCta}>
              <Text style={styles.navCtaText}>Start free</Text>
            </Pressable>
          </View>
        </View>
      </View>

      <ScrollView contentContainerStyle={{ paddingBottom: 60 }}>
        {/* ─── HERO — split: angel artwork left, brand copy right ─── */}
        <View style={[styles.hero, isDesktop ? styles.heroDesktop : styles.heroMobile]}>
          {/* LEFT: angel image (cropped from brand board) */}
          <View style={[styles.heroLeft, isDesktop ? { width: "46%", height: "100%" } : { width: "100%", height: 420 }]}>
            <View style={styles.heroImageClip}>
              <Image
                source={{ uri: HERO_IMG }}
                style={styles.heroImageCrop}
                resizeMode="cover"
              />
            </View>
            {/* Right-edge fade so it bleeds into the dark side */}
            <LinearGradient
              colors={["rgba(7,11,31,0)", "rgba(7,11,31,0.0)", "rgba(7,11,31,0.95)"]}
              start={{ x: 0, y: 0.5 }} end={{ x: 1, y: 0.5 }}
              style={StyleSheet.absoluteFillObject}
              pointerEvents="none"
            />
          </View>

          {/* RIGHT: brand copy */}
          <View style={[styles.heroRight, isDesktop ? { width: "54%", paddingHorizontal: 60, paddingVertical: 80 } : { width: "100%", paddingHorizontal: 24, paddingVertical: 48 }]}>
            {/* Subtle cosmic glow behind text */}
            <LinearGradient
              colors={["rgba(124,58,237,0.18)", "rgba(7,11,31,0)"]}
              style={[StyleSheet.absoluteFillObject, { opacity: 0.6 }]}
              pointerEvents="none"
            />
            <Text style={styles.heroBrand}>ASCENDRA</Text>
            <View style={styles.heroDivider} />
            <Text style={styles.heroKicker}>AI-POWERED LEARNING · BOUNDLESS GROWTH</Text>
            <Text style={[styles.heroH1, { fontSize: isDesktop ? 64 : 44 }]}>
              Ready to{"\n"}<Text style={styles.heroH1Gold}>rise today?</Text>
            </Text>
            <Text style={[styles.heroSub, { maxWidth: 520 }]}>
              The AI learning partner that walks beside you — from your first prompt to your first launch.
              Beginner to advanced, taught through every model that matters in 2026.
            </Text>
            <View style={styles.heroCtas}>
              <Pressable testID="hero-cta-btn" onPress={onCTA} style={styles.primaryBtn}>
                <Text style={styles.primaryBtnText}>Begin your ascent</Text>
                <Ionicons name="arrow-forward" size={18} color="#000" />
              </Pressable>
              <Pressable onPress={() => router.push("/pricing")} style={styles.secondaryBtn}>
                <Text style={styles.secondaryBtnText}>See pricing</Text>
              </Pressable>
            </View>
          </View>
        </View>

        {/* ─── MISSION ─── */}
        <View style={[styles.missionSection, { paddingHorizontal: isDesktop ? 60 : 24 }]}>
          <View style={[styles.missionCard, { maxWidth: 900 }]}>
            <LinearGradient
              colors={["rgba(124,58,237,0.20)", "rgba(255,176,0,0.06)"]}
              start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }}
              style={StyleSheet.absoluteFillObject}
            />
            <Text style={styles.missionLabel}>OUR MISSION</Text>
            <Text style={[styles.missionText, { fontSize: isDesktop ? 30 : 22 }]}>
              To <Text style={{ color: C.brand }}>empower</Text> every learner to{" "}
              <Text style={{ color: C.brand, fontStyle: "italic" }}>rise beyond limits</Text>{" "}
              through AI-driven education and human potential.
            </Text>
          </View>
        </View>

        {/* ─── MODELS STRIP ─── */}
        <View style={styles.modelsStrip}>
          <Text style={styles.modelsStripLabel}>COVERING THE MODELS THAT MATTER</Text>
          <View style={styles.modelsStripRow}>
            {["GPT-5.2", "Claude 4.5", "Gemini 3", "Nano Banana", "Sora 2", "ElevenLabs", "Perplexity", "Midjourney", "Veo 3", "Whisper", "Cursor"].map((m) => (
              <View key={m} style={styles.modelChip}>
                <Text style={styles.modelChipText}>{m}</Text>
              </View>
            ))}
          </View>
        </View>

        {/* ─── PILLARS (Built for your rise) ─── */}
        <Section title="BUILT FOR YOUR RISE" h1="Everything you need to ascend." isDesktop={isDesktop}>
          <View style={[styles.grid, { gap: 16 }]}>
            {PILLARS.map((p) => (
              <View key={p.title} style={[styles.pillarCard, { flexBasis: isDesktop ? "23%" : "100%" }]}>
                <View style={styles.pillarIcon}>
                  <Ionicons name={p.icon as any} size={24} color={C.brand} />
                </View>
                <Text style={styles.pillarTitle}>{p.title}</Text>
                <Text style={styles.pillarBody}>{p.body}</Text>
              </View>
            ))}
          </View>
        </Section>

        {/* ─── SYMBOLISM (the name means) ─── */}
        <Section title="THE NAME MEANS" h1="Rise. Light. Transformation. Guidance." isDesktop={isDesktop}>
          <View style={[styles.grid, { gap: 16 }]}>
            {SYMBOLISM.map((s) => (
              <View key={s.title} style={[styles.symbolCard, { flexBasis: isDesktop ? "23%" : "100%" }]}>
                <View style={styles.symbolIcon}>
                  <Ionicons name={s.icon as any} size={26} color={C.brand} />
                </View>
                <Text style={styles.symbolTitle}>{s.title}</Text>
                <Text style={styles.symbolBody}>{s.body}</Text>
              </View>
            ))}
          </View>
        </Section>

        {/* ─── PRICING ─── */}
        <Section title="PRICING" h1="Start free. Rise on your terms." isDesktop={isDesktop}>
          <View style={[styles.grid, { gap: 16 }]}>
            {tiers.map((t) => (
              <View
                key={t.id}
                testID={`landing-tier-card-${t.id}`}
                style={[
                  styles.tierCard,
                  { flexBasis: isDesktop ? "31%" : "100%" },
                  t.highlight && styles.tierHighlight,
                ]}
              >
                {t.highlight && <View style={styles.tierBadge}><Text style={styles.tierBadgeText}>MOST POPULAR</Text></View>}
                <Text style={styles.tierName}>{t.name}</Text>
                <View style={styles.tierPriceRow}>
                  <Text style={styles.tierPrice}>${t.price_monthly}</Text>
                  {t.price_monthly > 0 && <Text style={styles.tierPriceUnit}>/mo</Text>}
                </View>
                <Text style={styles.tierBlurb}>{t.blurb}</Text>
                <View style={{ height: 12 }} />
                {t.features.map((f: string, i: number) => (
                  <View key={i} style={styles.featureRow}>
                    <Ionicons name="checkmark-circle" size={16} color={t.highlight ? C.brand : C.lavender} />
                    <Text style={styles.featureRowText}>{f}</Text>
                  </View>
                ))}
                <Pressable
                  testID={`landing-tier-cta-${t.id}`}
                  onPress={onCTA}
                  style={[styles.tierCta, t.highlight ? { backgroundColor: C.brand } : { backgroundColor: C.surface2, borderWidth: 1, borderColor: C.borderStrong }]}
                >
                  <Text style={[styles.tierCtaText, !t.highlight && { color: C.text }]}>
                    {t.id === "free" ? "Start free" : `Choose ${t.name}`}
                  </Text>
                </Pressable>
              </View>
            ))}
          </View>
        </Section>

        {/* ─── FINAL SLOGAN ─── */}
        <View style={[styles.finalCta, { padding: isDesktop ? 100 : 40 }]}>
          <LinearGradient
            colors={["rgba(124,58,237,0.18)", "rgba(255,176,0,0.06)"]}
            style={StyleSheet.absoluteFillObject}
          />
          <Text style={styles.finalKicker}>YOUR ASCENT BEGINS NOW</Text>
          <View style={styles.sloganRow}>
            <Text style={styles.sloganWord}>LEARN.</Text>
            <View style={styles.sloganDot} />
            <Text style={styles.sloganWord}>GROW.</Text>
            <View style={styles.sloganDot} />
            <Text style={styles.sloganWord}>TRANSFORM.</Text>
            <View style={styles.sloganDot} />
            <Text style={[styles.sloganWord, { color: C.brand }]}>ASCEND.</Text>
          </View>
          <Text style={styles.finalSub}>Free to start. No card required.</Text>
          <Pressable testID="final-cta-btn" onPress={onCTA} style={[styles.primaryBtn, { marginTop: 24 }]}>
            <Text style={styles.primaryBtnText}>Begin your ascent</Text>
            <Ionicons name="arrow-forward" size={18} color="#000" />
          </Pressable>
        </View>

        {/* Footer */}
        <View style={styles.footer}>
          <View style={styles.brandRow}>
            <View style={styles.brandLogo}><Ionicons name="sparkles" size={12} color="#000" /></View>
            <Text style={styles.brandText}>ASCENDRA</Text>
          </View>
          <Text style={styles.footerText}>© 2026 Ascendra · AI-Powered Learning. Boundless Growth.</Text>
        </View>
      </ScrollView>
    </View>
  );
}

function Section({ title, h1, children, isDesktop }: any) {
  return (
    <View style={[styles.section, { paddingHorizontal: isDesktop ? 60 : 24, paddingVertical: isDesktop ? 88 : 56 }]}>
      <View style={{ maxWidth: 1100, alignSelf: "center", width: "100%" }}>
        <Text style={styles.sectionKicker}>{title}</Text>
        <Text style={[styles.sectionH1, { fontSize: isDesktop ? 40 : 28 }]}>{h1}</Text>
        <View style={{ height: 32 }} />
        {children}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },

  // Nav
  nav: {
    position: Platform.OS === "web" ? ("sticky" as any) : "relative",
    top: 0, zIndex: 50,
    backgroundColor: "rgba(7,11,31,0.85)", borderBottomWidth: 1, borderColor: C.border,
    ...(Platform.OS === "web" ? ({ backdropFilter: "blur(20px)" } as any) : {}),
  },
  navInner: {
    flexDirection: "row", alignItems: "center", justifyContent: "space-between",
    paddingHorizontal: 24, paddingVertical: 14, maxWidth: 1280, width: "100%", alignSelf: "center",
  },
  brandRow: { flexDirection: "row", alignItems: "center", gap: 10 },
  brandLogo: { width: 24, height: 24, borderRadius: 7, backgroundColor: C.brand, alignItems: "center", justifyContent: "center" },
  brandText: { color: C.text, fontWeight: "900", fontSize: 13, letterSpacing: 4 },
  navLink: { color: C.textDim, fontSize: 14, fontWeight: "500" },
  navCta: { backgroundColor: C.brand, paddingHorizontal: 16, paddingVertical: 10, borderRadius: RADIUS.pill },
  navCtaText: { color: "#000", fontWeight: "800", fontSize: 13 },

  // Hero — split layout
  hero: { width: "100%", backgroundColor: "#0A0413", overflow: "hidden", position: "relative" },
  heroDesktop: { flexDirection: "row", minHeight: 720, alignItems: "stretch" },
  heroMobile: { flexDirection: "column" },
  heroLeft: { position: "relative", backgroundColor: "#0A0413", overflow: "hidden" },
  // Clipping box for the brand-board crop. We render the full board image enlarged
  // and shifted so only the angel (≈ left 30% of the board) is visible.
  heroImageClip: { width: "100%", height: "100%", overflow: "hidden" },
  // New hero artwork is a complete brand composition (wordmark + angel + tagline).
  // Display it cleanly — no zoom hacks needed.
  heroImageCrop: {
    width: "100%",
    height: "100%",
    ...Platform.select({
      web: {
        objectFit: "cover",
        objectPosition: "center",
      } as any,
      default: {},
    }),
  },
  heroRight: { position: "relative", justifyContent: "center", overflow: "hidden" },
  heroBrand: {
    color: C.brand, fontSize: 16, fontWeight: "900",
    letterSpacing: 10, marginBottom: 16,
  },
  heroDivider: { width: 40, height: 2, backgroundColor: C.brand, marginBottom: 16, opacity: 0.7 },
  heroKicker: { color: C.lavender, fontSize: 11, fontWeight: "700", letterSpacing: 3, marginBottom: 24 },
  heroH1: { color: C.text, fontWeight: "900", letterSpacing: -2, lineHeight: undefined as any },
  heroH1Gold: { color: C.brand, fontStyle: "italic" },
  heroSub: { color: C.textDim, fontSize: 17, marginTop: 24, lineHeight: 26 },
  heroCtas: { flexDirection: "row", flexWrap: "wrap", gap: 12, marginTop: 32 },
  heroProofRow: { marginTop: 28 },
  heroProofText: { color: C.textMuted, fontSize: 12 },

  // Buttons
  primaryBtn: { backgroundColor: C.brand, paddingHorizontal: 24, paddingVertical: 16, borderRadius: RADIUS.lg, flexDirection: "row", alignItems: "center", gap: 8 },
  primaryBtnText: { color: "#000", fontWeight: "800", fontSize: 15 },
  secondaryBtn: { backgroundColor: "rgba(7,11,31,0.6)", paddingHorizontal: 24, paddingVertical: 16, borderRadius: RADIUS.lg, borderWidth: 1, borderColor: C.borderStrong },
  secondaryBtnText: { color: C.text, fontWeight: "700", fontSize: 15 },

  // Mission
  missionSection: { alignItems: "center", paddingVertical: 48, paddingHorizontal: 24 },
  missionCard: {
    width: "100%", padding: 36, borderRadius: RADIUS.xl, borderWidth: 1, borderColor: C.borderStrong,
    backgroundColor: "rgba(26,31,61,0.55)", overflow: "hidden",
  },
  missionLabel: { color: C.brand, fontSize: 11, fontWeight: "800", letterSpacing: 3, marginBottom: 14 },
  missionText: { color: C.text, fontWeight: "700", letterSpacing: -0.5, lineHeight: undefined as any },

  // Models strip
  modelsStrip: { paddingVertical: 32, paddingHorizontal: 24, borderTopWidth: 1, borderBottomWidth: 1, borderColor: C.border, backgroundColor: C.celestial },
  modelsStripLabel: { color: C.lavender, fontSize: 11, fontWeight: "800", letterSpacing: 3, marginBottom: 18, textAlign: "center" },
  modelsStripRow: { justifyContent: "center", alignItems: "center", gap: 10, flexDirection: "row", flexWrap: "wrap" },
  modelChip: { paddingHorizontal: 14, paddingVertical: 8, borderRadius: RADIUS.pill, borderWidth: 1, borderColor: C.borderStrong, backgroundColor: C.bg },
  modelChipText: { color: C.textDim, fontWeight: "700", fontSize: 12 },

  // Sections frame
  section: { backgroundColor: C.bg },
  sectionKicker: { color: C.brand, fontSize: 11, fontWeight: "800", letterSpacing: 3 },
  sectionH1: { color: C.text, fontWeight: "900", letterSpacing: -1.2, marginTop: 14 },
  grid: { flexDirection: "row", flexWrap: "wrap" },

  // Pillars
  pillarCard: { flexGrow: 1, padding: 22, backgroundColor: C.celestial, borderWidth: 1, borderColor: C.border, borderRadius: RADIUS.xl, minHeight: 200 },
  pillarIcon: { width: 48, height: 48, borderRadius: 12, backgroundColor: "rgba(255,176,0,0.12)", alignItems: "center", justifyContent: "center", marginBottom: 14, borderWidth: 1, borderColor: "rgba(255,176,0,0.35)" },
  pillarTitle: { color: C.brand, fontWeight: "800", fontSize: 14, letterSpacing: 1.2, textTransform: "uppercase" },
  pillarBody: { color: C.textDim, fontSize: 14, marginTop: 8, lineHeight: 21 },

  // Symbolism
  symbolCard: { flexGrow: 1, padding: 22, backgroundColor: C.celestial, borderWidth: 1, borderColor: C.border, borderRadius: RADIUS.xl, minHeight: 180 },
  symbolIcon: { width: 48, height: 48, borderRadius: 24, alignItems: "center", justifyContent: "center", marginBottom: 14, backgroundColor: "rgba(124,58,237,0.15)", borderWidth: 1, borderColor: "rgba(191,180,255,0.35)" },
  symbolTitle: { color: C.text, fontWeight: "900", fontSize: 19, letterSpacing: -0.2, marginBottom: 8 },
  symbolBody: { color: C.textDim, fontSize: 13, lineHeight: 20 },

  // Brand board image
  boardSection: { width: "100%", paddingVertical: 40, paddingHorizontal: 24, backgroundColor: C.bg, alignItems: "center" },
  boardImage: { width: "100%", maxWidth: 1100, aspectRatio: 1, borderRadius: RADIUS.xl },

  // Pricing
  tierCard: { flexGrow: 1, padding: 28, backgroundColor: C.celestial, borderWidth: 1, borderColor: C.border, borderRadius: RADIUS.xl, position: "relative" },
  tierHighlight: { borderColor: C.brand, backgroundColor: "rgba(255,176,0,0.05)" },
  tierBadge: { position: "absolute", top: -10, left: 24, backgroundColor: C.brand, paddingHorizontal: 10, paddingVertical: 4, borderRadius: RADIUS.pill },
  tierBadgeText: { color: "#000", fontWeight: "900", fontSize: 10, letterSpacing: 1.5 },
  tierName: { color: C.text, fontWeight: "900", fontSize: 20 },
  tierPriceRow: { flexDirection: "row", alignItems: "flex-end", gap: 4, marginTop: 8 },
  tierPrice: { color: C.text, fontWeight: "900", fontSize: 38, letterSpacing: -1.5 },
  tierPriceUnit: { color: C.textDim, fontSize: 13, paddingBottom: 7 },
  tierBlurb: { color: C.textDim, fontSize: 13, marginTop: 4 },
  featureRow: { flexDirection: "row", alignItems: "center", gap: 8, marginVertical: 4 },
  featureRowText: { color: C.textDim, fontSize: 13, flex: 1 },
  tierCta: { marginTop: 18, paddingVertical: 12, borderRadius: RADIUS.md, alignItems: "center" },
  tierCtaText: { color: "#000", fontWeight: "800", fontSize: 14 },

  // Final slogan
  finalCta: { alignItems: "center", borderTopWidth: 1, borderColor: C.border, overflow: "hidden" },
  finalKicker: { color: C.brand, fontSize: 11, fontWeight: "800", letterSpacing: 3, marginBottom: 12 },
  sloganRow: { flexDirection: "row", flexWrap: "wrap", justifyContent: "center", alignItems: "center", gap: 12, marginVertical: 12 },
  sloganWord: { color: C.text, fontSize: 22, fontWeight: "900", letterSpacing: 2 },
  sloganDot: { width: 6, height: 6, borderRadius: 3, backgroundColor: C.lavender },
  finalSub: { color: C.textDim, fontSize: 14, marginTop: 12 },

  // Footer
  footer: { paddingHorizontal: 40, paddingVertical: 32, alignItems: "center", gap: 10 },
  footerText: { color: C.textMuted, fontSize: 12 },
});
