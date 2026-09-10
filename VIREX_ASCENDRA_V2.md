# Virex's Ascendra Version 2.0

## Product promise

Ascendra should make people comfortable, capable, and eventually excited about using AI. The learner should feel as though a patient expert is sitting beside them—not as though software is reading a course aloud.

The core loop is:

**Learn → Hear → See → Interact → Practice → Explain → Apply → Get coached → Demonstrate mastery**

Version 2.0 is additive. Existing Ascendra paths, curriculum, subscriptions, onboarding, quizzes, XP, streaks, certificates, model library, admin capabilities, and billing remain part of the product.

## Implemented in this branch

### Natural lesson narration
- Server-side ElevenLabs integration; API key is never shipped to the frontend.
- Default narration model: `eleven_v3`.
- Written course text is transformed into conversational instructor copy before synthesis while preserving factual meaning.
- Generated MP3 and spoken script are cached by content/voice/model hash so repeat listens avoid repeated TTS generation charges.
- Native/web player controls: play, pause, rewind 10 seconds, 1x/1.25x/1.5x playback, progress, duration.

### Adaptive in-lesson coaching
Every lesson card can now invoke an Ascendra instructor for:
- **Explain differently** — analogy + concrete example.
- **Let me try it** — one practical exercise without immediately revealing the answer.
- **Evaluate my attempt** — identifies what is correct before coaching the most important improvement.
- **Ask Ascendra** — free-form contextual questions about the concept being studied.

The same coach becomes available after the existing mastery quiz so a wrong answer can become a teaching moment rather than a dead end.

### Backward compatibility
The original lesson card data shape remains valid. Version 2.0 enriches the experience around the existing `cards` and `quiz` objects, so the curriculum does not need to be rewritten before the new learning experience can begin.

## Configuration

Backend environment variables:

```bash
ELEVENLABS_API_KEY=your_server_side_key
ELEVENLABS_VOICE_ID=your_approved_ascendra_voice_id
ELEVENLABS_MODEL_ID=eleven_v3
```

`EMERGENT_LLM_KEY` remains required for the current tutor and is also used by V2 to produce spoken-style narration and adaptive coaching.

For V2 development, start the additive backend entrypoint:

```bash
cd backend
uvicorn server_v2:app --host 0.0.0.0 --port 8001
```

The existing `server.py` has not been replaced.

Frontend dependency added for Expo SDK 54:

```bash
cd frontend
npx expo install expo-audio
```

## Voice standard

Ascendra narration must:
- sound like one excellent teacher speaking to one learner;
- use contractions and varied sentence length naturally;
- pause conceptually between ideas rather than reading punctuation mechanically;
- avoid announcer voice, corporate-training voice, fake enthusiasm, and customer-service cadence;
- explain difficult ideas calmly and without condescension;
- never shame mistakes;
- treat mistakes as information about what to teach next;
- avoid reading formatting, URLs, markdown, or structural labels aloud unless required;
- prioritize understanding over speed.

The eventual branded voice should be original to Ascendra rather than an imitation of a real person's voice.

## Phase 2 — richer lesson objects

Next, extend curriculum content beyond text cards with optional objects such as:

```ts
type LearningBlock =
  | { kind: "explanation"; title: string; body: string }
  | { kind: "visual"; asset: string; caption?: string }
  | { kind: "scenario"; prompt: string; choices?: string[] }
  | { kind: "sandbox"; task: string; evaluator: string }
  | { kind: "reflection"; prompt: string }
  | { kind: "project"; brief: string; rubric: Rubric }
  | { kind: "mastery"; skill: string; threshold: number };
```

The legacy `cards` structure should continue rendering until each path is progressively enriched.

## Phase 3 — Ascendra Live Guide

Add microphone-driven conversation so learners can interrupt a lesson and ask questions naturally. The guide should receive context for:
- current path/module/lesson/card;
- prior completed lessons;
- quiz performance;
- exercises attempted;
- areas of difficulty;
- learner goals and experience level.

Voice conversation should use a low-latency conversational speech model rather than the higher-latency long-form narration pipeline.

## Phase 4 — mastery and adaptation

Add:
- skill-level mastery scores;
- adaptive remediation;
- optional skipping when mastery is demonstrated;
- practical project rubrics;
- portfolio artifacts;
- boss challenges;
- verified competency certificates;
- course and instructor analytics measuring where learners struggle or disengage.

## Guardrails

1. Never remove an existing Ascendra feature merely to simplify V2.
2. New features must improve learning, retention, revenue, or operating leverage.
3. Cache reusable AI outputs when safe so scale does not create unnecessary inference cost.
4. Keep API keys and proprietary prompts server-side.
5. The instructor must support the learner; it should not simply solve every exercise for them.
6. Accessibility remains a first-class requirement: audio is optional, visible text remains available, and learning must work without a microphone.
7. V2 remains isolated from `main` until tested and intentionally merged.
