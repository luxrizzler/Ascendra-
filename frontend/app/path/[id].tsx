import { useCallback, useEffect, useState } from "react";
import {
  View, Text, StyleSheet, ScrollView, Pressable, Image, ActivityIndicator,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useLocalSearchParams, useRouter, useFocusEffect, Stack } from "expo-router";
import { LinearGradient } from "expo-linear-gradient";
import { Ionicons } from "@expo/vector-icons";
import { C, RADIUS } from "@/src/theme";
import { api } from "@/src/api";

export default function PathDetail() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const [path, setPath] = useState<any>(null);
  const [progress, setProgress] = useState<any>(null);

  const load = useCallback(async () => {
    const [p, prog] = await Promise.all([api.get(`/paths/${id}`), api.get("/progress")]);
    setPath(p);
    setProgress(prog);
  }, [id]);

  useEffect(() => { load(); }, [load]);
  useFocusEffect(useCallback(() => { load(); }, [load]));

  if (!path) {
    return (
      <View style={[styles.root, { alignItems: "center", justifyContent: "center" }]}>
        <ActivityIndicator color={C.brand} />
      </View>
    );
  }

  const completedSet = new Set<string>(progress?.completed_lesson_ids || []);
  const allLessons = path.modules.flatMap((m: any) => m.lessons);
  const totalLessons = allLessons.length;
  const completedInPath = allLessons.filter((l: any) => completedSet.has(l.id)).length;
  const pct = totalLessons ? Math.round((completedInPath / totalLessons) * 100) : 0;
  const nextLesson = allLessons.find((l: any) => !completedSet.has(l.id)) || allLessons[0];

  return (
    <View style={styles.root}>
      <Stack.Screen options={{ headerShown: false }} />
      <ScrollView contentContainerStyle={{ paddingBottom: 120 }} showsVerticalScrollIndicator={false}>
        <View style={styles.hero}>
          <Image source={{ uri: path.image }} style={StyleSheet.absoluteFillObject as any} />
          <LinearGradient
            colors={["rgba(0,0,0,0.2)", "rgba(0,0,0,0.4)", "rgba(10,10,10,1)"]}
            style={StyleSheet.absoluteFillObject}
          />
          <SafeAreaView edges={["top"]} style={{ padding: 20 }}>
            <Pressable testID="path-back-btn" onPress={() => router.back()} style={styles.back}>
              <Ionicons name="chevron-back" size={24} color="#fff" />
            </Pressable>
          </SafeAreaView>
          <View style={styles.heroBottom}>
            <View style={[styles.levelTag, { borderColor: path.color }]}>
              <Text style={[styles.levelText, { color: path.color }]}>{path.level.toUpperCase()}</Text>
            </View>
            <Text style={styles.heroTitle}>{path.title}</Text>
            <Text style={styles.heroSub}>{path.tagline}</Text>
            <View style={styles.metaRow}>
              <Text style={styles.metaText}>{path.modules.length} modules</Text>
              <View style={styles.dot} />
              <Text style={styles.metaText}>{totalLessons} lessons</Text>
              <View style={styles.dot} />
              <Text style={styles.metaText}>{path.duration}</Text>
            </View>
          </View>
        </View>

        <View style={styles.body}>
          <View style={styles.progressBox}>
            <View style={{ flex: 1 }}>
              <Text style={styles.progressKicker}>YOUR PROGRESS</Text>
              <Text style={styles.progressValue}>{completedInPath} / {totalLessons} lessons</Text>
              <View style={styles.progressTrack}>
                <View style={[styles.progressFill, { width: `${pct}%`, backgroundColor: path.color }]} />
              </View>
            </View>
            <Pressable
              testID="path-resume-btn"
              onPress={() => nextLesson && router.push(`/lesson/${nextLesson.id}`)}
              style={[styles.resumeBtn, { backgroundColor: path.color }]}
            >
              <Ionicons name={completedInPath > 0 ? "play" : "rocket"} size={16} color="#000" />
              <Text style={styles.resumeText}>{completedInPath > 0 ? "Resume" : "Start"}</Text>
            </Pressable>
          </View>

          {path.modules.map((m: any, mi: number) => (
            <View key={m.id} style={{ marginTop: 24 }}>
              <Text style={styles.moduleKicker}>MODULE {mi + 1}</Text>
              <Text style={styles.moduleTitle}>{m.title}</Text>

              {m.lessons.map((l: any, li: number) => {
                const done = completedSet.has(l.id);
                return (
                  <Pressable
                    key={l.id}
                    testID={`lesson-row-${l.id}`}
                    onPress={() => router.push(`/lesson/${l.id}`)}
                    style={styles.lessonRow}
                  >
                    <View style={[styles.lessonNum, done && { backgroundColor: path.color, borderColor: path.color }]}>
                      {done ? (
                        <Ionicons name="checkmark" size={16} color="#000" />
                      ) : (
                        <Text style={styles.lessonNumText}>{li + 1}</Text>
                      )}
                    </View>
                    <View style={{ flex: 1 }}>
                      <Text style={styles.lessonTitle}>{l.title}</Text>
                      <Text style={styles.lessonMeta}>{l.duration_min} min · {l.xp} XP · {l.card_count} cards</Text>
                    </View>
                    <Ionicons name="chevron-forward" size={18} color={C.textMuted} />
                  </Pressable>
                );
              })}
            </View>
          ))}
        </View>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  hero: { height: 320, justifyContent: "flex-end" },
  back: {
    width: 40, height: 40, borderRadius: 20, backgroundColor: "rgba(0,0,0,0.5)",
    alignItems: "center", justifyContent: "center",
  },
  heroBottom: { padding: 20, paddingBottom: 26 },
  levelTag: { alignSelf: "flex-start", borderWidth: 1, paddingHorizontal: 10, paddingVertical: 4, borderRadius: RADIUS.pill, marginBottom: 12 },
  levelText: { fontSize: 10, fontWeight: "800", letterSpacing: 2 },
  heroTitle: { color: "#fff", fontSize: 32, fontWeight: "900", letterSpacing: -1 },
  heroSub: { color: "rgba(255,255,255,0.7)", fontSize: 14, marginTop: 8 },
  metaRow: { flexDirection: "row", alignItems: "center", gap: 8, marginTop: 14 },
  metaText: { color: "rgba(255,255,255,0.6)", fontSize: 12 },
  dot: { width: 3, height: 3, borderRadius: 2, backgroundColor: "rgba(255,255,255,0.4)" },
  body: { padding: 20 },
  progressBox: {
    flexDirection: "row", gap: 12, padding: 16, backgroundColor: C.surface,
    borderRadius: RADIUS.lg, borderWidth: 1, borderColor: C.border,
  },
  progressKicker: { color: C.textMuted, fontSize: 10, fontWeight: "800", letterSpacing: 2 },
  progressValue: { color: C.text, fontWeight: "800", fontSize: 18, marginTop: 4 },
  progressTrack: { height: 4, backgroundColor: C.surface2, borderRadius: 2, marginTop: 10, overflow: "hidden" },
  progressFill: { height: 4, borderRadius: 2 },
  resumeBtn: {
    flexDirection: "row", alignItems: "center", gap: 6, paddingHorizontal: 16, paddingVertical: 12,
    borderRadius: RADIUS.pill, alignSelf: "center",
  },
  resumeText: { color: "#000", fontWeight: "800", fontSize: 13 },
  moduleKicker: { color: C.textMuted, fontSize: 10, fontWeight: "800", letterSpacing: 2, marginBottom: 4 },
  moduleTitle: { color: C.text, fontWeight: "800", fontSize: 19, marginBottom: 10 },
  lessonRow: {
    flexDirection: "row", alignItems: "center", gap: 14, padding: 14, marginTop: 8,
    backgroundColor: C.surface, borderRadius: RADIUS.lg, borderWidth: 1, borderColor: C.border,
  },
  lessonNum: {
    width: 32, height: 32, borderRadius: 16, borderWidth: 1, borderColor: C.border,
    alignItems: "center", justifyContent: "center",
  },
  lessonNumText: { color: C.textDim, fontWeight: "700" },
  lessonTitle: { color: C.text, fontWeight: "700", fontSize: 15 },
  lessonMeta: { color: C.textMuted, fontSize: 12, marginTop: 2 },
});
