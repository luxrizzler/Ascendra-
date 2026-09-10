import { useState } from "react";
import { ActivityIndicator, Pressable, StyleSheet, Text, TextInput, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";

import { api } from "@/src/api";
import { C, RADIUS } from "@/src/theme";

type Action = "explain" | "practice" | "evaluate" | "question";

type Props = {
  lessonId?: string;
  lessonTitle: string;
  conceptText: string;
  accentColor?: string;
};

export function AdaptiveCoachPanel({ lessonId, lessonTitle, conceptText, accentColor }: Props) {
  const color = accentColor || C.brand;
  const [reply, setReply] = useState<string | null>(null);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [lastAction, setLastAction] = useState<Action | null>(null);

  const run = async (action: Action, learnerMessage?: string) => {
    setLoading(true);
    try {
      const result = await api.post("/v2/coach", {
        lesson_id: lessonId,
        lesson_title: lessonTitle,
        concept_text: conceptText,
        action,
        learner_message: learnerMessage || undefined,
      });
      setReply(result.reply);
      setLastAction(action);
      setMessage("");
    } catch (e: any) {
      setReply(e?.message || "Ascendra Live Guide is temporarily unavailable.");
      setLastAction(action);
    } finally {
      setLoading(false);
    }
  };

  const submit = () => {
    const cleaned = message.trim();
    if (!cleaned) return;
    const action: Action = lastAction === "practice" ? "evaluate" : "question";
    run(action, cleaned);
  };

  return (
    <View style={styles.wrap}>
      <View style={styles.headingRow}>
        <View style={[styles.icon, { backgroundColor: color + "22" }]}>
          <Ionicons name="chatbubbles" size={17} color={color} />
        </View>
        <View style={{ flex: 1 }}>
          <Text style={styles.title}>Ask Ascendra</Text>
          <Text style={styles.subtitle}>Your instructor adapts to what you need right now.</Text>
        </View>
      </View>

      <View style={styles.quickRow}>
        <Pressable disabled={loading} onPress={() => run("explain")} style={styles.quickBtn}>
          <Ionicons name="bulb-outline" size={16} color={C.text} />
          <Text style={styles.quickText}>Explain differently</Text>
        </Pressable>
        <Pressable disabled={loading} onPress={() => run("practice")} style={styles.quickBtn}>
          <Ionicons name="construct-outline" size={16} color={C.text} />
          <Text style={styles.quickText}>Let me try it</Text>
        </Pressable>
      </View>

      {loading && (
        <View style={styles.replyBox}>
          <ActivityIndicator color={color} />
          <Text style={styles.thinking}>Ascendra is thinking about how to teach this best…</Text>
        </View>
      )}

      {!loading && reply && (
        <View style={styles.replyBox}>
          <Text style={[styles.replyLabel, { color }]}>ASCENDRA LIVE GUIDE</Text>
          <Text style={styles.reply}>{reply}</Text>
        </View>
      )}

      <View style={styles.inputRow}>
        <TextInput
          value={message}
          onChangeText={setMessage}
          onSubmitEditing={submit}
          placeholder={lastAction === "practice" ? "Type your attempt here…" : "Ask anything about this concept…"}
          placeholderTextColor={C.textMuted}
          style={styles.input}
          multiline
        />
        <Pressable
          disabled={loading || !message.trim()}
          onPress={submit}
          style={[styles.send, { backgroundColor: color }, (loading || !message.trim()) && styles.disabled]}
        >
          <Ionicons name="arrow-up" size={18} color="#000" />
        </Pressable>
      </View>

      {lastAction === "practice" && !loading && (
        <Text style={styles.hint}>Try the challenge above, then send your answer. Ascendra will coach the attempt instead of simply giving you the solution.</Text>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    marginTop: 18,
    padding: 16,
    borderRadius: RADIUS.lg,
    backgroundColor: C.surface,
    borderWidth: 1,
    borderColor: C.border,
  },
  headingRow: { flexDirection: "row", alignItems: "center", gap: 10 },
  icon: { width: 36, height: 36, borderRadius: 18, alignItems: "center", justifyContent: "center" },
  title: { color: C.text, fontSize: 16, fontWeight: "900" },
  subtitle: { color: C.textMuted, fontSize: 12, lineHeight: 17, marginTop: 2 },
  quickRow: { flexDirection: "row", gap: 8, marginTop: 14 },
  quickBtn: { flex: 1, minHeight: 44, borderRadius: RADIUS.md, backgroundColor: C.surface2, borderWidth: 1, borderColor: C.border, flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 6, paddingHorizontal: 8 },
  quickText: { color: C.text, fontWeight: "700", fontSize: 12 },
  replyBox: { marginTop: 14, padding: 14, borderRadius: RADIUS.md, backgroundColor: C.surface2, borderWidth: 1, borderColor: C.border },
  replyLabel: { fontSize: 10, fontWeight: "900", letterSpacing: 1.6, marginBottom: 7 },
  reply: { color: C.textDim, fontSize: 14, lineHeight: 22 },
  thinking: { color: C.textMuted, fontSize: 12, textAlign: "center", marginTop: 8 },
  inputRow: { flexDirection: "row", alignItems: "flex-end", gap: 8, marginTop: 12 },
  input: { flex: 1, minHeight: 46, maxHeight: 120, borderRadius: RADIUS.md, backgroundColor: C.surface2, borderWidth: 1, borderColor: C.border, color: C.text, paddingHorizontal: 13, paddingVertical: 11, fontSize: 14 },
  send: { width: 46, height: 46, borderRadius: RADIUS.md, alignItems: "center", justifyContent: "center" },
  disabled: { opacity: 0.35 },
  hint: { color: C.textMuted, fontSize: 11, lineHeight: 16, marginTop: 10 },
});
