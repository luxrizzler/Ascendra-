"""Virex's Ascendra Version 2.0 learning services.

This module is intentionally additive. The existing Ascendra API remains untouched;
server_v2.py mounts these routes on top of the current application.

Goals:
- Generate human-sounding lesson narration without exposing provider API keys.
- Cache generated narration so repeat listens do not trigger repeat TTS charges.
- Convert display copy into spoken instructor copy while preserving meaning.
- Provide an adaptive lesson coach for explanations, practice, and feedback.
"""
from __future__ import annotations

import hashlib
import os
import uuid
from pathlib import Path
from typing import Callable, Literal, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from emergentintegrations.llm.chat import LlmChat, UserMessage

ROOT_DIR = Path(__file__).parent
AUDIO_DIR = ROOT_DIR / "static" / "v2-audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID", "")
ELEVENLABS_MODEL_ID = os.environ.get("ELEVENLABS_MODEL_ID", "eleven_v3")
EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")

NARRATION_SYSTEM = """You are the voice-writing engine for Ascendra, an AI learning platform whose purpose is to help people become confident using AI. Rewrite the supplied lesson text as spoken instruction from an exceptional human teacher talking to one learner. Preserve every factual claim and technical meaning. Do not add unsupported facts. Use natural contractions, varied sentence lengths, occasional rhetorical questions, and conversational transitions. Never sound like an announcer, textbook, corporate training video, or customer-service bot. Avoid fake enthusiasm. Explain difficult ideas calmly. Do not read markdown, labels, bullets, URLs, or formatting aloud unless essential. Return only the words that should be spoken."""

COACH_SYSTEM = """You are Ascendra Live Guide, a patient and highly capable AI instructor. Your goal is not to give students answers as quickly as possible; your goal is to help them understand, practice, and become confident. Be warm, natural, concise, and specific. Never shame a learner for a mistake. When correcting work, identify what is already right before explaining the next improvement. Adapt the explanation to the learner's response and use concrete examples. When asked for practice, give one practical exercise at a time. When evaluating a learner response, explain the reasoning and give a next step. Avoid robotic phrases and generic encouragement."""


class VoicePrepareIn(BaseModel):
    source_text: str = Field(min_length=1, max_length=5000)
    lesson_id: Optional[str] = None
    segment_id: Optional[str] = None
    voice_id: Optional[str] = None
    naturalize: bool = True


class VoicePrepareOut(BaseModel):
    audio_url: str
    script: str
    provider: str = "elevenlabs"
    model: str
    cached: bool


class CoachIn(BaseModel):
    lesson_id: Optional[str] = None
    lesson_title: str = Field(default="Current lesson", max_length=300)
    concept_text: str = Field(min_length=1, max_length=8000)
    action: Literal["explain", "practice", "evaluate", "question"] = "question"
    learner_message: Optional[str] = Field(default=None, max_length=6000)


class CoachOut(BaseModel):
    reply: str


def _audio_key(text: str, voice_id: str, model_id: str, naturalize: bool) -> str:
    material = f"{voice_id}|{model_id}|{int(naturalize)}|{text}".encode("utf-8")
    return hashlib.sha256(material).hexdigest()


async def _naturalize_for_speech(source_text: str) -> str:
    if not EMERGENT_LLM_KEY:
        return source_text
    try:
        session_id = f"v2-narration-{uuid.uuid4()}"
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=session_id,
            system_message=NARRATION_SYSTEM,
        ).with_model("anthropic", "claude-sonnet-4-5-20250929")
        spoken = await chat.send_message(UserMessage(text=source_text))
        spoken = (spoken or "").strip()
        return spoken if spoken else source_text
    except Exception:
        # Narration must remain available even if the rewriting model is temporarily down.
        return source_text


async def _coach_reply(body: CoachIn) -> str:
    if not EMERGENT_LLM_KEY:
        raise HTTPException(503, "Adaptive coach is not configured")

    if body.action == "explain":
        instruction = "Explain this concept a different way. Use a concrete analogy, then one short example."
    elif body.action == "practice":
        instruction = "Create one practical, hands-on challenge that tests this concept. Do not provide the answer yet."
    elif body.action == "evaluate":
        instruction = "Evaluate the learner's attempt. Say what is correct, identify the most important improvement, and give one next action."
    else:
        instruction = "Answer the learner's question in the context of this lesson, then check whether the distinction makes sense."

    prompt = (
        f"Lesson: {body.lesson_title}\n\n"
        f"Concept being studied:\n{body.concept_text}\n\n"
        f"Teaching action: {instruction}\n\n"
        f"Learner message/attempt: {body.learner_message or '(none)'}"
    )
    try:
        session_id = f"v2-coach-{uuid.uuid4()}"
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=session_id,
            system_message=COACH_SYSTEM,
        ).with_model("anthropic", "claude-sonnet-4-5-20250929")
        reply = await chat.send_message(UserMessage(text=prompt))
        return (reply or "").strip()
    except Exception as exc:
        raise HTTPException(503, f"Ascendra Live Guide unavailable: {str(exc)[:120]}")


def build_router(current_user_dependency: Callable) -> APIRouter:
    router = APIRouter(prefix="/api/v2", tags=["Ascendra Learning Engine 2.0"])

    @router.get("/status")
    async def v2_status():
        return {
            "name": "Virex's Ascendra Version 2.0",
            "natural_voice_configured": bool(ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID),
            "adaptive_coach_configured": bool(EMERGENT_LLM_KEY),
            "tts_model": ELEVENLABS_MODEL_ID,
        }

    @router.post("/voice/prepare", response_model=VoicePrepareOut)
    async def prepare_voice(body: VoicePrepareIn, user=Depends(current_user_dependency)):
        del user  # authentication gate; no user-specific audio is cached in this phase
        if not ELEVENLABS_API_KEY or not (body.voice_id or ELEVENLABS_VOICE_ID):
            raise HTTPException(
                503,
                "Natural voice is not configured. Set ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID.",
            )

        voice_id = body.voice_id or ELEVENLABS_VOICE_ID
        cache_key = _audio_key(body.source_text, voice_id, ELEVENLABS_MODEL_ID, body.naturalize)
        audio_path = AUDIO_DIR / f"{cache_key}.mp3"
        script_path = AUDIO_DIR / f"{cache_key}.txt"

        if audio_path.exists() and script_path.exists():
            return VoicePrepareOut(
                audio_url=f"/api/v2/voice/audio/{cache_key}",
                script=script_path.read_text(encoding="utf-8"),
                model=ELEVENLABS_MODEL_ID,
                cached=True,
            )

        script = await _naturalize_for_speech(body.source_text) if body.naturalize else body.source_text
        # Eleven v3 has a 5,000-character request limit. The naturalizer normally shortens
        # prose, but this guard keeps the request deterministic.
        script = script[:5000].strip()
        if not script:
            raise HTTPException(422, "Narration script is empty")

        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        headers = {"xi-api-key": ELEVENLABS_API_KEY, "Content-Type": "application/json"}
        payload = {
            "text": script,
            "model_id": ELEVENLABS_MODEL_ID,
        }
        params = {"output_format": "mp3_44100_128"}
        try:
            async with httpx.AsyncClient(timeout=75.0) as client:
                response = await client.post(url, headers=headers, params=params, json=payload)
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text[:240] if exc.response is not None else str(exc)
            raise HTTPException(502, f"Voice provider rejected the request: {detail}")
        except Exception as exc:
            raise HTTPException(502, f"Voice generation failed: {str(exc)[:160]}")

        audio_path.write_bytes(response.content)
        script_path.write_text(script, encoding="utf-8")
        return VoicePrepareOut(
            audio_url=f"/api/v2/voice/audio/{cache_key}",
            script=script,
            model=ELEVENLABS_MODEL_ID,
            cached=False,
        )

    @router.get("/voice/audio/{asset_id}")
    async def voice_audio(asset_id: str):
        # SHA-256 IDs are deliberately opaque; the GET can be consumed directly by the
        # native audio player without putting a bearer token into the media URL.
        if len(asset_id) != 64 or any(ch not in "0123456789abcdef" for ch in asset_id.lower()):
            raise HTTPException(404, "Audio not found")
        audio_path = AUDIO_DIR / f"{asset_id}.mp3"
        if not audio_path.exists():
            raise HTTPException(404, "Audio not found")
        return FileResponse(audio_path, media_type="audio/mpeg", filename=f"ascendra-{asset_id[:10]}.mp3")

    @router.post("/coach", response_model=CoachOut)
    async def coach(body: CoachIn, user=Depends(current_user_dependency)):
        del user
        reply = await _coach_reply(body)
        return CoachOut(reply=reply)

    return router
