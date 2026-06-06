import { useEffect, useMemo, useState } from "react";
import {
  View, Text, StyleSheet, ScrollView, Pressable, ActivityIndicator, FlatList,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import { C, RADIUS } from "@/src/theme";
import { api } from "@/src/api";

type Model = {
  id: string; name: string; provider: string; category: string; color: string;
  tagline: string; description: string; use_cases: string[]; strengths: string; pricing_hint: string;
};

const CATEGORIES = ["All", "Text", "Image", "Video", "Audio", "Search", "Coding"];

export default function Models() {
  const [models, setModels] = useState<Model[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeCat, setActiveCat] = useState("All");
  const [selected, setSelected] = useState<Model | null>(null);

  useEffect(() => {
    api.get("/models").then((r) => setModels(r.models)).finally(() => setLoading(false));
  }, []);

  const filtered = useMemo(
    () => (activeCat === "All" ? models : models.filter((m) => m.category === activeCat)),
    [models, activeCat],
  );

  if (loading) {
    return (
      <View style={[styles.root, { alignItems: "center", justifyContent: "center" }]}>
        <ActivityIndicator color={C.brand} />
      </View>
    );
  }

  return (
    <SafeAreaView style={styles.root} edges={["top"]}>
      <View style={styles.headerWrap}>
        <Text style={styles.kicker}>AI MODEL LIBRARY</Text>
        <Text style={styles.h1}>Every model that matters</Text>
        <Text style={styles.sub}>22 frontier models. Pick the right tool for the job.</Text>

        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={styles.chipRow}
          style={{ marginTop: 16 }}
        >
          {CATEGORIES.map((cat) => {
            const active = activeCat === cat;
            return (
              <Pressable
                key={cat}
                testID={`models-chip-${cat.toLowerCase()}`}
                onPress={() => setActiveCat(cat)}
                style={[styles.chip, active && styles.chipActive]}
              >
                <Text style={[styles.chipText, active && styles.chipTextActive]}>{cat}</Text>
              </Pressable>
            );
          })}
        </ScrollView>
      </View>

      <FlatList
        data={filtered}
        keyExtractor={(m) => m.id}
        numColumns={2}
        columnWrapperStyle={{ gap: 12 }}
        contentContainerStyle={{ padding: 16, paddingBottom: 110, gap: 12 }}
        renderItem={({ item }) => (
          <Pressable
            testID={`model-card-${item.id}`}
            onPress={() => setSelected(item)}
            style={[styles.modelCard, { borderColor: item.color + "55" }]}
          >
            <View style={[styles.modelGlow, { backgroundColor: item.color + "22" }]} />
            <View style={[styles.modelDot, { backgroundColor: item.color }]} />
            <Text style={styles.modelName}>{item.name}</Text>
            <Text style={styles.modelProvider}>{item.provider}</Text>
            <Text style={styles.modelTagline} numberOfLines={3}>{item.tagline}</Text>
            <View style={styles.modelFooter}>
              <Text style={styles.modelCategory}>{item.category}</Text>
              <Text style={styles.modelPrice}>{item.pricing_hint}</Text>
            </View>
          </Pressable>
        )}
      />

      {selected && <ModelSheet model={selected} onClose={() => setSelected(null)} />}
    </SafeAreaView>
  );
}

function ModelSheet({ model, onClose }: { model: Model; onClose: () => void }) {
  return (
    <Pressable style={styles.backdrop} onPress={onClose}>
      <Pressable style={styles.sheet} onPress={(e) => e.stopPropagation()}>
        <View style={styles.sheetHandle} />
        <View style={{ flexDirection: "row", alignItems: "center", gap: 12, marginTop: 8 }}>
          <View style={[styles.modelDot, { backgroundColor: model.color, width: 24, height: 24, borderRadius: 12 }]} />
          <View style={{ flex: 1 }}>
            <Text style={styles.sheetTitle}>{model.name}</Text>
            <Text style={styles.sheetSub}>{model.provider} · {model.category}</Text>
          </View>
          <Pressable testID="model-sheet-close" onPress={onClose} hitSlop={12}>
            <Ionicons name="close" size={26} color={C.textDim} />
          </Pressable>
        </View>
        <ScrollView contentContainerStyle={{ paddingVertical: 18 }}>
          <Text style={styles.sheetTagline}>{model.tagline}</Text>
          <Text style={styles.sheetBody}>{model.description}</Text>
          <Text style={styles.sheetLabel}>STRENGTHS</Text>
          <Text style={styles.sheetBody}>{model.strengths}</Text>
          <Text style={styles.sheetLabel}>USE CASES</Text>
          {model.use_cases.map((u, i) => (
            <View key={i} style={{ flexDirection: "row", alignItems: "center", gap: 10, marginTop: 8 }}>
              <Ionicons name="checkmark-circle" size={18} color={model.color} />
              <Text style={styles.sheetBody}>{u}</Text>
            </View>
          ))}
        </ScrollView>
      </Pressable>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  headerWrap: { padding: 20, paddingBottom: 8 },
  kicker: { fontSize: 11, fontWeight: "800", letterSpacing: 3, color: C.brand, marginBottom: 8 },
  h1: { fontSize: 28, fontWeight: "900", color: C.text, letterSpacing: -0.8 },
  sub: { color: C.textDim, fontSize: 13, marginTop: 6 },
  chipRow: { gap: 8, paddingRight: 16 },
  chip: {
    paddingHorizontal: 14, height: 36, borderRadius: RADIUS.pill,
    backgroundColor: C.surface, borderWidth: 1, borderColor: C.border,
    alignItems: "center", justifyContent: "center", flexShrink: 0,
  },
  chipActive: { backgroundColor: C.brand, borderColor: C.brand },
  chipText: { color: C.textDim, fontSize: 13, fontWeight: "600" },
  chipTextActive: { color: "#000", fontWeight: "800" },
  modelCard: {
    flex: 1, padding: 16, borderRadius: RADIUS.lg, backgroundColor: C.surface,
    borderWidth: 1, overflow: "hidden",
    minHeight: 170,
  },
  modelGlow: { position: "absolute", top: -30, right: -30, width: 120, height: 120, borderRadius: 60 },
  modelDot: { width: 14, height: 14, borderRadius: 7, marginBottom: 12 },
  modelName: { color: C.text, fontWeight: "800", fontSize: 16, letterSpacing: -0.3 },
  modelProvider: { color: C.textMuted, fontSize: 11, marginTop: 2, fontWeight: "600" },
  modelTagline: { color: C.textDim, fontSize: 12, marginTop: 10, lineHeight: 17 },
  modelFooter: { flexDirection: "row", justifyContent: "space-between", marginTop: "auto", paddingTop: 12 },
  modelCategory: { color: C.textMuted, fontSize: 10, fontWeight: "700", letterSpacing: 1, textTransform: "uppercase" },
  modelPrice: { color: C.brand, fontSize: 10, fontWeight: "700", letterSpacing: 1, textTransform: "uppercase" },
  backdrop: { position: "absolute", top: 0, bottom: 0, left: 0, right: 0, backgroundColor: "rgba(0,0,0,0.7)", justifyContent: "flex-end" },
  sheet: { backgroundColor: C.surface, borderTopLeftRadius: 28, borderTopRightRadius: 28, padding: 20, maxHeight: "80%", borderTopWidth: 1, borderColor: C.border },
  sheetHandle: { width: 40, height: 4, borderRadius: 2, backgroundColor: C.borderStrong, alignSelf: "center", marginBottom: 12 },
  sheetTitle: { color: C.text, fontWeight: "900", fontSize: 22 },
  sheetSub: { color: C.textMuted, fontSize: 13, marginTop: 2 },
  sheetTagline: { color: C.brand, fontSize: 14, fontWeight: "700", marginBottom: 14 },
  sheetBody: { color: C.textDim, fontSize: 14, lineHeight: 22, marginTop: 2 },
  sheetLabel: { color: C.textMuted, fontSize: 11, fontWeight: "800", letterSpacing: 2, marginTop: 18, marginBottom: 4 },
});
