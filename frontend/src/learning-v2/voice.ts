import { api, BACKEND_URL } from "@/src/api";

export type PreparedVoice = {
  audio_url: string;
  script: string;
  provider: string;
  model: string;
  cached: boolean;
};

function absoluteAudioUrl(path: string): string {
  if (/^https?:\/\//i.test(path)) return path;
  const base = (BACKEND_URL || "").replace(/\/$/, "");
  return `${base}${path.startsWith("/") ? "" : "/"}${path}`;
}

export async function prepareNaturalVoice(args: {
  sourceText: string;
  lessonId?: string;
  segmentId?: string;
  naturalize?: boolean;
}): Promise<PreparedVoice & { absolute_audio_url: string }> {
  const result = await api.post("/v2/voice/prepare", {
    source_text: args.sourceText,
    lesson_id: args.lessonId,
    segment_id: args.segmentId,
    naturalize: args.naturalize ?? true,
  });

  return {
    ...result,
    absolute_audio_url: absoluteAudioUrl(result.audio_url),
  };
}
