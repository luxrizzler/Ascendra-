import React from "react";
import { View, Text, StyleSheet, Pressable } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { C, RADIUS } from "@/src/theme";

type Lesson = {
  id: string;
  title: string;
  duration_min?: number;
  xp?: number;
};

type Module = {
  id: string;
  title: string;
  lessons: Lesson[];
};

type Props = {
  modules: Module[];
  completedLessonIds: string[];
  pathColor: string;
  onOpenLesson: (lessonId: string) => void;
};

export function LearningJourneyMap({
  modules,
  completedLessonIds,
  pathColor,
  onOpenLesson,
}: Props) {
  const completed = new Set(completedLessonIds || []);
  const allLessons = modules.flatMap((module) => module.lessons);
  const nextLesson = allLessons.find((lesson) => !completed.has(lesson.id));
  const nextLessonId = nextLesson?.id;

  const isUnlocked = (lessonId: string, index: number) => {
    if (completed.has(lessonId)) return true;
    if (lessonId === nextLessonId) return true;
    if (index === 0 && completed.size === 0) return true;
    return false;
  };

  let globalIndex = 0;

  return (
    <View style={styles.wrap}>
      <View style={styles.headerRow}>
        <View style={{ flex: 1 }}>
          <Text style={styles.eyebrow}>YOUR JOURNEY TO MASTERY</Text>
          <Text style={styles.title}>Follow the trail. Build real skill.</Text>
          <Text style={styles.subtitle}>
            Completed lessons stay behind you. Your next recommended step is highlighted.
          </Text>
        </View>
        <Ionicons name="map" size={24} color={pathColor} />
      </View>

      <View style={styles.trail}>
        {modules.map((module, moduleIndex) => (
          <View key={module.id} style={styles.moduleSection}>
            <View style={styles.moduleBanner}>
              <View style={[styles.moduleBadge, { borderColor: pathColor }]}>
                <Text style={[styles.moduleBadgeText, { color: pathColor }]}>M{moduleIndex + 1}</Text>
              </View>
              <View style={{ flex: 1 }}>
                <Text style={styles.moduleLabel}>MODULE {moduleIndex + 1}</Text>
                <Text style={styles.moduleTitle}>{module.title}</Text>
              </View>
            </View>

            {module.lessons.map((lesson, lessonIndex) => {
              const index = globalIndex++;
              const done = completed.has(lesson.id);
              const current = lesson.id === nextLessonId;
              const unlocked = isUnlocked(lesson.id, index);
              const side = index % 2 === 0 ? "left" : "right";

              return (
                <View key={lesson.id} style={styles.stepRow}>
                  <View style={styles.connectorColumn}>
                    <View
                      style={[
                        styles.connector,
                        index === 0 && { opacity: 0 },
                        done || current ? { backgroundColor: pathColor } : null,
                      ]}
                    />
                    <Pressable
                      accessibilityRole="button"
                      accessibilityLabel={`${done ? "Completed" : current ? "Current" : unlocked ? "Available" : "Locked"} lesson: ${lesson.title}`}
                      disabled={!unlocked}
                      onPress={() => unlocked && onOpenLesson(lesson.id)}
                      style={[
                        styles.node,
                        { borderColor: done || current ? pathColor : C.borderStrong },
                        done && { backgroundColor: pathColor },
                        current && { backgroundColor: C.surface2, borderWidth: 3 },
                        !unlocked && { opacity: 0.55 },
                      ]}
                    >
                      <Ionicons
                        name={done ? "checkmark" : current ? "navigate" : unlocked ? "play" : "lock-closed"}
                        size={18}
                        color={done ? "#000" : current ? pathColor : C.textMuted}
                      />
                    </Pressable>
                    <View
                      style={[
                        styles.connector,
                        done ? { backgroundColor: pathColor } : null,
                      ]}
                    />
                  </View>

                  <View
                    style={[
                      styles.lessonCard,
                      side === "left" ? styles.cardLeft : styles.cardRight,
                      current && { borderColor: pathColor },
                    ]}
                  >
                    {current && (
                      <View style={[styles.youAreHere, { backgroundColor: pathColor }]}>
                        <Ionicons name="location" size={12} color="#000" />
                        <Text style={styles.youAreHereText}>YOU ARE HERE</Text>
                      </View>
                    )}
                    <Text style={styles.lessonState}>
                      {done ? "MASTERED" : current ? "NEXT STEP" : unlocked ? "AVAILABLE" : "LOCKED"}
                    </Text>
                    <Text style={styles.lessonTitle}>{lesson.title}</Text>
                    <Text style={styles.lessonMeta}>
                      {lesson.duration_min ? `${lesson.duration_min} min` : "Short lesson"}
                      {lesson.xp ? ` · ${lesson.xp} XP` : ""}
                    </Text>
                    {current && (
                      <Pressable
                        onPress={() => onOpenLesson(lesson.id)}
                        style={[styles.continueButton, { backgroundColor: pathColor }]}
                      >
                        <Text style={styles.continueButtonText}>Continue journey</Text>
                        <Ionicons name="arrow-forward" size={15} color="#000" />
                      </Pressable>
                    )}
                  </View>
                </View>
              );
            })}

            {moduleIndex < modules.length - 1 && (
              <View style={styles.checkpoint}>
                <Ionicons name="flag" size={18} color={pathColor} />
                <Text style={styles.checkpointText}>Checkpoint · Module {moduleIndex + 1} complete</Text>
              </View>
            )}
          </View>
        ))}

        <View style={styles.summitWrap}>
          <View style={[styles.summitIcon, { borderColor: pathColor }]}>
            <Ionicons name="trophy" size={24} color={pathColor} />
          </View>
          <Text style={styles.summitKicker}>THE SUMMIT</Text>
          <Text style={styles.summitTitle}>Mastery & Certification</Text>
          <Text style={styles.summitText}>
            Finish the journey to unlock your final mastery milestone and certificate.
          </Text>
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    marginTop: 20,
    backgroundColor: C.surface,
    borderRadius: RADIUS.xl,
    borderWidth: 1,
    borderColor: C.border,
    padding: 18,
  },
  headerRow: { flexDirection: "row", alignItems: "flex-start", gap: 14 },
  eyebrow: { color: C.textMuted, fontSize: 10, fontWeight: "900", letterSpacing: 2 },
  title: { color: C.text, fontSize: 21, fontWeight: "900", marginTop: 5 },
  subtitle: { color: C.textDim, fontSize: 13, lineHeight: 19, marginTop: 7 },
  trail: { marginTop: 18 },
  moduleSection: { marginBottom: 6 },
  moduleBanner: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    marginBottom: 8,
    paddingVertical: 8,
  },
  moduleBadge: {
    width: 42,
    height: 42,
    borderRadius: 21,
    borderWidth: 1,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: C.surface2,
  },
  moduleBadgeText: { fontWeight: "900", fontSize: 12 },
  moduleLabel: { color: C.textMuted, fontSize: 9, fontWeight: "900", letterSpacing: 2 },
  moduleTitle: { color: C.text, fontSize: 16, fontWeight: "800", marginTop: 3 },
  stepRow: {
    minHeight: 130,
    flexDirection: "row",
    alignItems: "stretch",
  },
  connectorColumn: {
    width: 48,
    alignItems: "center",
  },
  connector: {
    width: 3,
    flex: 1,
    minHeight: 16,
    backgroundColor: C.borderStrong,
    borderRadius: 2,
  },
  node: {
    width: 42,
    height: 42,
    borderRadius: 21,
    borderWidth: 2,
    backgroundColor: C.surface,
    alignItems: "center",
    justifyContent: "center",
  },
  lessonCard: {
    flex: 1,
    alignSelf: "center",
    backgroundColor: C.surface2,
    borderRadius: RADIUS.lg,
    borderWidth: 1,
    borderColor: C.border,
    padding: 14,
    marginVertical: 10,
    minWidth: 0,
  },
  cardLeft: { marginRight: 0 },
  cardRight: { marginRight: 0 },
  youAreHere: {
    alignSelf: "flex-start",
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: RADIUS.pill,
    marginBottom: 8,
  },
  youAreHereText: { color: "#000", fontSize: 9, fontWeight: "900", letterSpacing: 1 },
  lessonState: { color: C.textMuted, fontSize: 9, fontWeight: "900", letterSpacing: 1.5 },
  lessonTitle: { color: C.text, fontSize: 15, fontWeight: "800", marginTop: 4 },
  lessonMeta: { color: C.textMuted, fontSize: 11, marginTop: 5 },
  continueButton: {
    alignSelf: "flex-start",
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    paddingHorizontal: 12,
    paddingVertical: 9,
    borderRadius: RADIUS.pill,
    marginTop: 12,
  },
  continueButtonText: { color: "#000", fontSize: 12, fontWeight: "900" },
  checkpoint: {
    marginLeft: 48,
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    paddingVertical: 12,
    paddingHorizontal: 4,
  },
  checkpointText: { color: C.textMuted, fontSize: 11, fontWeight: "700" },
  summitWrap: {
    marginLeft: 48,
    marginTop: 16,
    alignItems: "center",
    padding: 18,
    borderWidth: 1,
    borderColor: C.border,
    borderRadius: RADIUS.lg,
    backgroundColor: C.surface2,
  },
  summitIcon: {
    width: 58,
    height: 58,
    borderRadius: 29,
    borderWidth: 2,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 10,
  },
  summitKicker: { color: C.textMuted, fontSize: 9, fontWeight: "900", letterSpacing: 2 },
  summitTitle: { color: C.text, fontSize: 17, fontWeight: "900", marginTop: 4 },
  summitText: { color: C.textDim, fontSize: 12, lineHeight: 18, textAlign: "center", marginTop: 6 },
});
