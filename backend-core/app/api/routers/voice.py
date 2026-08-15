"""
Voice — hearing and speaking, 100% local.

  GET  /api/v1/voice/status         which engines are ready
  POST /api/v1/voice/transcribe     audio file -> text (STT)
  POST /api/v1/voice/speak          text -> WAV audio (TTS)
  POST /api/v1/voice/chat           audio -> transcribe -> think -> reply (+ optional audio)
  GET  /api/v1/voice/packs          list available voice packs
  GET  /api/v1/voice/packs/{name}   get a voice pack by key
  GET  /api/v1/voice/personality    random personality phrase

Voice is an optional extra. If an engine isn't installed/configured, the
relevant endpoint returns 503 with a clear message (same pattern as the brain).
"""
import base64

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.jwt import get_current_owner
from app.brain.cognition import Cognition
from app.brain.engine import BrainUnavailable
from app.core.config import settings
from app.core.di import get_cognition, get_voice
from app.db.database import get_db
from app.models.models import Owner
from app.voice.box import VoiceBox
from app.voice.stt import VoiceUnavailable
from app.voice.voice_packs import get_pack, list_packs

router = APIRouter(prefix="/api/v1/voice", tags=["voice"])


class SpeakRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)


class VoiceChatResponse(BaseModel):
    transcript: str
    reply: str
    conversation_id: str
    audio_wav_base64: str | None = None


@router.get("/status")
async def voice_status(
    owner: Owner = Depends(get_current_owner),
    voice: VoiceBox = Depends(get_voice),
):
    return {"enabled": settings.voice_enabled, **voice.status()}


@router.post("/transcribe")
async def transcribe(
    file: UploadFile = File(...),
    language: str | None = None,
    owner: Owner = Depends(get_current_owner),
    voice: VoiceBox = Depends(get_voice),
):
    try:
        text = await voice.transcriber.transcribe(await file.read(), language)
        return {"text": text}
    except VoiceUnavailable as e:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(e)) from e


@router.post("/speak")
async def speak(
    body: SpeakRequest,
    owner: Owner = Depends(get_current_owner),
    voice: VoiceBox = Depends(get_voice),
):
    try:
        audio = await voice.synthesizer.speak(body.text)
        return Response(content=audio, media_type="audio/wav")
    except VoiceUnavailable as e:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(e)) from e


@router.post("/chat", response_model=VoiceChatResponse)
async def voice_chat(
    file: UploadFile = File(...),
    conversation_id: str | None = None,
    device_id: str | None = None,
    speak_reply: bool | None = None,
    owner: Owner = Depends(get_current_owner),
    voice: VoiceBox = Depends(get_voice),
    cognition: Cognition = Depends(get_cognition),
    db: Session = Depends(get_db),
):
    """The full loop: hear → think (with memory) → answer, optionally spoken."""
    try:
        transcript = await voice.transcriber.transcribe(await file.read())
    except VoiceUnavailable as e:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(e)) from e

    try:
        reply, conv_id = await cognition.respond(
            db, owner.id, transcript, conversation_id, device_id,
            persona=voice.pack.persona,
        )
    except BrainUnavailable as e:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(e)) from e

    audio_b64 = None
    want_audio = settings.tts_speak_replies if speak_reply is None else speak_reply
    if want_audio and voice.synthesizer.available():
        try:
            audio_b64 = base64.b64encode(await voice.synthesizer.speak(reply)).decode()
        except VoiceUnavailable:
            audio_b64 = None  # reply text still returned

    return VoiceChatResponse(
        transcript=transcript, reply=reply,
        conversation_id=conv_id, audio_wav_base64=audio_b64,
    )


# ── Voice Packs ───────────────────────────────────────────


@router.get("/packs")
async def get_voice_packs(
    owner: Owner = Depends(get_current_owner),
):
    """List all available voice packs (personality presets)."""
    return list_packs()


@router.get("/packs/{pack_name}")
async def get_voice_pack(
    pack_name: str,
    owner: Owner = Depends(get_current_owner),
    voice: VoiceBox = Depends(get_voice),
):
    """Get a voice pack by name and set it as active."""
    pack = get_pack(pack_name)
    voice.set_pack(pack_name)
    return {
        "name": pack.name,
        "description": pack.description,
        "greeting": pack.greeting,
        "farewell": pack.farewell,
        "personality_phrases": pack.personality_phrases,
        "tts_voice": pack.tts_voice,
        "tts_rate": pack.tts_rate,
        "tts_pitch": pack.tts_pitch,
        "voice_profile": pack.voice_profile,
        "persona": pack.persona,
    }


@router.get("/personality")
async def get_personality_phrase(
    owner: Owner = Depends(get_current_owner),
    voice: VoiceBox = Depends(get_voice),
):
    """Return a random personality phrase from the active voice pack."""
    import random
    phrases = voice.pack.personality_phrases
    return {"phrase": random.choice(phrases), "pack": voice.pack.name}
