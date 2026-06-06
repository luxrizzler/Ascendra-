import { useEffect, useRef, useState } from "react";
import {
  View, Text, StyleSheet, ActivityIndicator, Pressable, Platform, Share, useWindowDimensions, ScrollView,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useLocalSearchParams, useRouter, Stack } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { LinearGradient } from "expo-linear-gradient";
import { C, RADIUS } from "@/src/theme";
import { api, BACKEND_URL } from "@/src/api";

type Cert = {
  id: string;
  user_id: string;
  user_name: string;
  path_id: string;
  path_title: string;
  path_color: string;
  issued_at: string;
  serial: string;
};

export default function Certificate() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const { width } = useWindowDimensions();
  const [cert, setCert] = useState<Cert | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const cardRef = useRef<View>(null);

  useEffect(() => {
    api.get(`/certificates/${id}`)
      .then(setCert)
      .catch((e: any) => setErr(e.message || "Could not load certificate"));
  }, [id]);

  if (err) {
    return (
      <SafeAreaView style={styles.root}>
        <Stack.Screen options={{ headerShown: false }} />
        <View style={styles.center}>
          <Ionicons name="alert-circle-outline" size={42} color={C.danger} />
          <Text style={styles.errText}>{err}</Text>
          <Pressable onPress={() => router.back()} style={styles.backBtn}><Text style={styles.backText}>Go back</Text></Pressable>
        </View>
      </SafeAreaView>
    );
  }

  if (!cert) {
    return (
      <SafeAreaView style={styles.root}>
        <Stack.Screen options={{ headerShown: false }} />
        <View style={styles.center}><ActivityIndicator color={C.brand} /></View>
      </SafeAreaView>
    );
  }

  const issued = new Date(cert.issued_at);
  const dateStr = issued.toLocaleDateString(undefined, { year: "numeric", month: "long", day: "numeric" });
  const verifyUrl = `${BACKEND_URL}/api/certificates/${cert.id}`;

  const onShare = async () => {
    const msg = `I just earned the "${cert.path_title}" certificate on Ascendra ✨ — building real skills with AI. (${cert.serial})`;
    try {
      if (Platform.OS === "web" && typeof navigator !== "undefined" && (navigator as any).share) {
        await (navigator as any).share({ title: "Ascendra Certificate", text: msg, url: verifyUrl });
      } else if (Platform.OS === "web") {
        if (typeof navigator !== "undefined" && navigator.clipboard) {
          await navigator.clipboard.writeText(msg + " " + verifyUrl);
        }
      } else {
        await Share.share({ message: msg + " " + verifyUrl });
      }
    } catch { /* user cancelled */ }
  };

  // Make the cert nicely sized on any screen
  const certWidth = Math.min(width - 32, 560);
  const certHeight = certWidth * 1.35;

  return (
    <View style={styles.root}>
      <Stack.Screen options={{ headerShown: false }} />
      <SafeAreaView edges={["top"]} style={styles.header}>
        <Pressable testID="cert-back-btn" onPress={() => router.back()} style={styles.headerBtn}>
          <Ionicons name="chevron-back" size={22} color={C.text} />
        </Pressable>
        <Text style={styles.headerTitle}>Certificate</Text>
        <Pressable testID="cert-share-btn" onPress={onShare} style={styles.headerBtn}>
          <Ionicons name="share-outline" size={22} color={C.text} />
        </Pressable>
      </SafeAreaView>

      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
        <View ref={cardRef} style={[styles.cert, { width: certWidth, minHeight: certHeight, borderColor: cert.path_color }]}>
          <LinearGradient
            colors={[cert.path_color + "22", "transparent", cert.path_color + "11"]}
            style={StyleSheet.absoluteFillObject as any}
          />

          {/* Corner ornaments */}
          <CornerOrnament color={cert.path_color} pos="tl" />
          <CornerOrnament color={cert.path_color} pos="tr" />
          <CornerOrnament color={cert.path_color} pos="bl" />
          <CornerOrnament color={cert.path_color} pos="br" />

          <View style={{ alignItems: "center", padding: 28 }}>
            <Text style={styles.brand}>ASCENDRA</Text>
            <View style={[styles.brandUnderline, { backgroundColor: cert.path_color }]} />

            <Text style={styles.certType}>CERTIFICATE OF MASTERY</Text>

            <Text style={styles.awardedTo}>This is to certify that</Text>
            <Text style={styles.userName}>{cert.user_name}</Text>

            <Text style={styles.awardedTo}>has successfully completed</Text>
            <Text style={[styles.pathName, { color: cert.path_color }]}>{cert.path_title}</Text>

            <View style={styles.sealWrap}>
              <View style={[styles.seal, { borderColor: cert.path_color }]}>
                <Ionicons name="ribbon" size={36} color={cert.path_color} />
                <Text style={[styles.sealText, { color: cert.path_color }]}>MASTERED</Text>
              </View>
            </View>

            <View style={styles.footerRow}>
              <View style={styles.footerCol}>
                <Text style={styles.footerLabel}>ISSUED</Text>
                <Text style={styles.footerValue}>{dateStr}</Text>
              </View>
              <View style={[styles.footerCol, { alignItems: "flex-end" }]}>
                <Text style={styles.footerLabel}>SERIAL</Text>
                <Text style={styles.footerValue}>{cert.serial}</Text>
              </View>
            </View>
          </View>
        </View>

        <Pressable testID="cert-share-cta" onPress={onShare} style={[styles.shareCta, { backgroundColor: cert.path_color }]}>
          <Ionicons name="share-social" size={18} color="#000" />
          <Text style={styles.shareCtaText}>Share your achievement</Text>
        </Pressable>

        <Text style={styles.note}>Tip: On mobile, you can also screenshot this certificate to save it.</Text>

        <Pressable testID="cert-paths-cta" onPress={() => router.replace("/(tabs)/paths")} style={styles.secondaryCta}>
          <Text style={styles.secondaryCtaText}>Explore more paths</Text>
          <Ionicons name="arrow-forward" size={16} color={C.text} />
        </Pressable>
      </ScrollView>
    </View>
  );
}

function CornerOrnament({ color, pos }: { color: string; pos: "tl" | "tr" | "bl" | "br" }) {
  const base: any = { position: "absolute", width: 36, height: 36 };
  const pieces: any = {
    tl: { top: 10, left: 10, borderTopWidth: 2, borderLeftWidth: 2, borderTopLeftRadius: 10 },
    tr: { top: 10, right: 10, borderTopWidth: 2, borderRightWidth: 2, borderTopRightRadius: 10 },
    bl: { bottom: 10, left: 10, borderBottomWidth: 2, borderLeftWidth: 2, borderBottomLeftRadius: 10 },
    br: { bottom: 10, right: 10, borderBottomWidth: 2, borderRightWidth: 2, borderBottomRightRadius: 10 },
  };
  return <View style={[base, pieces[pos], { borderColor: color }]} />;
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  header: {
    flexDirection: "row", alignItems: "center", justifyContent: "space-between",
    paddingHorizontal: 12, paddingVertical: 8,
  },
  headerBtn: { width: 40, height: 40, alignItems: "center", justifyContent: "center" },
  headerTitle: { color: C.text, fontWeight: "800", fontSize: 16 },
  scroll: { padding: 16, alignItems: "center", paddingBottom: 60 },
  cert: {
    backgroundColor: C.surface, borderRadius: RADIUS.xl, borderWidth: 2,
    overflow: "hidden", marginVertical: 12,
  },
  brand: { color: C.brand, fontWeight: "900", fontSize: 22, letterSpacing: 6 },
  brandUnderline: { width: 60, height: 2, marginTop: 6, marginBottom: 22 },
  certType: { color: C.textDim, fontSize: 11, fontWeight: "800", letterSpacing: 4 },
  awardedTo: { color: C.textMuted, fontSize: 12, marginTop: 20, fontStyle: "italic" },
  userName: { color: C.text, fontWeight: "900", fontSize: 28, marginTop: 8, letterSpacing: -0.5, textAlign: "center" },
  pathName: { fontWeight: "900", fontSize: 22, marginTop: 8, letterSpacing: -0.5, textAlign: "center", maxWidth: "90%" },
  sealWrap: { alignItems: "center", marginTop: 32 },
  seal: { width: 110, height: 110, borderRadius: 55, borderWidth: 2, alignItems: "center", justifyContent: "center" },
  sealText: { fontSize: 9, fontWeight: "900", letterSpacing: 2, marginTop: 2 },
  footerRow: { flexDirection: "row", justifyContent: "space-between", width: "100%", marginTop: 36 },
  footerCol: { flex: 1 },
  footerLabel: { color: C.textMuted, fontSize: 9, fontWeight: "800", letterSpacing: 1.5 },
  footerValue: { color: C.text, fontSize: 13, fontWeight: "700", marginTop: 2 },
  shareCta: {
    flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 8,
    paddingVertical: 14, paddingHorizontal: 28, borderRadius: RADIUS.pill, marginTop: 20,
  },
  shareCtaText: { color: "#000", fontWeight: "800", fontSize: 14 },
  note: { color: C.textMuted, fontSize: 11, marginTop: 14, textAlign: "center", paddingHorizontal: 24 },
  secondaryCta: {
    marginTop: 20, paddingVertical: 12, paddingHorizontal: 18, borderRadius: RADIUS.pill,
    borderWidth: 1, borderColor: C.borderStrong, flexDirection: "row", alignItems: "center", gap: 8,
  },
  secondaryCtaText: { color: C.text, fontWeight: "700", fontSize: 14 },
  center: { flex: 1, alignItems: "center", justifyContent: "center", padding: 24 },
  errText: { color: C.text, marginTop: 14, textAlign: "center" },
  backBtn: { marginTop: 18, padding: 12, borderRadius: RADIUS.md, backgroundColor: C.surface, borderWidth: 1, borderColor: C.border },
  backText: { color: C.text, fontWeight: "700" },
});
