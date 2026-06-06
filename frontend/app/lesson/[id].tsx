import { useEffect, useState } from "react";
import {
  View, Text, StyleSheet, Pressable, ScrollView, ActivityIndicator, useWindowDimensions,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useLocalSearchParams, useRouter, Stack } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { LinearGradient } from "expo-linear-gradient";
import { C, RADIUS } from "@/src/theme";
import { api } from "@/src/api";

type Card = { kind: string; title: string; body: string };
type Quiz = { question: string; options: string[]; answer_index: number; explanation: string };

export default function Lesson() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const { width } = useWindowDimensions();

  const [lesson, setLesson] = useState<any>(null);
  const [idx, setIdx] = useState(0);
  const [quizPick, setQuizPick] = useState<number | null>(null);
  const [revealed, setRevealed] = useState(false);
  const [done, setDone] = useState(false);
  const [issuedCertId, setIssuedCertId] = useState<string | null>(null);

  useEffect(() => { api.get(`/lessons/${id}`).then(setLesson); }, [id]);

  if (!lesson) {
    return (
      <View style={[styles.root, { alignItems: "center", justifyContent: "center" }]}>
        <ActivityIndicator color={C.brand} />
      </View>
    );
  }

  const cards: Card[] = lesson.cards;
  const quiz: Quiz = lesson.quiz;
  const totalSteps = cards.length + 1; // +1 for quiz
  const isQuiz = idx >= cards.length;
  const color = lesson.path_color || C.brand;
  const progress = (Math.min(idx + 1, totalSteps) / totalSteps) * 100;

  const onNext = () => {
    if (isQuiz) return;
    setIdx((i) => i + 1);
  };
  const onPrev = () => {
    if (idx === 0) {
      router.back();
      return;
    }
    setIdx((i) => i - 1);
    setRevealed(false);
    setQuizPick(null);
  };
  const onSubmitQuiz = async () => {
    setRevealed(true);
  };
  const onFinish = async () => {
    try {
      const result = await api.post("/progress/complete", { lesson_id: lesson.id });
      if (result?.certificates_issued?.length) {
        setIssuedCertId(result.certificates_issued[0]);
      }
    } catch {}
    setDone(true);
  };

  if (done) {
    return (
      <SafeAreaView style={styles.root}>
        <Stack.Screen options={{ headerShown: false }} />
        <View style={styles.doneWrap}>
          <View style={[styles.doneIcon, { backgroundColor: color }]}>
            <Ionicons name={issuedCertId ? "ribbon" : "trophy"} size={48} color="#000" />
          </View>
          <Text style={styles.doneTitle}>{issuedCertId ? "Path mastered!" : "Nice work!"}</Text>
          <Text style={styles.doneSub}>+{lesson.xp} XP earned</Text>
          <Text style={styles.doneNote}>
            {issuedCertId
              ? `You finished the entire "${lesson.path_title || ''}" path. A certificate has been added to your profile.`
              : `You finished "${lesson.title}".`}
          </Text>
          <View style={{ height: 40 }} />
          {issuedCertId && (
            <Pressable
              testID="lesson-view-cert-btn"
              onPress={() => router.replace(`/certificate/${issuedCertId}`)}
              style={[styles.primaryBtn, { backgroundColor: color, marginBottom: 12 }]}
            >
              <Ionicons name="ribbon" size={18} color="#000" />
              <Text style={styles.primaryBtnText}>View my certificate</Text>
            </Pressable>
          )}
          <Pressable testID="lesson-back-to-path-btn" onPress={() => router.replace(`/path/${lesson.path_id}`)} style={[styles.primaryBtn, issuedCertId ? { backgroundColor: C.surface, borderWidth: 1, borderColor: C.borderStrong } : { backgroundColor: color }]}>
            <Text style={[styles.primaryBtnText, issuedCertId ? { color: C.text } : null]}>Back to path</Text>
            <Ionicons name="arrow-forward" size={18} color={issuedCertId ? C.text : "#000"} />
          </Pressable>
          <Pressable testID="lesson-back-to-home-btn" onPress={() => router.replace("/(tabs)/home")} style={{ paddingVertical: 16, alignItems: "center" }}>
            <Text style={{ color: C.textDim }}>Back to home</Text>
          </Pressable>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.root}>
      <Stack.Screen options={{ headerShown: false }} />
      <View style={styles.header}>
        <Pressable testID="lesson-prev-btn" onPress={onPrev} style={styles.iconBtn}>
          <Ionicons name="chevron-back" size={24} color={C.text} />
        </Pressable>
        <View style={styles.progressTrack}>
          <View style={[styles.progressFill, { width: `${progress}%`, backgroundColor: color }]} />
        </View>
        <Pressable testID="lesson-close-btn" onPress={() => router.back()} style={styles.iconBtn}>
          <Ionicons name="close" size={24} color={C.text} />
        </Pressable>
      </View>

      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
        {!isQuiz ? (
          <>
            <Text style={styles.module}>{lesson.module_title}</Text>
            <Text style={[styles.lessonTitle, { color: color }]}>{lesson.title}</Text>
            <View style={styles.cardWrap}>
              <LinearGradient
                colors={[color + "22", "transparent"]}
                style={styles.cardGlow}
              />
              <Text style={styles.cardKicker}>CARD {idx + 1} OF {cards.length}</Text>
              <Text style={styles.cardTitle}>{cards[idx].title}</Text>
              <Text style={styles.cardBody}>{cards[idx].body}</Text>
            </View>
          </>
        ) : (
          <>
            <Text style={styles.module}>QUIZ TIME</Text>
            <Text style={[styles.lessonTitle, { color: color }]}>One quick check</Text>
            <View style={styles.cardWrap}>
              <LinearGradient colors={[color + "22", "transparent"]} style={styles.cardGlow} />
              <Text style={styles.cardKicker}>QUESTION</Text>
              <Text style={styles.cardTitle}>{quiz.question}</Text>
              <View style={{ height: 18 }} />
              {quiz.options.map((opt, i) => {
                const picked = quizPick === i;
                const correct = revealed && i === quiz.answer_index;
                const wrong = revealed && picked && i !== quiz.answer_index;
                return (
                  <Pressable
                    key={i}
                    testID={`quiz-option-${i}`}
                    onPress={() => !revealed && setQuizPick(i)}
                    style={[
                      styles.quizOpt,
                      picked && !revealed && { borderColor: color, backgroundColor: color + "15" },
                      correct && { borderColor: C.success, backgroundColor: "rgba(16,185,129,0.12)" },
                      wrong && { borderColor: C.danger, backgroundColor: "rgba(239,68,68,0.12)" },
                    ]}
                  >
                    <Text style={styles.quizOptText}>{opt}</Text>
                    {correct && <Ionicons name="checkmark-circle" size={20} color={C.success} />}
                    {wrong && <Ionicons name="close-circle" size={20} color={C.danger} />}
                  </Pressable>
                );
              })}
              {revealed && (
                <View style={styles.explainBox}>
                  <Text style={styles.explainLabel}>WHY</Text>
                  <Text style={styles.explainText}>{quiz.explanation}</Text>
                </View>
              )}
            </View>
          </>
        )}
      </ScrollView>

      <View style={styles.footer}>
        {!isQuiz ? (
          <Pressable testID="lesson-next-btn" onPress={onNext} style={[styles.primaryBtn, { backgroundColor: color }]}>
            <Text style={styles.primaryBtnText}>{idx === cards.length - 1 ? "To the quiz" : "Next card"}</Text>
            <Ionicons name="arrow-forward" size={18} color="#000" />
          </Pressable>
        ) : !revealed ? (
          <Pressable
            testID="quiz-submit-btn"
            onPress={onSubmitQuiz}
            disabled={quizPick === null}
            style={[styles.primaryBtn, { backgroundColor: color }, quizPick === null && { opacity: 0.4 }]}
          >
            <Text style={styles.primaryBtnText}>Check answer</Text>
          </Pressable>
        ) : (
          <Pressable testID="quiz-finish-btn" onPress={onFinish} style={[styles.primaryBtn, { backgroundColor: color }]}>
            <Text style={styles.primaryBtnText}>Finish lesson · +{lesson.xp} XP</Text>
            <Ionicons name="trophy" size={18} color="#000" />
          </Pressable>
        )}
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  header: { flexDirection: "row", alignItems: "center", gap: 12, padding: 16 },
  iconBtn: { width: 36, height: 36, alignItems: "center", justifyContent: "center" },
  progressTrack: { flex: 1, height: 4, backgroundColor: C.surface2, borderRadius: 2, overflow: "hidden" },
  progressFill: { height: 4, borderRadius: 2 },
  scroll: { padding: 20, paddingBottom: 40 },
  module: { color: C.textMuted, fontSize: 11, fontWeight: "800", letterSpacing: 2.5, marginBottom: 6 },
  lessonTitle: { fontSize: 26, fontWeight: "900", letterSpacing: -0.8, marginBottom: 24 },
  cardWrap: { backgroundColor: C.surface, padding: 24, borderRadius: RADIUS.xl, borderWidth: 1, borderColor: C.border, overflow: "hidden", minHeight: 320 },
  cardGlow: { position: "absolute", top: -60, left: -40, right: -40, height: 180 },
  cardKicker: { color: C.textMuted, fontSize: 11, fontWeight: "800", letterSpacing: 2.5, marginBottom: 10 },
  cardTitle: { color: C.text, fontSize: 22, fontWeight: "800", letterSpacing: -0.4 },
  cardBody: { color: C.textDim, fontSize: 16, lineHeight: 26, marginTop: 14 },
  quizOpt: {
    flexDirection: "row", alignItems: "center", justifyContent: "space-between",
    padding: 14, borderRadius: RADIUS.md, backgroundColor: C.surface2,
    borderWidth: 1, borderColor: C.border, marginTop: 10,
  },
  quizOptText: { color: C.text, fontSize: 15, flex: 1 },
  explainBox: { marginTop: 18, padding: 14, borderRadius: RADIUS.md, backgroundColor: "rgba(255,255,255,0.04)" },
  explainLabel: { color: C.brand, fontSize: 10, fontWeight: "800", letterSpacing: 2, marginBottom: 6 },
  explainText: { color: C.textDim, fontSize: 14, lineHeight: 22 },
  footer: { padding: 16, borderTopWidth: 1, borderColor: C.border },
  primaryBtn: { backgroundColor: C.brand, paddingVertical: 16, borderRadius: RADIUS.lg, alignItems: "center", flexDirection: "row", justifyContent: "center", gap: 8 },
  primaryBtnText: { color: "#000", fontWeight: "800", fontSize: 16 },
  doneWrap: { flex: 1, alignItems: "center", justifyContent: "center", padding: 24 },
  doneIcon: { width: 110, height: 110, borderRadius: 55, alignItems: "center", justifyContent: "center", marginBottom: 24 },
  doneTitle: { color: C.text, fontWeight: "900", fontSize: 32, letterSpacing: -1 },
  doneSub: { color: C.brand, fontSize: 18, fontWeight: "800", marginTop: 10 },
  doneNote: { color: C.textDim, fontSize: 14, marginTop: 16, textAlign: "center" },
});
