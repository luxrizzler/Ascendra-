import { useCallback, useEffect, useState } from "react";
import {
  View, Text, StyleSheet, ScrollView, Pressable, RefreshControl, ActivityIndicator, Image,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useRouter, useFocusEffect } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { LinearGradient } from "expo-linear-gradient";
import { C, RADIUS } from "@/src/theme";
import { useAuth } from "@/src/context/AuthContext";
import { api } from "@/src/api";

type PathSummary = {
  id: string; title: string; subtitle: string; tagline: string; color: string;
  level: string; duration: string; image: string; total_lessons: number; total_xp: number; module_count: number;
};

type Progress = { completed_lesson_ids: string[]; total_xp: number; streak_days: number; last_active_date: string | null };

export default function Home() {
  const router = useRouter();
  const { user } = useAuth();
  const [paths, setPaths] = useState<PathSummary[]>([]);
  const [progress, setProgress] = useState<Progress | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    const [p, prog] = await Promise.all([api.get("/paths"), api.get("/progress")]);
    setPaths(p.paths);
    setProgress(prog);
  }, []);

  useEffect(() => { load().finally(() => setLoading(false)); }, [load]);

  useFocusEffect(useCallback(() => { load(); }, [load]));

  const onRefresh = async () => {
    setRefreshing(true);
    try { await load(); } finally { setRefreshing(false); }
  };

  // Pick "continue" path - first path with incomplete lessons, otherwise first
  const completedSet = new Set(progress?.completed_lesson_ids || []);
  const continuePath =
    paths.find((p) => completedSet.size > 0 && completedSet.size < p.total_lessons) ||
    paths[0];

  if (loading) {
    return (
      <View style={[styles.root, { alignItems: "center", justifyContent: "center" }]}>
        <ActivityIndicator color={C.brand} />
      </View>
    );
  }

  const goalLabel = user?.goal ? ` · ${user.goal[0].toUpperCase() + user.goal.slice(1)}` : "";

  return (
    <SafeAreaView style={styles.root} edges={["top"]}>
      <ScrollView
        contentContainerStyle={styles.scroll}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={C.brand} />}
        showsVerticalScrollIndicator={false}
      >
        {/* Header */}
        <View style={styles.header}>
          <View>
            <Text style={styles.kicker}>HELLO{goalLabel.toUpperCase()}</Text>
            <Text style={styles.greeting}>Ready to rise today, {user?.name?.split(" ")[0] || "friend"}? ✨</Text>
          </View>
          <Pressable testID="home-profile-btn" onPress={() => router.push("/(tabs)/profile")} style={styles.avatar}>
            <Text style={styles.avatarText}>{(user?.name || user?.email || "?").charAt(0).toUpperCase()}</Text>
          </Pressable>
        </View>

        {/* Stats Row */}
        <View style={styles.statsRow}>
          <Stat icon="flame" value={progress?.streak_days || 0} label="Day streak" color="#FF8A00" />
          <Stat icon="trophy" value={progress?.total_xp || 0} label="XP earned" color={C.brand} />
          <Stat icon="checkmark-circle" value={progress?.completed_lesson_ids.length || 0} label="Lessons" color={C.success} />
        </View>

        {/* Continue Card */}
        {continuePath && (
          <Pressable
            testID="continue-learning-card"
            onPress={() => router.push(`/path/${continuePath.id}`)}
            style={styles.continueCard}
          >
            <Image source={{ uri: continuePath.image }} style={styles.continueImg} />
            <LinearGradient
              colors={["rgba(0,0,0,0.0)", "rgba(0,0,0,0.4)", "rgba(0,0,0,0.95)"]}
              style={StyleSheet.absoluteFillObject}
            />
            <View style={styles.continueInner}>
              <Text style={[styles.miniKicker, { color: continuePath.color }]}>CONTINUE LEARNING</Text>
              <Text style={styles.continueTitle}>{continuePath.title}</Text>
              <Text style={styles.continueSub}>
                {continuePath.module_count} modules · {continuePath.total_lessons} lessons · {continuePath.duration}
              </Text>
              <View style={styles.continueBtn}>
                <Text style={styles.continueBtnText}>Resume</Text>
                <Ionicons name="play" size={14} color="#000" />
              </View>
            </View>
          </Pressable>
        )}

        {/* All Paths */}
        <View style={styles.sectionHead}>
          <Text style={styles.sectionTitle}>All paths</Text>
          <Pressable onPress={() => router.push("/(tabs)/paths")}>
            <Text style={{ color: C.brand, fontWeight: "700" }}>See all</Text>
          </Pressable>
        </View>

        {paths.map((p) => {
          const completedHere = p.module_count > 0
            ? (progress?.completed_lesson_ids || []).filter((id) => id.startsWith(p.id[0])).length
            : 0;
          const pct = p.total_lessons ? Math.min(100, Math.round((completedHere / p.total_lessons) * 100)) : 0;
          return (
            <Pressable
              key={p.id}
              testID={`path-card-${p.id}`}
              onPress={() => router.push(`/path/${p.id}`)}
              style={styles.pathRow}
            >
              <View style={[styles.pathDot, { backgroundColor: p.color }]} />
              <View style={{ flex: 1 }}>
                <Text style={styles.pathRowTitle}>{p.title}</Text>
                <Text style={styles.pathRowSub}>{p.total_lessons} lessons · {p.duration}</Text>
                <View style={styles.progressTrack}>
                  <View style={[styles.progressFill, { width: `${pct}%`, backgroundColor: p.color }]} />
                </View>
              </View>
              <Ionicons name="chevron-forward" size={20} color={C.textMuted} />
            </Pressable>
          );
        })}

        {/* AI Tutor CTA */}
        <Pressable testID="home-tutor-cta" onPress={() => router.push("/(tabs)/tutor")} style={styles.tutorCard}>
          <View style={styles.tutorIcon}>
            <Ionicons name="sparkles" size={26} color="#000" />
          </View>
          <View style={{ flex: 1 }}>
            <Text style={styles.tutorTitle}>Ask Ascendra, your AI partner</Text>
            <Text style={styles.tutorSub}>Powered by Claude Sonnet 4.5. Ask anything about AI.</Text>
          </View>
          <Ionicons name="arrow-forward" size={20} color={C.brand} />
        </Pressable>

        {user?.tier === "free" && (
          <Pressable testID="home-upgrade-cta" onPress={() => router.push("/pricing")} style={styles.upgradeCard}>
            <View>
              <Text style={styles.upgradeKicker}>UPGRADE</Text>
              <Text style={styles.upgradeTitle}>Unlock all paths & unlimited tutor</Text>
              <Text style={styles.upgradeSub}>From $19.99/mo. Cancel anytime.</Text>
            </View>
            <Ionicons name="rocket" size={28} color={C.brand} />
          </Pressable>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

function Stat({ icon, value, label, color }: { icon: any; value: number; label: string; color: string }) {
  return (
    <View style={styles.statCard}>
      <Ionicons name={icon} size={20} color={color} />
      <Text style={styles.statValue}>{value}</Text>
      <Text style={styles.statLabel}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  scroll: { padding: 20, paddingBottom: 110 },
  header: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginBottom: 24 },
  kicker: { fontSize: 11, fontWeight: "800", letterSpacing: 3, color: C.brand, marginBottom: 6 },
  greeting: { fontSize: 26, fontWeight: "900", color: C.text, letterSpacing: -0.8 },
  avatar: {
    width: 42, height: 42, borderRadius: 21, backgroundColor: C.brand,
    alignItems: "center", justifyContent: "center",
  },
  avatarText: { color: "#000", fontWeight: "900", fontSize: 16 },
  statsRow: { flexDirection: "row", gap: 10, marginBottom: 24 },
  statCard: { flex: 1, backgroundColor: C.surface, borderRadius: RADIUS.lg, padding: 14, borderWidth: 1, borderColor: C.border },
  statValue: { color: C.text, fontWeight: "900", fontSize: 22, marginTop: 6, letterSpacing: -0.5 },
  statLabel: { color: C.textMuted, fontSize: 11, fontWeight: "600", marginTop: 2 },
  continueCard: {
    height: 220, borderRadius: RADIUS.xl, overflow: "hidden", marginBottom: 28,
    borderWidth: 1, borderColor: C.border,
  },
  continueImg: { width: "100%", height: "100%", position: "absolute" },
  continueInner: { flex: 1, padding: 20, justifyContent: "flex-end" },
  miniKicker: { fontSize: 10, fontWeight: "800", letterSpacing: 2.5, marginBottom: 6 },
  continueTitle: { color: "#fff", fontSize: 28, fontWeight: "900", letterSpacing: -0.5 },
  continueSub: { color: "rgba(255,255,255,0.7)", fontSize: 13, marginTop: 6 },
  continueBtn: {
    backgroundColor: C.brand, alignSelf: "flex-start", paddingHorizontal: 16, paddingVertical: 10,
    borderRadius: RADIUS.pill, marginTop: 14, flexDirection: "row", alignItems: "center", gap: 8,
  },
  continueBtnText: { color: "#000", fontWeight: "800", fontSize: 13 },
  sectionHead: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 14 },
  sectionTitle: { color: C.text, fontSize: 20, fontWeight: "800", letterSpacing: -0.5 },
  pathRow: {
    flexDirection: "row", alignItems: "center", gap: 14, padding: 14,
    backgroundColor: C.surface, borderRadius: RADIUS.lg, marginBottom: 10, borderWidth: 1, borderColor: C.border,
  },
  pathDot: { width: 12, height: 50, borderRadius: 6 },
  pathRowTitle: { color: C.text, fontWeight: "700", fontSize: 15 },
  pathRowSub: { color: C.textMuted, fontSize: 12, marginTop: 2 },
  progressTrack: { height: 4, backgroundColor: C.surface2, borderRadius: 2, marginTop: 8, overflow: "hidden" },
  progressFill: { height: 4, borderRadius: 2 },
  tutorCard: {
    flexDirection: "row", alignItems: "center", gap: 14, padding: 18,
    backgroundColor: C.brandDim, borderRadius: RADIUS.xl, marginTop: 20, borderWidth: 1, borderColor: "rgba(255,176,0,0.3)",
  },
  tutorIcon: {
    width: 50, height: 50, borderRadius: 25, backgroundColor: C.brand,
    alignItems: "center", justifyContent: "center",
  },
  tutorTitle: { color: C.text, fontSize: 16, fontWeight: "800" },
  tutorSub: { color: C.textDim, fontSize: 12, marginTop: 2 },
  upgradeCard: {
    flexDirection: "row", alignItems: "center", justifyContent: "space-between", padding: 18,
    backgroundColor: C.surface, borderRadius: RADIUS.xl, marginTop: 14, borderWidth: 1, borderColor: C.borderStrong,
  },
  upgradeKicker: { fontSize: 10, fontWeight: "800", letterSpacing: 2.5, color: C.brand, marginBottom: 4 },
  upgradeTitle: { color: C.text, fontSize: 16, fontWeight: "800" },
  upgradeSub: { color: C.textMuted, fontSize: 12, marginTop: 2 },
});
