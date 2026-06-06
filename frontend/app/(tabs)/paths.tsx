import { useEffect, useState } from "react";
import { View, Text, StyleSheet, ScrollView, Pressable, Image, ActivityIndicator } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useRouter } from "expo-router";
import { LinearGradient } from "expo-linear-gradient";
import { Ionicons } from "@expo/vector-icons";
import { C, RADIUS } from "@/src/theme";
import { api } from "@/src/api";

export default function Paths() {
  const router = useRouter();
  const [paths, setPaths] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get("/paths").then((r) => setPaths(r.paths)).finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <View style={[styles.root, { alignItems: "center", justifyContent: "center" }]}>
        <ActivityIndicator color={C.brand} />
      </View>
    );
  }

  return (
    <SafeAreaView style={styles.root} edges={["top"]}>
      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
        <Text style={styles.kicker}>LEARNING PATHS</Text>
        <Text style={styles.h1}>Pick your direction</Text>
        <Text style={styles.sub}>Each path goes from beginner-friendly to advanced workflows.</Text>

        <View style={{ height: 24 }} />

        {paths.map((p) => (
          <Pressable
            key={p.id}
            testID={`paths-card-${p.id}`}
            onPress={() => router.push(`/path/${p.id}`)}
            style={styles.card}
          >
            <Image source={{ uri: p.image }} style={styles.cardImg} />
            <LinearGradient
              colors={["rgba(0,0,0,0.0)", "rgba(0,0,0,0.4)", "rgba(0,0,0,0.95)"]}
              style={StyleSheet.absoluteFillObject}
            />
            <View style={styles.cardInner}>
              <View style={[styles.levelTag, { borderColor: p.color }]}>
                <Text style={[styles.levelText, { color: p.color }]}>{p.level.toUpperCase()}</Text>
              </View>
              <Text style={styles.cardTitle}>{p.title}</Text>
              <Text style={styles.cardSub}>{p.tagline}</Text>
              <View style={styles.metaRow}>
                <Meta icon="library-outline" text={`${p.total_lessons} lessons`} />
                <Meta icon="time-outline" text={p.duration} />
                <Meta icon="trophy-outline" text={`${p.total_xp} XP`} />
              </View>
              <View style={styles.openBtn}>
                <Text style={styles.openBtnText}>Open path</Text>
                <Ionicons name="arrow-forward" size={14} color="#000" />
              </View>
            </View>
          </Pressable>
        ))}
      </ScrollView>
    </SafeAreaView>
  );
}

function Meta({ icon, text }: { icon: any; text: string }) {
  return (
    <View style={styles.metaItem}>
      <Ionicons name={icon} size={13} color="rgba(255,255,255,0.7)" />
      <Text style={styles.metaText}>{text}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  scroll: { padding: 20, paddingBottom: 110 },
  kicker: { fontSize: 11, fontWeight: "800", letterSpacing: 3, color: C.brand, marginBottom: 8, marginTop: 8 },
  h1: { fontSize: 32, fontWeight: "900", color: C.text, letterSpacing: -1 },
  sub: { color: C.textDim, fontSize: 14, marginTop: 8 },
  card: {
    height: 260, borderRadius: RADIUS.xl, overflow: "hidden", marginBottom: 16,
    borderWidth: 1, borderColor: C.border,
  },
  cardImg: { width: "100%", height: "100%", position: "absolute" },
  cardInner: { flex: 1, padding: 20, justifyContent: "flex-end" },
  levelTag: { alignSelf: "flex-start", borderWidth: 1, paddingHorizontal: 10, paddingVertical: 4, borderRadius: RADIUS.pill, marginBottom: 12 },
  levelText: { fontSize: 10, fontWeight: "800", letterSpacing: 2 },
  cardTitle: { color: "#fff", fontSize: 26, fontWeight: "900", letterSpacing: -0.5 },
  cardSub: { color: "rgba(255,255,255,0.75)", fontSize: 13, marginTop: 6 },
  metaRow: { flexDirection: "row", gap: 16, marginTop: 14 },
  metaItem: { flexDirection: "row", alignItems: "center", gap: 4 },
  metaText: { color: "rgba(255,255,255,0.7)", fontSize: 12 },
  openBtn: {
    backgroundColor: C.brand, alignSelf: "flex-start", paddingHorizontal: 16, paddingVertical: 10,
    borderRadius: RADIUS.pill, marginTop: 14, flexDirection: "row", alignItems: "center", gap: 8,
  },
  openBtnText: { color: "#000", fontWeight: "800", fontSize: 13 },
});
