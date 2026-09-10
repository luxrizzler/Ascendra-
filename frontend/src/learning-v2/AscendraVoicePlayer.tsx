import { useEffect, useMemo, useState } from "react";
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useAudioPlayer, useAudioPlayerStatus } from "expo-audio";

import { C, RADIUS } from "@/src/theme";
import { prepareNaturalVoice } from "@/src/learning-v2/voice";

type Props = {
  sourceText: string;
  lessonId?: string;
  segmentId?: string;
  accentColor?: string;
};

const RATES = [1, 1.25, 1.5];

function clock(seconds = 0) {
  const total = Math.max(0, Math.floor(seconds || 0));
  const mins = Math.floor(total / 60);
  const secs = String(total % 60).padStart(2, "0");
  return `${mins}:${secs}`;
}

export function AscendraVoicePlayer({ sourceText, lessonId, segmentId, accentColor }: Props) {
  const color = accentColor || C.brand;
  const player = useAudioPlayer(null, { updateInterval: 250, downloadFirst: true });
  const status = useAudioPlayerStatus(player);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [spokenScript, setSpokenScript] = useState<string | null>(null);
  const [preparing, setPreparing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [rateIndex, setRateIndex] = useState(0);
  const [autoplayWhenReady, setAutoplayWhenReady] = useState(false);

  const progress = useMemo(() => {
    if (!status.duration) return 0;
    return Math.min(100, Math.max(0, (status.currentTime / status.duration) * 100));
  }, [status.currentTime, status.duration]);

  useEffect(() => {
    player.pause();
    setAudioUrl(null);
    setSpokenScript(null);
    setError(null);
    setAutoplayWhenReady(false);
  }, [sourceText, segmentId]);

  useEffect(() => {
    player.playbackRate = RATES[rateIndex];
  }, [player, rateIndex]);

  useEffect(() => {
    if (!audioUrl) return;
    player.replace({ uri: audioUrl });
    if (autoplayWhenReady) {
      // replace() begins loading immediately; a brief turn of the event loop avoids
      // a play-before-source race on slower native devices.
      setTimeout(() => player.play(), 40);
      setAutoplayWhenReady(false);
    }
  }, [audioUrl]);

  const ensureAudio = async (autoplay = true) => {
    if (audioUrl) {
      if (status.playing) player.pause();
      else player.play();
      return;
    }
    setPreparing(true);
    setError(null);
    setAutoplayWhenReady(autoplay);
    try {
      const prepared = await prepareNaturalVoice({
        sourceText,
        lessonId,
        segmentId,
        naturalize: true,
      });
      setSpokenScript(prepared.script);
      setAudioUrl(prepared.absolute_audio_url);
    } catch (e: any) {
      setAutoplayWhenReady(false);
      setError(e?.message || "Natural narration is temporarily unavailable.");
    } finally {
      setPreparing(false);
    }
  };

  const rewind = async () => {
    if (!audioUrl) return;
    await player.seekTo(Math.max(0, (status.currentTime || 0) - 10));
  };

  const cycleRate = () => setRateIndex((i) => (i + 1) % RATES.length);

  return (
    <View style={styles.wrap}>
      <View style={styles.topRow}>
        <View style={styles.labelRow}>
          <Ionicons name="sparkles" size={15} color={color} />
          <Text style={[styles.label, { color }]}>ASCENDRA NATURAL VOICE</Text>
        </View>
        <Text style={styles.time}>{clock(status.currentTime)} / {clock(status.duration)}</Text>
      </View>

      <View style={styles.track}>
        <View style={[styles.fill, { width: `${progress}%`, backgroundColor: color }]} />
      </View>

      <View style={styles.controls}>
        <Pressable onPress={rewind} disabled={!audioUrl} style={[styles.smallBtn, !audioUrl && styles.disabled]}>
          <Ionicons name="play-back" size={17} color={C.text} />
          <Text style={styles.smallText}>10s</Text>
        </Pressable>

        <Pressable onPress={() => ensureAudio(true)} style={[styles.playBtn, { backgroundColor: color }]}>
          {preparing ? (
            <ActivityIndicator color="#000" />
          ) : (
            <Ionicons name={status.playing ? "pause" : "play"} size={22} color="#000" />
          )}
          <Text style={styles.playText}>
            {preparing ? "Preparing voice…" : status.playing ? "Pause" : audioUrl ? "Continue" : "Listen"}
          </Text>
        </Pressable>

        <Pressable onPress={cycleRate} style={styles.smallBtn}>
          <Text style={styles.rate}>{RATES[rateIndex]}×</Text>
        </Pressable>
      </View>

      {spokenScript && (
        <Text style={styles.note}>Narration is rewritten for natural speech while preserving the lesson meaning.</Text>
      )}
      {error && <Text style={styles.error}>{error}</Text>}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    marginTop: 16,
    padding: 14,
    borderRadius: RADIUS.lg,
    backgroundColor: C.surface2,
    borderWidth: 1,
    borderColor: C.border,
  },
  topRow: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 12 },
  labelRow: { flexDirection: "row", alignItems: "center", gap: 6, flex: 1 },
  label: { fontSize: 10, fontWeight: "900", letterSpacing: 1.5 },
  time: { color: C.textMuted, fontSize: 11 },
  track: { height: 4, borderRadius: 3, backgroundColor: C.borderStrong, overflow: "hidden", marginTop: 12 },
  fill: { height: 4, borderRadius: 3 },
  controls: { flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 10, marginTop: 12 },
  playBtn: { minWidth: 150, paddingVertical: 11, paddingHorizontal: 18, borderRadius: RADIUS.md, flexDirection: "row", justifyContent: "center", alignItems: "center", gap: 8 },
  playText: { color: "#000", fontSize: 14, fontWeight: "900" },
  smallBtn: { minWidth: 55, minHeight: 42, borderRadius: RADIUS.md, backgroundColor: C.surface, borderWidth: 1, borderColor: C.border, alignItems: "center", justifyContent: "center", flexDirection: "row", gap: 4 },
  smallText: { color: C.text, fontSize: 11, fontWeight: "700" },
  rate: { color: C.text, fontSize: 13, fontWeight: "900" },
  disabled: { opacity: 0.35 },
  note: { color: C.textMuted, fontSize: 11, lineHeight: 16, marginTop: 10, textAlign: "center" },
  error: { color: C.danger, fontSize: 12, lineHeight: 17, marginTop: 10, textAlign: "center" },
});
