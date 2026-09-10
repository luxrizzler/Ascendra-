import React, { useEffect, useMemo, useRef } from "react";
import { Animated, Pressable, StyleSheet, Text, View } from "react-native";
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
  onOpenSideQuest?: (moduleId: string) => void;
};

type IconName = React.ComponentProps<typeof Ionicons>["name"];

const landmarks: { name: string; icon: IconName }[] = [
  { name: "AI Base Camp", icon: "bonfire-outline" },
  { name: "Prompting Pass", icon: "chatbubble-ellipses-outline" },
  { name: "Creator Canyon", icon: "color-palette-outline" },
  { name: "Automation Crossing", icon: "git-branch-outline" },
  { name: "Agent Ridge", icon: "hardware-chip-outline" },
  { name: "Builder's Peak", icon: "code-slash-outline" },
  { name: "Strategy Heights", icon: "compass-outline" },
];

function landmarkFor(title: string, index: number) {
  const value = title.toLowerCase();
  if (value.includes("prompt")) return landmarks[1];
  if (value.includes("creator") || value.includes("image") || value.includes("video")) return landmarks[2];
  if (value.includes("automat") || value.includes("workflow")) return landmarks[3];
  if (value.includes("agent")) return landmarks[4];
  if (value.includes("code") || value.includes("build") || value.includes("emergent")) return landmarks[5];
  if (value.includes("business") || value.includes("enterprise") || value.includes("strategy")) return landmarks[6];
  if (value.includes("fundament") || index === 0) return landmarks[0];
  return { name: `Waypoint ${index + 1}`, icon: "flag-outline" as IconName };
}

function questFor(title: string) {
  const value = title.toLowerCase();
  if (value.includes("prompt")) return "Turn a vague request into a clear, reusable prompt.";
  if (value.includes("automat") || value.includes("workflow")) return "Design a small workflow that removes one repetitive task.";
  if (value.includes("business")) return "Apply this module to a real business problem and defend your choices.";
  if (value.includes("creator") || value.includes("image") || value.includes("video")) return "Create a finished artifact using the skills from this stop.";
  if (value.includes("code") || value.includes("build")) return "Build a small working feature and explain how it works.";
  if (value.includes("agent")) return "Design an AI agent with a goal, tools, guardrails, and success test.";
  return "Use what you learned in this module to solve one realistic problem.";
}

function JourneyAvatar({ color }: { color: string }) {
  const hop = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(hop, { toValue: -5, duration: 550, useNativeDriver: true }),
        Animated.timing(hop, { toValue: 0, duration: 550, useNativeDriver: true }),
      ])
    );
    loop.start();
    return () => loop.stop();
  }, [hop]);

  return (
    <Animated.View style={[styles.avatar, { backgroundColor: color, transform: [{ translateY: hop }] }]}>
      <Ionicons name="person" size={16} color="#000" />
    </Animated.View>
  );
}

export function LearningJourneyMap({
  modules,
  completedLessonIds,
  pathColor,
  onOpenLesson,
  onOpenSideQuest,
}: Props) {
  const completed = useMemo(() => new Set(completedLessonIds || []), [completedLessonIds]);
  const allLessons = useMemo(() => modules.flatMap((module) => module.lessons), [modules]);
  const nextLesson = allLessons.find((lesson) => !completed.has(lesson.id));
  const nextLessonId = nextLesson?.id;
  const pathComplete = allLessons.length > 0 && allLessons.every((lesson) => completed.has(lesson.id));
  const completionPct = allLessons.length ? Math.round((completed.size / allLessons.length) * 100) : 0;

  let globalIndex = 0;

  return (
    <View style={styles.wrap}>
      <View style={styles.headerRow}>
        <View style={{ flex: 1 }}>
          <Text style={styles.eyebrow}>ASCENDRA ADVENTURE MAP</Text>
          <Text style={styles.title}>{pathComplete ? "You reached the summit." : "Your next step is already waiting."}</Text>
          <Text style={styles.subtitle}>
            Move landmark by landmark. Mastered lessons stay lit behind you, and Ascendra keeps your recommended next stop easy to find.
          </Text>
        </View>
        <Ionicons name="map" size={25} color={pathColor} />
      </View>

      <View style={styles.mapStats}>
        <View>
          <Text style={styles.statValue}>{completed.size}</Text>
          <Text style={styles.statLabel}>STOPS MASTERED</Text>
        </View>
        <View>
          <Text style={styles.statValue}>{Math.max(0, allLessons.length - completed.size)}</Text>
          <Text style={styles.statLabel}>STOPS AHEAD</Text>
        </View>
        <View>
          <Text style={[styles.statValue, { color: pathColor }]}>{completionPct}%</Text>
          <Text style={styles.statLabel}>JOURNEY</Text>
        </View>
      </View>

      <View style={styles.trail}>
        {modules.map((module, moduleIndex) => {
          const landmark = landmarkFor(module.title, moduleIndex);
          const moduleDone = module.lessons.length > 0 && module.lessons.every((lesson) => completed.has(lesson.id));
          const moduleStarted = module.lessons.some((lesson) => completed.has(lesson.id)) || module.lessons.some((lesson) => lesson.id === nextLessonId);

          return (
            <View key={module.id} style={styles.moduleSection}>
              <View style={[styles.landmarkCard, moduleStarted && { borderColor: pathColor }]}> 
                <View style={[styles.landmarkIcon, { borderColor: moduleDone ? pathColor : C.borderStrong }, moduleDone && { backgroundColor: pathColor }]}> 
                  <Ionicons name={moduleDone ? "checkmark" : landmark.icon} size={20} color={moduleDone ? "#000" : moduleStarted ? pathColor : C.textMuted} />
                </View>
                <View style={{ flex: 1 }}>
                  <Text style={styles.landmarkKicker}>LANDMARK {moduleIndex + 1}</Text>
                  <Text style={styles.landmarkName}>{landmark.name}</Text>
                  <Text style={styles.moduleTitle}>{module.title}</Text>
                </View>
                <Text style={[styles.landmarkState, moduleDone && { color: pathColor }]}>{moduleDone ? "CLEARED" : moduleStarted ? "ACTIVE" : "AHEAD"}</Text>
              </View>

              {module.lessons.map((lesson) => {
                const index = globalIndex++;
                const done = completed.has(lesson.id);
                const current = lesson.id === nextLessonId;
                const unlocked = done || current || (index === 0 && completed.size === 0);

                return (
                  <View key={lesson.id} style={[styles.stepRow, index % 2 ? styles.stepRight : styles.stepLeft]}>
                    <View style={styles.railColumn}>
                      <View style={[styles.connector, (done || current) && { backgroundColor: pathColor }]} />
                      <Pressable
                        accessibilityRole="button"
                        accessibilityLabel={`${done ? "Completed" : current ? "Current" : "Locked"} lesson: ${lesson.title}`}
                        disabled={!unlocked}
                        onPress={() => unlocked && onOpenLesson(lesson.id)}
                        style={[
                          styles.node,
                          { borderColor: done || current ? pathColor : C.borderStrong },
                          done && { backgroundColor: pathColor },
                          current && styles.currentNode,
                          !unlocked && styles.locked,
                        ]}
                      >
                        <Ionicons name={done ? "checkmark" : current ? "navigate" : "lock-closed"} size={18} color={done ? "#000" : current ? pathColor : C.textMuted} />
                      </Pressable>
                      <View style={[styles.connector, done && { backgroundColor: pathColor }]} />
                      {current && <JourneyAvatar color={pathColor} />}
                    </View>

                    <View style={[styles.lessonCard, current && { borderColor: pathColor }]}> 
                      {current && (
                        <View style={styles.currentRow}>
                          <View style={[styles.youAreHere, { backgroundColor: pathColor }]}>
                            <Ionicons name="location" size={12} color="#000" />
                            <Text style={styles.youAreHereText}>YOU ARE HERE</Text>
                          </View>
                          <View style={styles.recommendedBadge}>
                            <Ionicons name="sparkles" size={11} color={pathColor} />
                            <Text style={[styles.recommendedText, { color: pathColor }]}>ASCENDRA RECOMMENDS</Text>
                          </View>
                        </View>
                      )}
                      <Text style={styles.lessonState}>{done ? "MASTERED" : current ? "NEXT STEP" : "LOCKED"}</Text>
                      <Text style={styles.lessonTitle}>{lesson.title}</Text>
                      <Text style={styles.lessonMeta}>
                        {lesson.duration_min ? `${lesson.duration_min} min` : "Short lesson"}{lesson.xp ? ` · ${lesson.xp} XP` : ""}
                      </Text>
                      {current && (
                        <Pressable onPress={() => onOpenLesson(lesson.id)} style={[styles.continueButton, { backgroundColor: pathColor }]}> 
                          <Text style={styles.continueButtonText}>Continue journey</Text>
                          <Ionicons name="arrow-forward" size={15} color="#000" />
                        </Pressable>
                      )}
                    </View>
                  </View>
                );
              })}

              <View style={[styles.checkpoint, moduleDone && { borderColor: pathColor }]}> 
                <Ionicons name={moduleDone ? "flag" : "flag-outline"} size={18} color={moduleDone ? pathColor : C.textMuted} />
                <View style={{ flex: 1 }}>
                  <Text style={styles.checkpointTitle}>{moduleDone ? "Checkpoint reached" : "Checkpoint ahead"}</Text>
                  <Text style={styles.checkpointText}>{moduleDone ? `${landmark.name} mastered. Your side quest is unlocked.` : `Complete ${landmark.name} to unlock its optional challenge.`}</Text>
                </View>
              </View>

              <View style={[styles.questCard, !moduleDone && styles.lockedQuest]}> 
                <View style={styles.questIcon}><Ionicons name={moduleDone ? "flash" : "lock-closed"} size={18} color={moduleDone ? pathColor : C.textMuted} /></View>
                <View style={{ flex: 1 }}>
                  <Text style={[styles.questKicker, moduleDone && { color: pathColor }]}>{moduleDone ? "OPTIONAL SIDE QUEST UNLOCKED" : "SIDE QUEST LOCKED"}</Text>
                  <Text style={styles.questText}>{questFor(module.title)}</Text>
                </View>
                {moduleDone && onOpenSideQuest && (
                  <Pressable accessibilityRole="button" accessibilityLabel={`Open side quest for ${module.title}`} onPress={() => onOpenSideQuest(module.id)} style={[styles.questButton, { borderColor: pathColor }]}> 
                    <Ionicons name="arrow-forward" size={17} color={pathColor} />
                  </Pressable>
                )}
              </View>
            </View>
          );
        })}

        <View style={[styles.summitWrap, pathComplete && { borderColor: pathColor }]}> 
          <View style={[styles.summitIcon, { borderColor: pathColor }, pathComplete && { backgroundColor: pathColor }]}> 
            <Ionicons name={pathComplete ? "trophy" : "lock-closed"} size={26} color={pathComplete ? "#000" : pathColor} />
          </View>
          <Text style={[styles.summitKicker, pathComplete && { color: pathColor }]}>{pathComplete ? "SUMMIT REACHED" : "THE SUMMIT"}</Text>
          <Text style={styles.summitTitle}>Mastery & Certification</Text>
          <Text style={styles.summitText}>
            {pathComplete ? "You completed every required stop. Your certification milestone is now earned through Ascendra's existing certificate system." : "Master the required stops to reach the summit. Future V2 mastery challenges will make this a practical final demonstration, not just a finish line."}
          </Text>
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { marginTop: 20, backgroundColor: C.surface, borderRadius: RADIUS.xl, borderWidth: 1, borderColor: C.border, padding: 18 },
  headerRow: { flexDirection: "row", alignItems: "flex-start", gap: 14 },
  eyebrow: { color: C.textMuted, fontSize: 10, fontWeight: "900", letterSpacing: 2 },
  title: { color: C.text, fontSize: 21, fontWeight: "900", marginTop: 5 },
  subtitle: { color: C.textDim, fontSize: 13, lineHeight: 19, marginTop: 7 },
  mapStats: { marginTop: 16, padding: 13, backgroundColor: C.surface2, borderRadius: RADIUS.lg, flexDirection: "row", justifyContent: "space-between", borderWidth: 1, borderColor: C.border },
  statValue: { color: C.text, fontSize: 18, fontWeight: "900" },
  statLabel: { color: C.textMuted, fontSize: 8, fontWeight: "900", letterSpacing: 1.2, marginTop: 2 },
  trail: { marginTop: 18 },
  moduleSection: { marginBottom: 18 },
  landmarkCard: { flexDirection: "row", alignItems: "center", gap: 11, padding: 13, borderWidth: 1, borderColor: C.border, borderRadius: RADIUS.lg, backgroundColor: C.surface2 },
  landmarkIcon: { width: 44, height: 44, borderRadius: 22, borderWidth: 2, alignItems: "center", justifyContent: "center", backgroundColor: C.surface },
  landmarkKicker: { color: C.textMuted, fontSize: 8, fontWeight: "900", letterSpacing: 1.6 },
  landmarkName: { color: C.text, fontSize: 17, fontWeight: "900", marginTop: 2 },
  moduleTitle: { color: C.textDim, fontSize: 12, fontWeight: "700", marginTop: 2 },
  landmarkState: { color: C.textMuted, fontSize: 9, fontWeight: "900", letterSpacing: 1 },
  stepRow: { minHeight: 132, flexDirection: "row", alignItems: "stretch" },
  stepLeft: { paddingRight: 10 },
  stepRight: { paddingLeft: 10 },
  railColumn: { width: 50, alignItems: "center", position: "relative" },
  connector: { width: 3, flex: 1, minHeight: 15, backgroundColor: C.borderStrong, borderRadius: 2 },
  node: { width: 42, height: 42, borderRadius: 21, borderWidth: 2, backgroundColor: C.surface, alignItems: "center", justifyContent: "center" },
  currentNode: { backgroundColor: C.surface2, borderWidth: 3 },
  locked: { opacity: 0.48 },
  avatar: { position: "absolute", top: 6, right: -8, width: 30, height: 30, borderRadius: 15, alignItems: "center", justifyContent: "center", borderWidth: 2, borderColor: C.bg },
  lessonCard: { flex: 1, alignSelf: "center", backgroundColor: C.surface2, borderRadius: RADIUS.lg, borderWidth: 1, borderColor: C.border, padding: 14, marginVertical: 10, minWidth: 0 },
  currentRow: { flexDirection: "row", flexWrap: "wrap", gap: 6, alignItems: "center", marginBottom: 8 },
  youAreHere: { flexDirection: "row", alignItems: "center", gap: 4, paddingHorizontal: 8, paddingVertical: 4, borderRadius: RADIUS.pill },
  youAreHereText: { color: "#000", fontSize: 8, fontWeight: "900", letterSpacing: 1 },
  recommendedBadge: { flexDirection: "row", alignItems: "center", gap: 4, paddingHorizontal: 7, paddingVertical: 4, borderRadius: RADIUS.pill, borderWidth: 1, borderColor: C.borderStrong },
  recommendedText: { fontSize: 7, fontWeight: "900", letterSpacing: 0.7 },
  lessonState: { color: C.textMuted, fontSize: 9, fontWeight: "900", letterSpacing: 1.5 },
  lessonTitle: { color: C.text, fontSize: 15, fontWeight: "800", marginTop: 4 },
  lessonMeta: { color: C.textMuted, fontSize: 11, marginTop: 5 },
  continueButton: { alignSelf: "flex-start", flexDirection: "row", alignItems: "center", gap: 6, paddingHorizontal: 12, paddingVertical: 9, borderRadius: RADIUS.pill, marginTop: 12 },
  continueButtonText: { color: "#000", fontSize: 12, fontWeight: "900" },
  checkpoint: { flexDirection: "row", alignItems: "center", gap: 9, padding: 12, borderWidth: 1, borderColor: C.border, borderRadius: RADIUS.md, backgroundColor: C.surface2, marginTop: 5 },
  checkpointTitle: { color: C.text, fontSize: 12, fontWeight: "800" },
  checkpointText: { color: C.textMuted, fontSize: 10, lineHeight: 15, marginTop: 2 },
  questCard: { flexDirection: "row", alignItems: "center", gap: 10, padding: 12, borderRadius: RADIUS.md, borderWidth: 1, borderColor: C.border, marginTop: 8 },
  lockedQuest: { opacity: 0.52 },
  questIcon: { width: 34, height: 34, borderRadius: 17, backgroundColor: C.surface2, alignItems: "center", justifyContent: "center" },
  questKicker: { color: C.textMuted, fontSize: 8, fontWeight: "900", letterSpacing: 1.2 },
  questText: { color: C.textDim, fontSize: 11, lineHeight: 16, marginTop: 3 },
  questButton: { width: 38, height: 38, borderRadius: 19, borderWidth: 1, alignItems: "center", justifyContent: "center" },
  summitWrap: { marginTop: 16, alignItems: "center", padding: 18, borderWidth: 1, borderColor: C.border, borderRadius: RADIUS.lg, backgroundColor: C.surface2 },
  summitIcon: { width: 62, height: 62, borderRadius: 31, borderWidth: 2, alignItems: "center", justifyContent: "center", marginBottom: 10 },
  summitKicker: { color: C.textMuted, fontSize: 9, fontWeight: "900", letterSpacing: 2 },
  summitTitle: { color: C.text, fontSize: 18, fontWeight: "900", marginTop: 4 },
  summitText: { color: C.textDim, fontSize: 12, lineHeight: 18, textAlign: "center", marginTop: 6 },
});
