// Tiny utility for sound effects + confetti, used by lesson completions,
// correct answers, and streak milestones. All sounds generated via Web Audio
// API so there are NO audio assets to ship. Users can disable via localStorage.

import confetti from "canvas-confetti";

const SETTINGS_KEY = "ascendra_celebration_prefs_v1";

function _getPrefs() {
  try {
    const raw = localStorage.getItem(SETTINGS_KEY);
    if (!raw) return { sound: true, confetti: true };
    return { sound: true, confetti: true, ...JSON.parse(raw) };
  } catch (_e) {
    return { sound: true, confetti: true };
  }
}

export function getCelebrationPrefs() { return _getPrefs(); }
export function setCelebrationPrefs(patch) {
  try {
    localStorage.setItem(SETTINGS_KEY, JSON.stringify({ ..._getPrefs(), ...patch }));
  } catch (_e) { /* noop */ }
}

let _ctx = null;
function _audio() {
  if (typeof window === "undefined") return null;
  if (_ctx) return _ctx;
  const Ctx = window.AudioContext || window.webkitAudioContext;
  if (!Ctx) return null;
  try { _ctx = new Ctx(); } catch (_e) { _ctx = null; }
  return _ctx;
}

// Plays a tone (or sequence of tones) using Web Audio API
function _tone({ freq, duration = 0.12, type = "sine", gain = 0.18, startOffset = 0 }) {
  const prefs = _getPrefs();
  if (!prefs.sound) return;
  const ctx = _audio();
  if (!ctx) return;
  try {
    const t0 = ctx.currentTime + startOffset;
    const osc = ctx.createOscillator();
    const g = ctx.createGain();
    osc.type = type;
    osc.frequency.value = freq;
    g.gain.setValueAtTime(0.0001, t0);
    g.gain.exponentialRampToValueAtTime(gain, t0 + 0.01);
    g.gain.exponentialRampToValueAtTime(0.0001, t0 + duration);
    osc.connect(g); g.connect(ctx.destination);
    osc.start(t0); osc.stop(t0 + duration + 0.03);
  } catch (_e) { /* noop */ }
}

// Public sound helpers ---------------------------------------------------
export function playCorrect() {
  _tone({ freq: 660, duration: 0.10, startOffset: 0 });
  _tone({ freq: 880, duration: 0.18, startOffset: 0.10 });
}
export function playWrong() {
  _tone({ freq: 320, duration: 0.10, type: "sawtooth", gain: 0.10 });
  _tone({ freq: 220, duration: 0.18, type: "sawtooth", gain: 0.10, startOffset: 0.10 });
}
export function playComplete() {
  // C major arpeggio
  _tone({ freq: 523, duration: 0.10, startOffset: 0 });
  _tone({ freq: 659, duration: 0.10, startOffset: 0.10 });
  _tone({ freq: 784, duration: 0.10, startOffset: 0.20 });
  _tone({ freq: 1046, duration: 0.26, startOffset: 0.30 });
}
export function playMilestone() {
  // Fanfare-ish
  _tone({ freq: 523, duration: 0.10, startOffset: 0 });
  _tone({ freq: 784, duration: 0.10, startOffset: 0.10 });
  _tone({ freq: 1046, duration: 0.10, startOffset: 0.20 });
  _tone({ freq: 1318, duration: 0.34, startOffset: 0.30 });
}

// Public confetti helpers ------------------------------------------------
export function burstConfetti(opts = {}) {
  const prefs = _getPrefs();
  if (!prefs.confetti) return;
  try {
    confetti({
      particleCount: opts.count || 90,
      spread: 70,
      startVelocity: 45,
      origin: { y: opts.y || 0.6 },
      colors: opts.colors || ["#FFB000", "#FF6B35", "#7C3AED", "#34D399", "#BFB4FF"],
      ...opts,
    });
  } catch (_e) { /* noop */ }
}

// Combined celebrations
export function celebrateCorrect() { playCorrect(); }
export function celebrateWrong() { playWrong(); }
export function celebrateLessonComplete() {
  playComplete();
  burstConfetti({ count: 110 });
}
export function celebrateStreakMilestone() {
  playMilestone();
  // Two staggered bursts for extra oomph
  burstConfetti({ count: 130, colors: ["#FF6B35", "#FFB000", "#FFFFFF"] });
  setTimeout(() => burstConfetti({ count: 80, y: 0.4, spread: 100, colors: ["#FFB000", "#FFFFFF"] }), 240);
}
