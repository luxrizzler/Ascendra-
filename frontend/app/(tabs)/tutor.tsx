import { useEffect, useRef, useState } from "react";
import {
  View, Text, StyleSheet, TextInput, Pressable, FlatList, KeyboardAvoidingView, Platform, ActivityIndicator,
} from "react-native";
import { SafeAreaView, useSafeAreaInsets } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import { C, RADIUS } from "@/src/theme";
import { api } from "@/src/api";

type Msg = { role: "user" | "assistant"; content: string };

const SUGGESTIONS = [
  "Compare GPT-5.2 vs Claude Sonnet 4.5",
  "How do I start a one-person SaaS with AI?",
  "Best AI tool for video ads?",
  "Write me a daily prompt routine",
];

export default function Tutor() {
  const insets = useSafeAreaInsets();
  const [messages, setMessages] = useState<Msg[]>([
    { role: "assistant", content: "Hey, I'm Aida — your AI tutor 👋\n\nAsk me anything about AI: which model to use, how to prompt better, how to ship an AI side hustle. What's on your mind today?" },
  ]);
  const [input, setInput] = useState("");
  const [sessionId, setSessionId] = useState<string | undefined>();
  const [sending, setSending] = useState(false);
  const listRef = useRef<FlatList>(null);

  const send = async (textOverride?: string) => {
    const text = (textOverride ?? input).trim();
    if (!text || sending) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", content: text }]);
    setSending(true);
    try {
      const resp = await api.post("/tutor/chat", { message: text, session_id: sessionId });
      setSessionId(resp.session_id);
      setMessages((m) => [...m, { role: "assistant", content: resp.reply }]);
    } catch (e: any) {
      setMessages((m) => [...m, { role: "assistant", content: `Sorry — I hit an error: ${e.message}` }]);
    } finally {
      setSending(false);
    }
  };

  useEffect(() => {
    const t = setTimeout(() => listRef.current?.scrollToEnd({ animated: true }), 60);
    return () => clearTimeout(t);
  }, [messages.length, sending]);

  return (
    <SafeAreaView style={styles.root} edges={["top"]}>
      <View style={styles.header}>
        <View style={styles.avatar}><Ionicons name="sparkles" size={18} color="#000" /></View>
        <View style={{ flex: 1 }}>
          <Text style={styles.headerTitle}>Aida</Text>
          <Text style={styles.headerSub}>AI Tutor · Claude Sonnet 4.5</Text>
        </View>
        <View style={styles.online}>
          <View style={styles.onlineDot} />
          <Text style={styles.onlineText}>Online</Text>
        </View>
      </View>

      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === "ios" ? "padding" : undefined}
        keyboardVerticalOffset={Platform.OS === "ios" ? 8 : 0}
      >
        <FlatList
          ref={listRef}
          data={messages}
          keyExtractor={(_, i) => String(i)}
          contentContainerStyle={{ padding: 16, paddingBottom: 12, gap: 12 }}
          renderItem={({ item }) => (
            <View
              testID={`msg-${item.role}`}
              style={[styles.bubble, item.role === "user" ? styles.bubbleUser : styles.bubbleAi]}
            >
              <Text style={[styles.bubbleText, item.role === "user" && { color: "#000" }]}>
                {item.content}
              </Text>
            </View>
          )}
          ListFooterComponent={
            <>
              {sending && (
                <View style={[styles.bubble, styles.bubbleAi]}>
                  <ActivityIndicator color={C.brand} size="small" />
                </View>
              )}
              {messages.length <= 1 && !sending && (
                <View style={{ marginTop: 12, gap: 8 }}>
                  {SUGGESTIONS.map((s, i) => (
                    <Pressable
                      key={i}
                      testID={`tutor-suggestion-${i}`}
                      onPress={() => send(s)}
                      style={styles.suggestion}
                    >
                      <Ionicons name="bulb-outline" size={14} color={C.brand} />
                      <Text style={styles.suggestionText}>{s}</Text>
                    </Pressable>
                  ))}
                </View>
              )}
            </>
          }
        />

        <View style={[styles.inputBar, { paddingBottom: Math.max(insets.bottom, 12) + 76 }]}>
          <TextInput
            testID="tutor-input"
            value={input}
            onChangeText={setInput}
            placeholder="Ask Aida anything…"
            placeholderTextColor={C.textMuted}
            style={styles.input}
            multiline
            onSubmitEditing={() => send()}
          />
          <Pressable
            testID="tutor-send-btn"
            onPress={() => send()}
            disabled={!input.trim() || sending}
            style={[styles.sendBtn, (!input.trim() || sending) && { opacity: 0.4 }]}
          >
            <Ionicons name="arrow-up" size={20} color="#000" />
          </Pressable>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  header: {
    flexDirection: "row", alignItems: "center", gap: 12,
    paddingHorizontal: 20, paddingVertical: 12, borderBottomWidth: 1, borderColor: C.border,
  },
  avatar: { width: 38, height: 38, borderRadius: 19, backgroundColor: C.brand, alignItems: "center", justifyContent: "center" },
  headerTitle: { color: C.text, fontWeight: "800", fontSize: 17 },
  headerSub: { color: C.textMuted, fontSize: 12 },
  online: { flexDirection: "row", alignItems: "center", gap: 6 },
  onlineDot: { width: 7, height: 7, borderRadius: 4, backgroundColor: C.success },
  onlineText: { color: C.textDim, fontSize: 11, fontWeight: "600" },
  bubble: {
    maxWidth: "85%", padding: 14, borderRadius: 18,
  },
  bubbleAi: { backgroundColor: C.surface, borderTopLeftRadius: 6, alignSelf: "flex-start", borderWidth: 1, borderColor: C.border },
  bubbleUser: { backgroundColor: C.brand, borderTopRightRadius: 6, alignSelf: "flex-end" },
  bubbleText: { color: C.text, fontSize: 15, lineHeight: 22 },
  inputBar: {
    paddingHorizontal: 16, paddingTop: 8, flexDirection: "row", gap: 10, alignItems: "flex-end",
    borderTopWidth: 1, borderColor: C.border, backgroundColor: C.bg,
  },
  input: {
    flex: 1, color: C.text, backgroundColor: C.surface, borderWidth: 1, borderColor: C.border,
    paddingHorizontal: 16, paddingVertical: 12, borderRadius: RADIUS.lg, maxHeight: 120, fontSize: 15,
  },
  sendBtn: { width: 44, height: 44, borderRadius: 22, backgroundColor: C.brand, alignItems: "center", justifyContent: "center" },
  suggestion: {
    flexDirection: "row", alignItems: "center", gap: 10, padding: 14,
    backgroundColor: C.surface, borderWidth: 1, borderColor: C.border, borderRadius: RADIUS.lg,
  },
  suggestionText: { color: C.textDim, fontSize: 14, flex: 1 },
});
