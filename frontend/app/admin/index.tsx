import { useCallback, useEffect, useMemo, useState } from "react";
import {
  View, Text, StyleSheet, ScrollView, Pressable, ActivityIndicator, TextInput, Platform, Alert, RefreshControl,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useRouter } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { C, RADIUS } from "@/src/theme";
import { api } from "@/src/api";
import { useAuth } from "@/src/context/AuthContext";

type Tab = "overview" | "sales" | "users" | "traffic";

type Stats = {
  users: { total: number; paid: number; conversion_pct: number; signups_30d: number; by_tier: Record<string, number> };
  revenue: { total_usd: number; mtd_usd: number; arr_estimate_usd: number; paid_sessions: number; stripe_tax_enabled: boolean };
  engagement: { lessons_completed: number; certificates_issued: number; dau: number; wau: number };
  traffic: { pageviews_total: number; pageviews_24h: number; pageviews_7d: number; unique_visitors_7d: number };
};
type Sale = {
  session_id: string; user_id: string; user_email?: string; user_name?: string;
  tier: string; interval: string; amount_usd: number; currency: string; paid_at?: string; created_at?: string;
};
type AdminUser = {
  id: string; email: string; name?: string; tier: string; subscription_interval?: string;
  tier_expires_at?: string; is_admin: boolean; has_used_trial: boolean; must_change_password: boolean;
  auth_provider: string; created_at?: string; last_active_date?: string; total_xp?: number;
};

export default function AdminDashboard() {
  const router = useRouter();
  const { user, loading } = useAuth();
  const [tab, setTab] = useState<Tab>("overview");
  const [stats, setStats] = useState<Stats | null>(null);
  const [sales, setSales] = useState<Sale[]>([]);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [traffic, setTraffic] = useState<{ daily: any[]; top_paths: any[] } | null>(null);
  const [search, setSearch] = useState("");
  const [busy, setBusy] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [editing, setEditing] = useState<AdminUser | null>(null);

  // Permission guard
  useEffect(() => {
    if (loading) return;
    if (!user) { router.replace("/login"); return; }
    if (!user.is_admin) { router.replace("/(tabs)/home"); return; }
    if (user.must_change_password) { router.replace("/change-password"); return; }
  }, [user, loading, router]);

  const loadAll = useCallback(async () => {
    setBusy(true);
    try {
      const [s, sa, u, t] = await Promise.all([
        api.get("/admin/stats"),
        api.get("/admin/sales?limit=100"),
        api.get("/admin/users?limit=200"),
        api.get("/admin/traffic?days=14"),
      ]);
      setStats(s); setSales(sa.sales || []); setUsers(u.users || []); setTraffic(t);
    } catch (e: any) {
      Alert.alert("Admin", e?.message || "Failed to load");
    } finally { setBusy(false); }
  }, []);

  useEffect(() => { if (user?.is_admin) loadAll(); }, [user?.is_admin, loadAll]);

  const onRefresh = async () => {
    setRefreshing(true);
    try { await loadAll(); } finally { setRefreshing(false); }
  };

  const filteredUsers = useMemo(() => {
    if (!search) return users;
    const q = search.toLowerCase();
    return users.filter(u =>
      u.email.toLowerCase().includes(q) || (u.name || "").toLowerCase().includes(q));
  }, [users, search]);

  if (loading || !user || !user.is_admin) {
    return (
      <SafeAreaView style={styles.root}>
        <View style={styles.center}><ActivityIndicator color={C.brand} /></View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.root} edges={["top"]}>
      <View style={styles.header}>
        <View>
          <Text style={styles.brand}>ASCENDRA ACADEMY</Text>
          <Text style={styles.headerTitle}>Admin Console</Text>
        </View>
        <Pressable testID="admin-back-home" onPress={() => router.replace("/(tabs)/home")} style={styles.iconBtn}>
          <Ionicons name="home-outline" size={20} color={C.text} />
        </Pressable>
      </View>

      <View style={styles.tabs}>
        {(["overview", "sales", "users", "traffic"] as Tab[]).map((t) => (
          <Pressable
            key={t}
            testID={`admin-tab-${t}`}
            onPress={() => setTab(t)}
            style={[styles.tab, tab === t && styles.tabActive]}
          >
            <Text style={[styles.tabText, tab === t && styles.tabTextActive]}>{t.toUpperCase()}</Text>
          </Pressable>
        ))}
      </View>

      <ScrollView
        style={{ flex: 1 }}
        contentContainerStyle={{ padding: 16, paddingBottom: 80 }}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={C.brand} />}
      >
        {busy && !stats && <ActivityIndicator color={C.brand} style={{ marginTop: 40 }} />}

        {tab === "overview" && stats && <OverviewTab stats={stats} />}

        {tab === "sales" && (
          <View>
            <SectionHeader title="Recent Sales" subtitle={`Last ${sales.length} transactions`} />
            {sales.length === 0 ? (
              <EmptyHint icon="cash-outline" text="No sales yet. The first paid checkout will land here." />
            ) : (
              sales.map((s) => (
                <View key={s.session_id} style={styles.saleRow}>
                  <View style={styles.tierDot} />
                  <View style={{ flex: 1 }}>
                    <Text style={styles.saleTitle}>{s.user_email || s.user_id}</Text>
                    <Text style={styles.saleMeta}>
                      {(s.tier || "").toUpperCase()} · {s.interval || "monthly"} · {s.paid_at ? new Date(s.paid_at).toLocaleString() : "—"}
                    </Text>
                  </View>
                  <Text style={styles.saleAmount}>${s.amount_usd?.toFixed(2)}</Text>
                </View>
              ))
            )}
          </View>
        )}

        {tab === "users" && (
          <View>
            <View style={styles.searchRow}>
              <Ionicons name="search" size={16} color={C.textMuted} />
              <TextInput
                value={search}
                onChangeText={setSearch}
                placeholder="Search by email or name…"
                placeholderTextColor={C.textMuted}
                style={styles.searchInput}
                testID="admin-search"
              />
            </View>
            <Text style={styles.smallNote}>{filteredUsers.length} of {users.length} users</Text>
            {filteredUsers.map((u) => (
              <Pressable
                key={u.id}
                testID={`admin-user-${u.email}`}
                onPress={() => setEditing(u)}
                style={styles.userRow}
              >
                <View style={[styles.avatar, { backgroundColor: tierColor(u.tier) }]}>
                  <Text style={styles.avatarText}>{(u.name || u.email).charAt(0).toUpperCase()}</Text>
                </View>
                <View style={{ flex: 1, marginLeft: 12 }}>
                  <View style={{ flexDirection: "row", alignItems: "center", gap: 6, flexWrap: "wrap" }}>
                    <Text style={styles.userName}>{u.name || u.email}</Text>
                    {u.is_admin && <Pill text="ADMIN" color={C.brand} />}
                    {u.must_change_password && <Pill text="PW PENDING" color={C.lavender} />}
                  </View>
                  <Text style={styles.userMeta}>{u.email}</Text>
                  <Text style={styles.userMeta}>
                    {(u.tier || "").toUpperCase()} · XP {u.total_xp || 0} · {u.auth_provider}
                    {u.tier_expires_at ? ` · exp ${new Date(u.tier_expires_at).toLocaleDateString()}` : ""}
                  </Text>
                </View>
                <Ionicons name="chevron-forward" size={18} color={C.textMuted} />
              </Pressable>
            ))}
          </View>
        )}

        {tab === "traffic" && traffic && (
          <View>
            <SectionHeader title="Page Views (last 14 days)" subtitle="Anonymous lightweight tracker" />
            {traffic.daily.length === 0 ? (
              <EmptyHint icon="analytics-outline" text="No traffic data yet. Visit a few pages to populate." />
            ) : (
              <View style={styles.chartWrap}>
                <SimpleBarChart data={traffic.daily} />
              </View>
            )}

            <SectionHeader title="Top Pages" subtitle="Most-viewed paths" />
            {traffic.top_paths.length === 0 ? (
              <EmptyHint icon="podium-outline" text="No top-pages data yet." />
            ) : (
              traffic.top_paths.map((tp, i) => (
                <View key={i} style={styles.pathRow}>
                  <Text style={styles.pathIndex}>{i + 1}</Text>
                  <Text style={[styles.pathText, { flex: 1 }]} numberOfLines={1}>{tp.path}</Text>
                  <Text style={styles.pathViews}>{tp.views}</Text>
                </View>
              ))
            )}
          </View>
        )}
      </ScrollView>

      {editing && (
        <EditUserSheet
          user={editing}
          onClose={() => setEditing(null)}
          onSaved={() => { setEditing(null); loadAll(); }}
          onDeleted={() => { setEditing(null); loadAll(); }}
        />
      )}
    </SafeAreaView>
  );
}

// ───────── Overview Tab ─────────
function OverviewTab({ stats }: { stats: Stats }) {
  return (
    <View style={{ gap: 18 }}>
      <View style={styles.statsGrid}>
        <Metric label="Total revenue" value={`$${stats.revenue.total_usd.toFixed(2)}`} icon="cash" tint={C.brand} />
        <Metric label="MTD revenue" value={`$${stats.revenue.mtd_usd.toFixed(2)}`} icon="trending-up" tint={C.success} />
        <Metric label="ARR estimate" value={`$${stats.revenue.arr_estimate_usd.toFixed(0)}`} icon="rocket" tint={C.coral} />
        <Metric label="Paid sessions" value={stats.revenue.paid_sessions} icon="card" tint={C.lavender} />
      </View>

      <SectionHeader title="Customers" subtitle={`${stats.users.total} total · ${stats.users.conversion_pct}% paid`} />
      <View style={styles.statsGrid}>
        <Metric label="Total users" value={stats.users.total} icon="people" tint={C.text} />
        <Metric label="Paid users" value={stats.users.paid} icon="ribbon" tint={C.brand} />
        <Metric label="Signups 30d" value={stats.users.signups_30d} icon="person-add" tint={C.success} />
        <Metric label="Conversion" value={`${stats.users.conversion_pct}%`} icon="podium" tint={C.coral} />
      </View>

      <SectionHeader title="By tier" />
      <View style={{ gap: 8 }}>
        {Object.entries(stats.users.by_tier).map(([tier, count]) => (
          <View key={tier} style={styles.tierBar}>
            <View style={[styles.tierBarDot, { backgroundColor: tierColor(tier) }]} />
            <Text style={styles.tierBarText}>{tier.toUpperCase()}</Text>
            <Text style={styles.tierBarCount}>{count as number}</Text>
          </View>
        ))}
      </View>

      <SectionHeader title="Engagement" subtitle="Across all users" />
      <View style={styles.statsGrid}>
        <Metric label="Lessons completed" value={stats.engagement.lessons_completed} icon="checkmark-done" tint={C.success} />
        <Metric label="Certificates" value={stats.engagement.certificates_issued} icon="ribbon" tint={C.brand} />
        <Metric label="DAU" value={stats.engagement.dau} icon="sunny" tint={C.coral} />
        <Metric label="WAU" value={stats.engagement.wau} icon="calendar" tint={C.lavender} />
      </View>

      <SectionHeader title="Traffic (lifetime)" />
      <View style={styles.statsGrid}>
        <Metric label="Page views" value={stats.traffic.pageviews_total} icon="eye" tint={C.text} />
        <Metric label="24h views" value={stats.traffic.pageviews_24h} icon="time" tint={C.brand} />
        <Metric label="7d views" value={stats.traffic.pageviews_7d} icon="bar-chart" tint={C.success} />
        <Metric label="7d unique" value={stats.traffic.unique_visitors_7d} icon="people-circle" tint={C.lavender} />
      </View>

      <View style={styles.taxCard}>
        <View style={{ flexDirection: "row", alignItems: "center", gap: 10 }}>
          <Ionicons name={stats.revenue.stripe_tax_enabled ? "checkmark-circle" : "alert-circle"} size={22} color={stats.revenue.stripe_tax_enabled ? C.success : C.brand} />
          <Text style={styles.taxTitle}>Sales tax · {stats.revenue.stripe_tax_enabled ? "Enabled" : "Setup pending"}</Text>
        </View>
        <Text style={styles.taxBody}>
          {stats.revenue.stripe_tax_enabled
            ? "Stripe Tax is collecting & remitting sales tax on your behalf. Detailed tax reports are available in Stripe Dashboard → Reports → Tax."
            : "Once you add your real Stripe keys, enable Stripe Tax from Stripe Dashboard → Tax. Stripe will then auto-calculate the right tax for each customer's location and the totals will appear here."}
        </Text>
      </View>
    </View>
  );
}

// ───────── Edit User Sheet (admin can change anything) ─────────
function EditUserSheet({ user, onClose, onSaved, onDeleted }: {
  user: AdminUser; onClose: () => void; onSaved: () => void; onDeleted: () => void;
}) {
  const [name, setName] = useState(user.name || "");
  const [email, setEmail] = useState(user.email);
  const [tier, setTier] = useState(user.tier);
  const [isAdmin, setIsAdmin] = useState(user.is_admin);
  const [newPassword, setNewPassword] = useState("");
  const [busy, setBusy] = useState(false);

  const onSave = async () => {
    setBusy(true);
    try {
      const body: any = {};
      if (name !== (user.name || "")) body.name = name;
      if (email !== user.email) body.email = email;
      if (tier !== user.tier) body.tier = tier;
      if (isAdmin !== user.is_admin) body.is_admin = isAdmin;
      if (newPassword) {
        body.new_password = newPassword;
        body.must_change_password = true;
      }
      if (!Object.keys(body).length) { onClose(); return; }
      await api.patch(`/admin/users/${user.id}`, body);
      onSaved();
    } catch (e: any) {
      Alert.alert("Update failed", e?.message || "Could not save");
    } finally { setBusy(false); }
  };

  const onDelete = async () => {
    const ok = Platform.OS === "web"
      ? (typeof confirm !== "undefined" && confirm(`Delete ${user.email}? This cannot be undone.`))
      : await new Promise<boolean>((res) => {
          Alert.alert("Delete user?", `${user.email} will be permanently removed.`, [
            { text: "Cancel", onPress: () => res(false), style: "cancel" },
            { text: "Delete", onPress: () => res(true), style: "destructive" },
          ]);
        });
    if (!ok) return;
    setBusy(true);
    try {
      await api.del(`/admin/users/${user.id}`);
      onDeleted();
    } catch (e: any) {
      Alert.alert("Delete failed", e?.message || "Could not delete user");
    } finally { setBusy(false); }
  };

  return (
    <View style={styles.sheetOverlay}>
      <Pressable style={StyleSheet.absoluteFillObject as any} onPress={onClose} />
      <View style={styles.sheet}>
        <ScrollView contentContainerStyle={{ padding: 20, paddingBottom: 40 }}>
          <View style={styles.sheetHandle} />
          <Text style={styles.sheetTitle}>Edit user</Text>
          <Text style={styles.sheetSub}>{user.id}</Text>

          <Field label="Name" value={name} onChangeText={setName} placeholder="Display name" />
          <Field label="Email" value={email} onChangeText={setEmail} placeholder="user@example.com" autoCapitalize="none" />

          <Text style={styles.label}>Tier</Text>
          <View style={styles.tierRow}>
            {["free", "ascender", "pathfinder", "sage"].map((t) => (
              <Pressable key={t} onPress={() => setTier(t)}
                style={[styles.tierChip, tier === t && { borderColor: tierColor(t), backgroundColor: tierColor(t) + "22" }]}>
                <Text style={[styles.tierChipText, tier === t && { color: C.text }]}>{t.toUpperCase()}</Text>
              </Pressable>
            ))}
          </View>

          <Pressable onPress={() => setIsAdmin(!isAdmin)} style={styles.toggleRow}>
            <Ionicons name={isAdmin ? "checkmark-circle" : "ellipse-outline"} size={22} color={isAdmin ? C.brand : C.textMuted} />
            <Text style={styles.toggleText}>Make this user an admin</Text>
          </Pressable>

          <Field label="Set new password (optional)" value={newPassword} onChangeText={setNewPassword} placeholder="Leave empty to keep current" secureTextEntry />
          <Text style={styles.smallNote}>If you set a new password, the user will be prompted to change it on next login.</Text>

          <Pressable testID="admin-edit-save" onPress={onSave} disabled={busy} style={[styles.primaryBtn, busy && { opacity: 0.6 }]}>
            {busy ? <ActivityIndicator color="#000" /> : <Text style={styles.primaryBtnText}>Save changes</Text>}
          </Pressable>

          <Pressable testID="admin-edit-delete" onPress={onDelete} disabled={busy} style={styles.dangerBtn}>
            <Ionicons name="trash-outline" size={16} color={C.danger} />
            <Text style={styles.dangerBtnText}>Delete user</Text>
          </Pressable>

          <Pressable onPress={onClose} style={{ paddingVertical: 14, alignItems: "center" }}>
            <Text style={{ color: C.textDim }}>Close</Text>
          </Pressable>
        </ScrollView>
      </View>
    </View>
  );
}

// ───────── helpers ─────────
function tierColor(tier: string) {
  switch (tier) {
    case "sage": return C.brand;
    case "pathfinder": return C.coral;
    case "ascender": return C.lavender;
    default: return C.textMuted;
  }
}

function SimpleBarChart({ data }: { data: { date: string; views: number; uniques: number }[] }) {
  const max = Math.max(1, ...data.map(d => d.views));
  return (
    <View style={{ flexDirection: "row", alignItems: "flex-end", gap: 4, height: 140, paddingHorizontal: 8 }}>
      {data.map((d) => (
        <View key={d.date} style={{ flex: 1, alignItems: "center" }}>
          <View style={{ width: "100%", height: `${(d.views / max) * 100}%`, backgroundColor: C.brand, borderRadius: 4, minHeight: 2 }} />
          <Text style={{ color: C.textMuted, fontSize: 9, marginTop: 4 }}>{d.date.slice(5)}</Text>
        </View>
      ))}
    </View>
  );
}

function SectionHeader({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <View style={{ marginTop: 8, marginBottom: 8 }}>
      <Text style={styles.sectionTitle}>{title}</Text>
      {subtitle && <Text style={styles.sectionSub}>{subtitle}</Text>}
    </View>
  );
}

function Metric({ label, value, icon, tint }: any) {
  return (
    <View style={styles.metric}>
      <Ionicons name={icon} size={18} color={tint} />
      <Text style={styles.metricValue}>{value}</Text>
      <Text style={styles.metricLabel}>{label}</Text>
    </View>
  );
}

function Pill({ text, color }: { text: string; color: string }) {
  return (
    <View style={{ backgroundColor: color, paddingHorizontal: 6, paddingVertical: 2, borderRadius: 4 }}>
      <Text style={{ color: "#000", fontSize: 9, fontWeight: "900", letterSpacing: 0.8 }}>{text}</Text>
    </View>
  );
}

function Field({ label, ...props }: any) {
  return (
    <View style={{ marginBottom: 12 }}>
      <Text style={styles.label}>{label}</Text>
      <TextInput
        {...props}
        placeholderTextColor={C.textMuted}
        style={styles.input}
      />
    </View>
  );
}

function EmptyHint({ icon, text }: { icon: any; text: string }) {
  return (
    <View style={styles.empty}>
      <Ionicons name={icon} size={32} color={C.textMuted} />
      <Text style={styles.emptyText}>{text}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  center: { flex: 1, alignItems: "center", justifyContent: "center" },
  header: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", padding: 16, paddingBottom: 8 },
  brand: { color: C.brand, fontWeight: "900", fontSize: 10, letterSpacing: 3 },
  headerTitle: { color: C.text, fontWeight: "800", fontSize: 22, marginTop: 2 },
  iconBtn: { width: 40, height: 40, borderRadius: 20, alignItems: "center", justifyContent: "center", backgroundColor: C.surface, borderWidth: 1, borderColor: C.border },
  tabs: { flexDirection: "row", paddingHorizontal: 16, paddingBottom: 4, gap: 6 },
  tab: { paddingHorizontal: 12, paddingVertical: 8, borderRadius: RADIUS.pill, backgroundColor: C.surface, borderWidth: 1, borderColor: C.border },
  tabActive: { backgroundColor: C.brand, borderColor: C.brand },
  tabText: { color: C.textDim, fontSize: 11, fontWeight: "800", letterSpacing: 1 },
  tabTextActive: { color: "#000" },
  statsGrid: { flexDirection: "row", flexWrap: "wrap", gap: 10 },
  metric: { flexBasis: "48%", flexGrow: 1, padding: 14, backgroundColor: C.surface, borderRadius: RADIUS.lg, borderWidth: 1, borderColor: C.border },
  metricValue: { color: C.text, fontWeight: "900", fontSize: 24, marginTop: 6 },
  metricLabel: { color: C.textMuted, fontSize: 11, fontWeight: "600", marginTop: 2 },
  sectionTitle: { color: C.text, fontWeight: "800", fontSize: 16, marginTop: 12 },
  sectionSub: { color: C.textMuted, fontSize: 12, marginTop: 2 },
  tierBar: { flexDirection: "row", alignItems: "center", gap: 12, padding: 12, backgroundColor: C.surface, borderRadius: RADIUS.md, borderWidth: 1, borderColor: C.border },
  tierBarDot: { width: 8, height: 8, borderRadius: 4 },
  tierBarText: { color: C.textDim, fontWeight: "700", fontSize: 12, letterSpacing: 1, flex: 1 },
  tierBarCount: { color: C.text, fontWeight: "900", fontSize: 16 },
  taxCard: { padding: 14, backgroundColor: C.surface, borderRadius: RADIUS.lg, borderWidth: 1, borderColor: C.border },
  taxTitle: { color: C.text, fontWeight: "800", fontSize: 14 },
  taxBody: { color: C.textDim, fontSize: 12, marginTop: 8, lineHeight: 18 },
  saleRow: { flexDirection: "row", alignItems: "center", gap: 12, padding: 12, backgroundColor: C.surface, borderRadius: RADIUS.md, borderWidth: 1, borderColor: C.border, marginBottom: 8 },
  tierDot: { width: 6, height: 30, backgroundColor: C.brand, borderRadius: 3 },
  saleTitle: { color: C.text, fontWeight: "700", fontSize: 13 },
  saleMeta: { color: C.textMuted, fontSize: 11, marginTop: 2 },
  saleAmount: { color: C.success, fontWeight: "900", fontSize: 16 },
  searchRow: { flexDirection: "row", alignItems: "center", gap: 8, padding: 10, backgroundColor: C.surface, borderRadius: RADIUS.md, borderWidth: 1, borderColor: C.border, marginBottom: 8 },
  searchInput: { flex: 1, color: C.text, fontSize: 14, paddingVertical: 4, outlineWidth: 0 as any },
  smallNote: { color: C.textMuted, fontSize: 11, marginBottom: 8 },
  userRow: { flexDirection: "row", alignItems: "center", padding: 12, backgroundColor: C.surface, borderRadius: RADIUS.md, borderWidth: 1, borderColor: C.border, marginBottom: 8 },
  avatar: { width: 38, height: 38, borderRadius: 19, alignItems: "center", justifyContent: "center" },
  avatarText: { color: "#000", fontWeight: "900" },
  userName: { color: C.text, fontWeight: "700", fontSize: 14 },
  userMeta: { color: C.textMuted, fontSize: 11, marginTop: 2 },
  chartWrap: { backgroundColor: C.surface, padding: 14, borderRadius: RADIUS.lg, borderWidth: 1, borderColor: C.border, marginBottom: 12 },
  pathRow: { flexDirection: "row", alignItems: "center", gap: 10, padding: 10, backgroundColor: C.surface, borderRadius: RADIUS.md, borderWidth: 1, borderColor: C.border, marginBottom: 6 },
  pathIndex: { color: C.textMuted, fontWeight: "900", fontSize: 12, width: 22 },
  pathText: { color: C.text, fontSize: 12 },
  pathViews: { color: C.brand, fontWeight: "800", fontSize: 13 },
  empty: { alignItems: "center", padding: 24, gap: 8 },
  emptyText: { color: C.textMuted, fontSize: 12, textAlign: "center" },
  sheetOverlay: { position: "absolute", top: 0, left: 0, right: 0, bottom: 0, backgroundColor: "rgba(0,0,0,0.55)", justifyContent: "flex-end" },
  sheet: { backgroundColor: C.bg, borderTopLeftRadius: 24, borderTopRightRadius: 24, maxHeight: "92%", borderWidth: 1, borderColor: C.border },
  sheetHandle: { alignSelf: "center", width: 40, height: 4, backgroundColor: C.border, borderRadius: 2, marginBottom: 12 },
  sheetTitle: { color: C.text, fontWeight: "900", fontSize: 22 },
  sheetSub: { color: C.textMuted, fontSize: 11, marginTop: 2, marginBottom: 18 },
  label: { color: C.textMuted, fontSize: 11, fontWeight: "700", letterSpacing: 1.5, marginBottom: 8, textTransform: "uppercase" },
  input: { backgroundColor: C.surface, borderWidth: 1, borderColor: C.border, color: C.text, paddingHorizontal: 14, paddingVertical: 12, borderRadius: RADIUS.md, fontSize: 14 },
  tierRow: { flexDirection: "row", gap: 6, marginBottom: 16, flexWrap: "wrap" },
  tierChip: { paddingHorizontal: 10, paddingVertical: 6, borderRadius: RADIUS.pill, borderWidth: 1, borderColor: C.border, backgroundColor: C.surface },
  tierChipText: { color: C.textDim, fontWeight: "800", fontSize: 11, letterSpacing: 1 },
  toggleRow: { flexDirection: "row", alignItems: "center", gap: 10, paddingVertical: 12 },
  toggleText: { color: C.text, fontSize: 14 },
  primaryBtn: { backgroundColor: C.brand, paddingVertical: 14, borderRadius: RADIUS.lg, alignItems: "center", marginTop: 12 },
  primaryBtnText: { color: "#000", fontWeight: "900", fontSize: 15 },
  dangerBtn: { flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 6, padding: 14, marginTop: 6 },
  dangerBtnText: { color: C.danger, fontWeight: "700", fontSize: 13 },
});
