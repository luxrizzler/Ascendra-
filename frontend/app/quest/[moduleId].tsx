import { useEffect, useMemo, useState } from "react";
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Stack, useLocalSearchParams, useRouter } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { api } from "@/src/api";
import { C, RADIUS } from "@/src/theme";

export default function SideQuest() {
  const { moduleId, pathId } = useLocalSearchParams<{ moduleId: string; pathId?: string }>();
  const router = useRouter();
  const [path, setPath] = useState<any>(null);
  const [challenge, setChallenge] = useState("");
  const [attempt, setAttempt] = useState("");
  const [feedback, setFeedback] = useState("");
  const [loading, setLoading] = useState(true);
  const [evaluating, setEvaluating] = useState(false);

  const module = useMemo(() => path?.modules?.find((item: any) => item.id === moduleId), [path, moduleId]);

  useEffect(() => {
    if (!pathId) {
      setLoading(false);
      return;
    }
    api.get(`/paths/${pathId}`).then(setPath).catch(() => setLoading(false));
  }, [pathId]);

  useEffect(() => {
    if (!module) return;
    const lessonSummary = module.lessons.map((lesson: any) => lesson.title).join("; ");
    api.post("/v2/coach", {
      lesson_title: `${module.title} — Side Quest`,
      concept_text: `This side quest covers the skills represented by these lessons: ${lessonSummary}`,
      action: "practice",
    }).then((result) => {
      setChallenge(result.reply);
      setLoading(false);
    }).catch((error) => {
      setChallenge(error?.message || "Ascendra could not prepare this side quest right now.");
      setLoading(false);
    });
  }, [module]);

  const submitAttempt = async () => {
    const cleaned = attempt.trim();
    if (!cleaned || !module) return;
    setEvaluating(true);
    try {
      const result = await api.post("/v2/coach", {
        lesson_title: `${module.title} — Side Quest`,
        concept_text: challenge,
        action: "evaluate",
        learner_message: cleaned,
      });
      setFeedback(result.reply);
    } catch (error: any) {
      setFeedback(error?.message || "Ascendra could not evaluate the attempt right now.");
    } finally {
      setEvaluating(false);
    }
  };

  return (
    <SafeAreaView style={styles.root}>
      <Stack.Screen options={{ headerShown: false }} />
      <View style={styles.header}>
        <Pressable accessibilityRole="button" accessibilityLabel="Back to learning map" onPress={() => router.back()} style={styles.back}>
          <Ionicons name="chevron-back" size={23} color={C.text} />
        </Pressable>
        <View style={{ flex: 1 }}>
          <Text style={styles.kicker}>ASCENDRA SIDE QUEST</Text>
          <Text style={styles.title}>{module?.title || "Optional Challenge"}</Text>
        </View>
        <Ionicons name="flash" size={24} color={C.brand} />
      </View>

      <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
        <View style={styles.explainCard}>
          <Ionicons name="compass-outline" size={21} color={C.brand} />
          <Text style={styles.explainText}>Side quests are optional. They turn what you just learned into something you have to think through and apply.</Text>
        </View>

        <View style={styles.questCard}>
          <Text style={styles.questKicker}>YOUR CHALLENGE</Text>
          {loading ? (
            <View style={styles.loadingRow}>
              <ActivityIndicator color={C.brand} />
              <Text style={styles.loadingText}>Ascendra is building a challenge from this module…</Text>
            </View>
          ) : (
            <Text style={styles.challenge}>{challenge}</Text>
          )}
        </View>

        {!loading && module && (
          <>
            <Text style={styles.answerLabel}>SHOW ASCENDRA HOW YOU'D SOLVE IT</Text>
            <TextInput
              value={attempt}
              onChangeText={setAttempt}
              placeholder="Explain your approach, write your prompt, or paste your solution here…"
              placeholderTextColor={C.textMuted}
              multiline
              style={styles.input}
            />
            <Pressable
              disabled={evaluating || !attempt.trim()}
              onPress={submitAttempt}
              style={[styles.submit, (evaluating || !attempt.trim()) && styles.disabled]}
            >
              {evaluating ? <ActivityIndicator color="#000" /> : <Ionicons name="sparkles" size={17} color="#000" />}
              <Text style={styles.submitText}>{evaluating ? "Reviewing…" : "Coach my attempt"}</Text>
            </Pressable>
          </>
        )}

        {!!feedback && (
          <View style={styles.feedback}>
            <Text style={styles.feedbackKicker}>ASCENDRA COACHING</Text>
            <Text style={styles.feedbackText}>{feedback}</Text>
            <Text style={styles.feedbackHint}>You can revise your answer above and submit again. The goal is improvement, not getting it perfect on the first try.</Text>
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  header: { flexDirection: "row", alignItems: "center", gap: 12, padding: 18, borderBottomWidth: 1, borderColor: C.border },
  back: { width: 42, height: 42, borderRadius: 21, alignItems: "center", justifyContent: "center", backgroundColor: C.surface },
  kicker: { color: C.brand, fontSize: 9, fontWeight: "900", letterSpacing: 1.8 },
  title: { color: C.text, fontSize: 18, fontWeight: "900", marginTop: 2 },
  scroll: { padding: 20, paddingBottom: 70 },
  explainCard: { flexDirection: "row", gap: 10, padding: 14, borderRadius: RADIUS.lg, backgroundColor: C.surface, borderWidth: 1, borderColor: C.border },
  explainText: { flex: 1, color: C.textDim, fontSize: 13, lineHeight: 20 },
  questCard: { marginTop: 18, padding: 20, borderRadius: RADIUS.xl, backgroundColor: C.surface, borderWidth: 1, borderColor: C.borderStrong, minHeight: 170 },
  questKicker: { color: C.brand, fontSize: 9, fontWeight: "900", letterSpacing: 1.8 },
  loadingRow: { flex: 1, alignItems: "center", justifyContent: "center", gap: 10, paddingVertical: 24 },
  loadingText: { color: C.textMuted, fontSize: 12, textAlign: "center" },
  challenge: { color: C.text, fontSize: 17, lineHeight: 27, fontWeight: "650", marginTop: 14 },
  answerLabel: { color: C.textMuted, fontSize: 9, fontWeight: "900", letterSpacing: 1.6, marginTop: 22, marginBottom: 8 },
  input: { minHeight: 150, borderRadius: RADIUS.lg, backgroundColor: C.surface, borderWidth: 1, borderColor: C.border, color: C.text, padding: 15, fontSize: 15, lineHeight: 22, textAlignVertical: "top" },
  submit: { minHeight: 50, marginTop: 12, borderRadius: RADIUS.lg, backgroundColor: C.brand, flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 8 },
  submitText: { color: "#000", fontSize: 14, fontWeight: "900" },
  disabled: { opacity: 0.4 },
  feedback: { marginTop: 18, padding: 18, borderRadius: RADIUS.lg, backgroundColor: C.surface2, borderWidth: 1, borderColor: C.borderStrong },
  feedbackKicker: { color: C.brand, fontSize: 9, fontWeight: "900", letterSpacing: 1.8 },
  feedbackText: { color: C.textDim, fontSize: 14, lineHeight: 22, marginTop: 9 },
  feedbackHint: { color: C.textMuted, fontSize: 11, lineHeight: 17, marginTop: 12 },
});
