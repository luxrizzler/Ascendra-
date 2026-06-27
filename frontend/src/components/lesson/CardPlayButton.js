import { Pause, Play, Square } from "lucide-react";
import { tts, useTTS } from "@/lib/tts";

// Small floating play/pause/stop control for a single text card.
// Props: text, title?, onEnd?, size? (sm | md)
export function CardPlayButton({ text, title, lessonTitle, onEnd, size = "md" }) {
  const { speaking, paused } = useTTS();
  if (!tts.isSupported()) return null;
  const idle = !speaking && !paused;
  const w = size === "sm" ? "h-9 w-9" : "h-11 w-11";
  const iconSize = size === "sm" ? 16 : 18;
  const onPlay = () => {
    tts.speak(text, { title: title || lessonTitle, artist: "Ascendra Academy", album: lessonTitle, onEnd });
  };
  const onPause = () => { tts.pause(); };
  const onResume = () => { tts.resume(); };
  const onStop = () => { tts.stop(); };
  return (
    <div className="inline-flex items-center gap-2" role="group" aria-label="Read this card aloud">
      {idle && (
        <button
          type="button"
          onClick={onPlay}
          data-testid="card-play-btn"
          aria-label="Play"
          className={`${w} rounded-full grid place-items-center transition-all hover:scale-105 active:scale-95`}
          style={{ background: "rgba(255,176,0,0.18)", color: "#FFB000", border: "1px solid rgba(255,176,0,0.35)" }}
        >
          <Play size={iconSize} fill="currentColor" />
        </button>
      )}
      {speaking && !paused && (
        <>
          <button
            type="button"
            onClick={onPause}
            data-testid="card-pause-btn"
            aria-label="Pause"
            className={`${w} rounded-full grid place-items-center transition-all hover:scale-105 active:scale-95`}
            style={{ background: "rgba(255,176,0,0.85)", color: "#0A0413" }}
          >
            <Pause size={iconSize} fill="currentColor" />
          </button>
          <button
            type="button"
            onClick={onStop}
            data-testid="card-stop-btn"
            aria-label="Stop"
            className="h-9 w-9 rounded-full grid place-items-center hover:bg-white/5"
          >
            <Square size={14} />
          </button>
        </>
      )}
      {paused && (
        <>
          <button
            type="button"
            onClick={onResume}
            data-testid="card-resume-btn"
            aria-label="Resume"
            className={`${w} rounded-full grid place-items-center transition-all hover:scale-105 active:scale-95`}
            style={{ background: "rgba(255,176,0,0.18)", color: "#FFB000", border: "1px solid rgba(255,176,0,0.35)" }}
          >
            <Play size={iconSize} fill="currentColor" />
          </button>
          <button
            type="button"
            onClick={onStop}
            data-testid="card-stop-btn"
            aria-label="Stop"
            className="h-9 w-9 rounded-full grid place-items-center hover:bg-white/5"
          >
            <Square size={14} />
          </button>
        </>
      )}
    </div>
  );
}
