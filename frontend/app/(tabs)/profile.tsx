import { useCallback, useEffect, useState } from "react";
import { View, Text, StyleSheet, ScrollView, Pressable, RefreshControl } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useRouter, useFocusEffect } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { C, RADIUS } from "@/src/theme";
import { useAuth } from "@/src/context/AuthContext";
import { api } from "@/src/api";

export default function Profile() {
  const router = useRouter();
  const { user, logout, refresh } = useAuth();
  const [progress, setProgress] = useState<any>(null);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    const p = await api.get("/progress");
    setProgress(p);
  }, []);

  useEffect(() => { load(); }, [load]);
  useFocusEffect(useCallback(() => { load(); refresh(); }, [load, refresh]));

  const onRefresh = async () => {
    setRefreshing(true);
    try { await load(); await refresh(); } finally { setRefreshing(false); }
  };

  const onLogout = async () => {
    await logout();
    router.replace("/onboarding");
  };

  const tierLabel = (user?.tier || "free").toUpperCase();
  const tierColor = user?.tier === "free" ? C.textMuted : C.brand;

  return (
    <SafeAreaView style={styles.root} edges={["top"]}>
      <ScrollView
        contentContainerStyle={styles.scroll}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={C.brand} />}
      >
        <View style={styles.header}>
          <View style={styles.avatar}>
            <Text style={styles.avatarText}>
              {(user?.name || user?.email || "?").charAt(0).toUpperCase()}
            </Text>
          </View>
          <Text style={styles.name}>{user?.name || "Friend"}</Text>
          <Text style={styles.email}>{user?.email}</Text>
          <View style={[styles.tierTag, { borderColor: tierColor }]}>
            <Text style={[styles.tierText, { color: tierColor }]}>{tierLabel} TIER</Text>
          </View>
        </View>

        <View style={styles.statsGrid}>
          <Stat label="Day streak" value={progress?.streak_days ?? 0} icon="flame" color="#FF8A00" />
          <Stat label="Total XP" value={progress?.total_xp ?? 0} icon="trophy" color={C.brand} />
          <Stat label="Lessons" value={progress?.completed_lesson_ids?.length ?? 0} icon="checkmark-circle" color={C.success} />
          <Stat label="Member since" value={new Date(user?.created_at || Date.now()).getFullYear()} icon="calendar" color={C.info} />
        </View>

        <Section title="Account">
          <Row icon="card-outline" label="Subscription" value={tierLabel} onPress={() => router.push("/pricing")} testID="profile-subscription-row" />
          <Row icon="sparkles-outline" label="AI Tutor" value="Open chat" onPress={() => router.push("/(tabs)/tutor")} testID="profile-tutor-row" />
          <Row icon="planet-outline" label="Model Library" value="Browse" onPress={() => router.push("/(tabs)/models")} testID="profile-models-row" />
        </Section>

        <Section title="About">
          <View style={styles.row}>
            <Ionicons name="information-circle-outline" size={22} color={C.textDim} />
            <Text style={styles.rowLabel}>Version</Text>
            <Text style={styles.rowValue}>1.0.0</Text>
          </View>
        </Section>

        <Pressable testID="profile-logout-btn" onPress={onLogout} style={styles.logout}>
          <Ionicons name="log-out-outline" size={20} color={C.danger} />
          <Text style={styles.logoutText}>Sign out</Text>
        </Pressable>
      </ScrollView>
    </SafeAreaView>
  );
}

function Section({ title, children }: any) {
  return (
    <View style={{ marginTop: 24 }}>
      <Text style={styles.sectionTitle}>{title.toUpperCase()}</Text>
      <View style={styles.card}>{children}</View>
    </View>
  );
}

function Stat({ label, value, icon, color }: any) {
  return (
    <View style={styles.statCard}>
      <Ionicons name={icon} size={20} color={color} />
      <Text style={styles.statValue}>{value}</Text>
      <Text style={styles.statLabel}>{label}</Text>
    </View>
  );
}

function Row({ icon, label, value, onPress, testID }: any) {
  return (
    <Pressable testID={testID} onPress={onPress} style={styles.row}>
      <Ionicons name={icon} size={22} color={C.textDim} />
      <Text style={styles.rowLabel}>{label}</Text>
      <Text style={styles.rowValue}>{value}</Text>
      <Ionicons name="chevron-forward" size={18} color={C.textMuted} />
    </Pressable>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  scroll: { padding: 20, paddingBottom: 110 },
  header: { alignItems: "center", paddingVertical: 16 },
  avatar: { width: 80, height: 80, borderRadius: 40, backgroundColor: C.brand, alignItems: "center", justifyContent: "center" },
  avatarText: { color: "#000", fontWeight: "900", fontSize: 30 },
  name: { color: C.text, fontWeight: "800", fontSize: 22, marginTop: 12 },
  email: { color: C.textMuted, fontSize: 13, marginTop: 4 },
  tierTag: { borderWidth: 1, paddingHorizontal: 12, paddingVertical: 5, borderRadius: RADIUS.pill, marginTop: 12 },
  tierText: { fontSize: 11, fontWeight: "800", letterSpacing: 2 },
  statsGrid: { flexDirection: "row", flexWrap: "wrap", gap: 10, marginTop: 24 },
  statCard: { flexBasis: "48%", flexGrow: 1, padding: 14, backgroundColor: C.surface, borderRadius: RADIUS.lg, borderWidth: 1, borderColor: C.border },
  statValue: { color: C.text, fontWeight: "900", fontSize: 22, marginTop: 6 },
  statLabel: { color: C.textMuted, fontSize: 11, fontWeight: "600", marginTop: 2 },
  sectionTitle: { color: C.textMuted, fontSize: 11, fontWeight: "800", letterSpacing: 2, marginBottom: 10, marginLeft: 4 },
  card: { backgroundColor: C.surface, borderRadius: RADIUS.lg, borderWidth: 1, borderColor: C.border, overflow: "hidden" },
  row: { flexDirection: "row", alignItems: "center", paddingHorizontal: 16, paddingVertical: 14, gap: 12, borderBottomWidth: 1, borderColor: C.border },
  rowLabel: { color: C.text, fontSize: 15, flex: 1 },
  rowValue: { color: C.textDim, fontSize: 13 },
  logout: { flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 8, padding: 16, marginTop: 24 },
  logoutText: { color: C.danger, fontSize: 15, fontWeight: "700" },
});
