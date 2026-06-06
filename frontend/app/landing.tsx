import { useEffect, useState } from "react";
import {
  View, Text, StyleSheet, ScrollView, Pressable, Image, useWindowDimensions, Platform,
} from "react-native";
import { useRouter, Stack } from "expo-router";
import { LinearGradient } from "expo-linear-gradient";
import { Ionicons } from "@expo/vector-icons";
import { C, RADIUS } from "@/src/theme";
import { api } from "@/src/api";

const HERO_BG = "https://images.pexels.com/photos/12623752/pexels-photo-12623752.jpeg";

const FEATURES = [
  { icon: "sparkles",       title: "AI-Personalized",  body: "Learning paths tailored to your goals, pace, and style." },
  { icon: "rocket",         title: "Real-World Skills",body: "Practical knowledge that drives real impact — not theory." },
  { icon: "trending-up",    title: "Track & Grow",     body: "See your progress. Celebrate your wins. Build the streak." },
  { icon: "people-circle",  title: "Expert Guidance",  body: "Learn from industry leaders and your AI tutor, 24/7." },
  { icon: "planet",         title: "22 Frontier Models", body: "GPT-5.2, Claude 4.5, Gemini 3, Nano Banana, Sora 2 — all covered." },
  { icon: "trophy",         title: "Built to Transform",  body: "Each lesson ends with a real-world quiz to lock it in." },
];

const TESTIMONIALS = [
  { name: "Maya R.", role: "Marketing Lead", text: "Went from AI-curious to shipping AI-powered campaigns in 2 weeks. Wild value.", img: "https://images.unsplash.com/photo-1532170579297-281918c8ae72" },
  { name: "Tom K.",  role: "Founder",        text: "The Build-a-Business path saved me $20k in consultants. I launched my MVP in 9 days.", img: "https://images.pexels.com/photos/34114598/pexels-photo-34114598.jpeg" },
  { name: "Priya S.", role: "Designer",      text: "Nano Banana + Sora 2 lessons unlocked an entire new creative workflow for me.", img: "https://images.pexels.com/photos/18173598/pexels-photo-18173598.jpeg" },
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
      <Stack.Screen options={{ headerShown: false, title: "AI Academy" }} />

      {/* Nav */}
      <View style={styles.nav}>
        <View style={styles.navInner}>
          <View style={styles.brandRow}>
            <View style={styles.brandLogo}><Ionicons name="sparkles" size={16} color="#000" /></View>
            <Text style={styles.brandText}>ASCENDRA</Text>
          </View>
          <View style={{ flexDirection: "row", alignItems: "center", gap: 16 }}>
            {isDesktop && (
              <>
                <NavLink label="Paths" />
                <NavLink label="Pricing" />
                <NavLink label="Reviews" />
              </>
            )}
            <Pressable testID="nav-signin-btn" onPress={onSignIn}><Text style={styles.linkText}>Sign in</Text></Pressable>
            <Pressable testID="nav-cta-btn" onPress={onCTA} style={styles.navCta}>
              <Text style={styles.navCtaText}>Start free</Text>
            </Pressable>
          </View>
        </View>
      </View>

      <ScrollView contentContainerStyle={{ paddingBottom: 60 }}>
        {/* Hero */}
        <View style={[styles.hero, { minHeight: isDesktop ? 620 : 540 }]}>
          <Image source={{ uri: HERO_BG }} style={StyleSheet.absoluteFillObject as any} resizeMode="cover" />
          <LinearGradient
            colors={["rgba(10,10,10,0.4)", "rgba(10,10,10,0.85)", "rgba(10,10,10,1)"]}
            style={StyleSheet.absoluteFillObject}
          />
          <View style={[styles.heroInner, { maxWidth: 1100, paddingHorizontal: isDesktop ? 60 : 24 }]}>
            <View style={styles.kickerBox}>
              <View style={styles.kickerDot} />
              <Text style={styles.kicker}>AI-POWERED LEARNING · BOUNDLESS GROWTH</Text>
            </View>
            <Text style={[styles.heroTitle, { fontSize: isDesktop ? 72 : 44 }]}>
              Ready to{"\n"}<Text style={{ color: C.brand }}>rise today?</Text>
            </Text>
            <Text style={[styles.heroSub, { maxWidth: 640 }]}>
              Ascendra is the AI learning partner that helps you ascend from beginner to builder.
              Personalized paths covering GPT-5.2, Claude 4.5, Gemini 3, Nano Banana, Sora 2, and 18 more
              frontier models — taught by an AI tutor who learns your style.
            </Text>
            <View style={styles.heroCtaRow}>
              <Pressable testID="hero-cta-btn" onPress={onCTA} style={styles.primaryBtn}>
                <Text style={styles.primaryBtnText}>Start free — no card needed</Text>
                <Ionicons name="arrow-forward" size={18} color="#000" />
              </Pressable>
              <Pressable onPress={() => router.push("/pricing")} style={styles.secondaryBtn}>
                <Text style={styles.secondaryBtnText}>See pricing</Text>
              </Pressable>
            </View>
            <View style={styles.heroProof}>
              <Text style={styles.heroProofText}>★★★★★  Loved by builders, marketers, and founders.</Text>
            </View>
          </View>
        </View>

        {/* Models marquee */}
        <View style={styles.modelsStrip}>
          <Text style={styles.modelsStripLabel}>COVERING THE MODELS THAT MATTER</Text>
          <View style={[styles.modelsStripRow, { flexWrap: "wrap" }]}>
            {["GPT-5.2", "Claude 4.5", "Gemini 3", "Nano Banana", "Sora 2", "ElevenLabs", "Perplexity", "Midjourney", "Veo 3", "Whisper", "Cursor"].map((m) => (
              <View key={m} style={styles.modelChip}>
                <Text style={styles.modelChipText}>{m}</Text>
              </View>
            ))}
          </View>
        </View>

        {/* Features grid */}
        <Section title="WHY ASCENDRA" h1="Built for your rise." isDesktop={isDesktop}>
          <View style={[styles.grid, { gap: 16 }]}>
            {FEATURES.map((f) => (
              <View key={f.title} style={[styles.featureCard, { flexBasis: isDesktop ? "31%" : "100%" }]}>
                <View style={styles.featureIcon}><Ionicons name={f.icon as any} size={22} color={C.brand} /></View>
                <Text style={styles.featureTitle}>{f.title}</Text>
                <Text style={styles.featureBody}>{f.body}</Text>
              </View>
            ))}
          </View>
        </Section>

        {/* Testimonials */}
        <Section title="REVIEWS" h1="People are learning faster than ever." isDesktop={isDesktop}>
          <View style={[styles.grid, { gap: 16 }]}>
            {TESTIMONIALS.map((t) => (
              <View key={t.name} style={[styles.testimonialCard, { flexBasis: isDesktop ? "31%" : "100%" }]}>
                <Text style={styles.stars}>★★★★★</Text>
                <Text style={styles.testimonialText}>&ldquo;{t.text}&rdquo;</Text>
                <View style={styles.testimonialFooter}>
                  <Image source={{ uri: t.img }} style={styles.testimonialAvatar} />
                  <View>
                    <Text style={styles.testimonialName}>{t.name}</Text>
                    <Text style={styles.testimonialRole}>{t.role}</Text>
                  </View>
                </View>
              </View>
            ))}
          </View>
        </Section>

        {/* Pricing preview */}
        <Section title="PRICING" h1="Start free. Upgrade when you're ready." isDesktop={isDesktop}>
          <View style={[styles.grid, { gap: 16 }]}>
            {tiers.map((t) => (
              <View key={t.id} style={[
                styles.tierCard,
                { flexBasis: isDesktop ? "31%" : "100%" },
                t.highlight && styles.tierHighlight,
              ]}>
                {t.highlight && (
                  <View style={styles.tierBadge}><Text style={styles.tierBadgeText}>MOST POPULAR</Text></View>
                )}
                <Text style={styles.tierName}>{t.name}</Text>
                <View style={styles.tierPriceRow}>
                  <Text style={styles.tierPrice}>${t.price_monthly}</Text>
                  {t.price_monthly > 0 && <Text style={styles.tierPriceUnit}>/mo</Text>}
                </View>
                <Text style={styles.tierBlurb}>{t.blurb}</Text>
                <View style={{ height: 12 }} />
                {t.features.map((f: string, i: number) => (
                  <View key={i} style={styles.featureRow}>
                    <Ionicons name="checkmark-circle" size={16} color={t.highlight ? C.brand : C.success} />
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

        {/* Final CTA */}
        <View style={[styles.finalCta, { padding: isDesktop ? 80 : 32 }]}>
          <Text style={[styles.finalTitle, { fontSize: isDesktop ? 56 : 36 }]}>
            Learn. Grow.{"\n"}Transform.{"\n"}<Text style={{ color: C.brand }}>Ascend.</Text>
          </Text>
          <Text style={styles.finalSub}>Your journey begins with a single rise. Start free today.</Text>
          <Pressable testID="final-cta-btn" onPress={onCTA} style={styles.primaryBtn}>
            <Text style={styles.primaryBtnText}>Start free</Text>
            <Ionicons name="arrow-forward" size={18} color="#000" />
          </Pressable>
        </View>

        {/* Footer */}
        <View style={styles.footer}>
          <View style={styles.brandRow}>
            <View style={styles.brandLogo}><Ionicons name="sparkles" size={14} color="#000" /></View>
            <Text style={styles.brandText}>ASCENDRA</Text>
          </View>
          <Text style={styles.footerText}>© 2026 Ascendra · AI-Powered Learning. Boundless Growth.</Text>
        </View>
      </ScrollView>
    </View>
  );
}

function NavLink({ label }: { label: string }) {
  return <Text style={styles.linkText}>{label}</Text>;
}

function Section({ title, h1, children, isDesktop }: any) {
  return (
    <View style={[styles.section, { paddingHorizontal: isDesktop ? 60 : 24, paddingVertical: isDesktop ? 96 : 56 }]}>
      <View style={{ maxWidth: 1100, alignSelf: "center", width: "100%" }}>
        <Text style={styles.sectionKicker}>{title}</Text>
        <Text style={[styles.sectionH1, { fontSize: isDesktop ? 44 : 30 }]}>{h1}</Text>
        <View style={{ height: 32 }} />
        {children}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  nav: {
    position: Platform.OS === "web" ? ("sticky" as any) : "relative",
    top: 0, zIndex: 50,
    backgroundColor: "rgba(10,10,10,0.85)", borderBottomWidth: 1, borderColor: C.border,
    ...(Platform.OS === "web" ? ({ backdropFilter: "blur(20px)" } as any) : {}),
  },
  navInner: {
    flexDirection: "row", alignItems: "center", justifyContent: "space-between",
    paddingHorizontal: 24, paddingVertical: 14, maxWidth: 1280, width: "100%", alignSelf: "center",
  },
  brandRow: { flexDirection: "row", alignItems: "center", gap: 8 },
  brandLogo: { width: 26, height: 26, borderRadius: 7, backgroundColor: C.brand, alignItems: "center", justifyContent: "center" },
  brandText: { color: C.text, fontWeight: "900", fontSize: 13, letterSpacing: 2.5 },
  linkText: { color: C.textDim, fontSize: 14, fontWeight: "500" },
  navCta: { backgroundColor: C.brand, paddingHorizontal: 16, paddingVertical: 10, borderRadius: RADIUS.pill },
  navCtaText: { color: "#000", fontWeight: "800", fontSize: 13 },

  hero: { justifyContent: "center", paddingVertical: 60 },
  heroInner: { width: "100%", alignSelf: "center" },
  kickerBox: { flexDirection: "row", alignItems: "center", gap: 8, marginBottom: 24 },
  kickerDot: { width: 7, height: 7, borderRadius: 4, backgroundColor: C.brand },
  kicker: { color: C.brand, fontSize: 12, fontWeight: "800", letterSpacing: 3 },
  heroTitle: { color: C.text, fontWeight: "900", letterSpacing: -2.5, lineHeight: undefined as any },
  heroSub: { color: C.textDim, fontSize: 18, marginTop: 24, lineHeight: 28 },
  heroCtaRow: { flexDirection: "row", flexWrap: "wrap", gap: 12, marginTop: 36 },
  primaryBtn: { backgroundColor: C.brand, paddingHorizontal: 24, paddingVertical: 16, borderRadius: RADIUS.lg, flexDirection: "row", alignItems: "center", gap: 8 },
  primaryBtnText: { color: "#000", fontWeight: "800", fontSize: 15 },
  secondaryBtn: { backgroundColor: "transparent", paddingHorizontal: 24, paddingVertical: 16, borderRadius: RADIUS.lg, borderWidth: 1, borderColor: C.borderStrong },
  secondaryBtnText: { color: C.text, fontWeight: "700", fontSize: 15 },
  heroProof: { marginTop: 32 },
  heroProofText: { color: C.textMuted, fontSize: 13 },

  modelsStrip: { paddingVertical: 30, paddingHorizontal: 24, borderTopWidth: 1, borderBottomWidth: 1, borderColor: C.border, backgroundColor: C.surface },
  modelsStripLabel: { color: C.textMuted, fontSize: 11, fontWeight: "800", letterSpacing: 3, marginBottom: 16, textAlign: "center" },
  modelsStripRow: { justifyContent: "center", alignItems: "center", gap: 10, flexDirection: "row" },
  modelChip: { paddingHorizontal: 14, paddingVertical: 8, borderRadius: RADIUS.pill, borderWidth: 1, borderColor: C.border, backgroundColor: C.surface2 },
  modelChipText: { color: C.textDim, fontWeight: "700", fontSize: 12 },

  section: { backgroundColor: C.bg },
  sectionKicker: { color: C.brand, fontSize: 11, fontWeight: "800", letterSpacing: 3 },
  sectionH1: { color: C.text, fontWeight: "900", letterSpacing: -1.5, marginTop: 14 },
  grid: { flexDirection: "row", flexWrap: "wrap" },

  featureCard: { flexGrow: 1, padding: 24, backgroundColor: C.surface, borderWidth: 1, borderColor: C.border, borderRadius: RADIUS.xl },
  featureIcon: { width: 44, height: 44, borderRadius: 12, backgroundColor: C.brandDim, alignItems: "center", justifyContent: "center", marginBottom: 14 },
  featureTitle: { color: C.text, fontWeight: "800", fontSize: 18, letterSpacing: -0.3 },
  featureBody: { color: C.textDim, fontSize: 14, marginTop: 6, lineHeight: 22 },

  testimonialCard: { flexGrow: 1, padding: 24, backgroundColor: C.surface, borderWidth: 1, borderColor: C.border, borderRadius: RADIUS.xl },
  stars: { color: C.brand, fontSize: 14, letterSpacing: 2 },
  testimonialText: { color: C.text, fontSize: 16, lineHeight: 26, marginTop: 12 },
  testimonialFooter: { flexDirection: "row", alignItems: "center", gap: 10, marginTop: 18 },
  testimonialAvatar: { width: 36, height: 36, borderRadius: 18, backgroundColor: C.surface2 },
  testimonialName: { color: C.text, fontWeight: "700", fontSize: 14 },
  testimonialRole: { color: C.textMuted, fontSize: 12 },

  tierCard: { flexGrow: 1, padding: 28, backgroundColor: C.surface, borderWidth: 1, borderColor: C.border, borderRadius: RADIUS.xl, position: "relative" },
  tierHighlight: { borderColor: C.brand, backgroundColor: "rgba(255,176,0,0.04)" },
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

  finalCta: { alignItems: "center", borderTopWidth: 1, borderBottomWidth: 1, borderColor: C.border, marginTop: 0, gap: 16, backgroundColor: C.surface },
  finalTitle: { color: C.text, fontWeight: "900", letterSpacing: -2, textAlign: "center" },
  finalSub: { color: C.textDim, fontSize: 16, textAlign: "center" },

  footer: { paddingHorizontal: 40, paddingVertical: 32, alignItems: "center", gap: 8 },
  footerText: { color: C.textMuted, fontSize: 12 },
});
