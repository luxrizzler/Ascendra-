// Lightweight Text-to-Speech engine backed by browser speechSynthesis,
// with Media Session API integration so playback shows on iOS/Android lock
// screens and OS media keys (▶ ⏸ ⏭ ⏮) work.
//
// Exposes a small singleton + a React hook `useTTS()`.

let _voices = [];
let _currentUtter = null;
let _wakeLockSentinel = null;
const _listeners = new Set();

function _emit(event) {
  _listeners.forEach((cb) => {
    try { cb(event); } catch (_e) { /* swallow */ }
  });
}

function _loadVoices() {
  if (typeof window === "undefined" || !window.speechSynthesis) return [];
  _voices = window.speechSynthesis.getVoices() || [];
  return _voices;
}

if (typeof window !== "undefined" && window.speechSynthesis) {
  _loadVoices();
  window.speechSynthesis.onvoiceschanged = _loadVoices;
}

function pickDefaultVoice() {
  const voices = _voices.length ? _voices : _loadVoices();
  if (!voices || !voices.length) return null;
  // Prefer high-quality named voices, in priority order:
  const preferred = [
    /Samantha/i, /Karen/i, /Daniel/i, /Allison/i, /Alex/i, /Aria/i,
    /Google US English/i, /Microsoft Aria/i, /Microsoft Jenny/i,
  ];
  for (const rx of preferred) {
    const match = voices.find((v) => rx.test(v.name) && /en[-_]?(US|GB)/i.test(v.lang));
    if (match) return match;
  }
  // Fallback: any English voice
  return voices.find((v) => /^en/i.test(v.lang)) || voices[0];
}

async function _requestWakeLock() {
  if (typeof navigator === "undefined" || !navigator.wakeLock) return;
  try {
    if (_wakeLockSentinel) return;
    _wakeLockSentinel = await navigator.wakeLock.request("screen");
    _wakeLockSentinel.addEventListener("release", () => { _wakeLockSentinel = null; });
  } catch (_e) { /* user may have denied or feature unsupported */ }
}

function _releaseWakeLock() {
  if (_wakeLockSentinel) {
    try { _wakeLockSentinel.release(); } catch (_e) { /* noop */ }
    _wakeLockSentinel = null;
  }
}

function _setMediaSession({ title, artist, album, onPrev, onNext, onPlay, onPause }) {
  if (typeof navigator === "undefined" || !navigator.mediaSession) return;
  try {
    navigator.mediaSession.metadata = new window.MediaMetadata({
      title: title || "Ascendra Lesson",
      artist: artist || "Ascendra Academy",
      album: album || "",
      artwork: [
        { src: "/favicon.svg", sizes: "96x96", type: "image/svg+xml" },
      ],
    });
    if (onPlay) navigator.mediaSession.setActionHandler("play", onPlay);
    if (onPause) navigator.mediaSession.setActionHandler("pause", onPause);
    if (onPrev) navigator.mediaSession.setActionHandler("previoustrack", onPrev);
    if (onNext) navigator.mediaSession.setActionHandler("nexttrack", onNext);
    navigator.mediaSession.playbackState = "playing";
  } catch (_e) { /* noop */ }
}

function _setMediaSessionState(state) {
  if (typeof navigator === "undefined" || !navigator.mediaSession) return;
  try { navigator.mediaSession.playbackState = state; } catch (_e) { /* noop */ }
}

export const tts = {
  isSupported() {
    return typeof window !== "undefined" && !!window.speechSynthesis;
  },
  voices() { return _voices.length ? _voices : _loadVoices(); },
  defaultVoice() { return pickDefaultVoice(); },
  speaking() { return !!(window.speechSynthesis && window.speechSynthesis.speaking); },
  paused() { return !!(window.speechSynthesis && window.speechSynthesis.paused); },
  speak(text, opts = {}) {
    if (!this.isSupported() || !text) return;
    const synth = window.speechSynthesis;
    // Cancel any in-progress speech first
    synth.cancel();
    const utter = new window.SpeechSynthesisUtterance(text);
    const v = opts.voice || pickDefaultVoice();
    if (v) utter.voice = v;
    utter.rate = Math.max(0.5, Math.min(2.0, opts.rate || 1.0));
    utter.pitch = 1.0;
    utter.volume = 1.0;
    utter.lang = (v && v.lang) || "en-US";
    utter.onend = () => {
      _currentUtter = null;
      _setMediaSessionState("none");
      _releaseWakeLock();
      _emit({ type: "end" });
      if (opts.onEnd) try { opts.onEnd(); } catch (_e) { /* noop */ }
    };
    utter.onerror = (e) => {
      _currentUtter = null;
      _setMediaSessionState("none");
      _releaseWakeLock();
      _emit({ type: "error", error: e });
      if (opts.onError) try { opts.onError(e); } catch (_e) { /* noop */ }
    };
    utter.onstart = () => {
      _setMediaSessionState("playing");
      _emit({ type: "start" });
    };
    _currentUtter = utter;
    _setMediaSession({
      title: opts.title,
      artist: opts.artist,
      album: opts.album,
      onPlay: () => this.resume(),
      onPause: () => this.pause(),
      onPrev: opts.onPrev,
      onNext: opts.onNext,
    });
    _requestWakeLock();
    synth.speak(utter);
  },
  pause() {
    if (!this.isSupported()) return;
    try { window.speechSynthesis.pause(); _setMediaSessionState("paused"); _emit({ type: "pause" }); } catch (_e) { /* noop */ }
  },
  resume() {
    if (!this.isSupported()) return;
    try { window.speechSynthesis.resume(); _setMediaSessionState("playing"); _emit({ type: "resume" }); } catch (_e) { /* noop */ }
  },
  stop() {
    if (!this.isSupported()) return;
    try { window.speechSynthesis.cancel(); _setMediaSessionState("none"); _releaseWakeLock(); _emit({ type: "stop" }); } catch (_e) { /* noop */ }
    _currentUtter = null;
  },
  on(cb) { _listeners.add(cb); return () => _listeners.delete(cb); },
};

// Tiny React hook so components can react to TTS state changes.
import { useEffect, useState } from "react";
export function useTTS() {
  const [state, setState] = useState({ speaking: false, paused: false });
  useEffect(() => {
    const handler = () => {
      setState({
        speaking: !!(window.speechSynthesis && window.speechSynthesis.speaking),
        paused: !!(window.speechSynthesis && window.speechSynthesis.paused),
      });
    };
    handler();
    const off = tts.on(handler);
    const i = setInterval(handler, 500); // poll because speechSynthesis events are flaky on iOS
    return () => { off(); clearInterval(i); };
  }, []);
  return { ...state, tts };
}
