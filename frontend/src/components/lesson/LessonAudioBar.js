import { Headphones, Pause, Play, Square } from "lucide-react";
import { tts, useTTS } from "@/lib/tts";

export function LessonAudioBar({ playAll, onTogglePlayAll, lessonTitle }) {
  const { speaking, paused } = useTTS();
  if (!tts.isSupported()) return null;
  return (
    <div className="flex items-center justify-between gap-3 mb-4 px-1">
      <div className="flex items-center gap-2 text-xs text-[var(--asc-text-muted)]">
        <Headphones size={14} /> <span>Audio</span>
      </div>
      <div className="flex items-center gap-2">
        {speaking && !paused && (
          <button
            type="button"
            onClick={() => tts.pause()}
            data-testid="audio-pause-btn"
            className="h-8 px-3 rounded-full text-xs font-bold flex items-center gap-1.5"
            style={{ background: "rgba(255,176,0,0.85)", color: "#0A0413" }}
          >
            <Pause size={12} fill="currentColor" /> Pause
          </button>
        )}
        {paused && (
          <button
            type="button"
            onClick={() => tts.resume()}
            data-testid="audio-resume-btn"
            className="h-8 px-3 rounded-full text-xs font-bold flex items-center gap-1.5"
            style={{ background: "rgba(255,176,0,0.18)", color: "#FFB000", border: "1px solid rgba(255,176,0,0.35)" }}
          >
            <Play size={12} fill="currentColor" /> Resume
          </button>
        )}
        {(speaking || paused) && (
          <button
            type="button"
            onClick={() => tts.stop()}
            data-testid="audio-stop-btn"
            className="h-8 w-8 rounded-full grid place-items-center hover:bg-white/5"
            aria-label="Stop"
          >
            <Square size={12} />
          </button>
        )}
        <button
          type="button"
          onClick={onTogglePlayAll}
          data-testid="audio-playall-toggle"
          aria-pressed={playAll}
          className="h-8 px-3 rounded-full text-xs font-bold flex items-center gap-1.5 transition-colors"
          style={{
            background: playAll ? "rgba(52,211,153,0.18)" : "rgba(191,180,255,0.08)",
            color: playAll ? "#34D399" : "#BFB4FF",
            border: `1px solid ${playAll ? "#34D399" : "rgba(191,180,255,0.2)"}`,
          }}
        >
          {playAll ? "Play-all: ON" : "Play-all: OFF"}
        </button>
      </div>
    </div>
  );
}
