import asyncio
import logging

from fastapi import APIRouter, Depends, File, UploadFile

from app.core.exceptions import ValidationError
from app.config import settings
from app.core.user_auth import get_current_user
from app.models.user import User
from app.schemas.speech import TranscribeResponse
from app.services.stt_service import stt_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/speech", tags=["speech"])

# H-5: Allowlist of accepted audio MIME types
_ALLOWED_AUDIO_TYPES = {
    "audio/webm",
    "audio/ogg",
    "audio/mpeg",
    "audio/mp4",
    "audio/wav",
    "audio/wave",
    "audio/x-wav",
    "audio/mp3",
    "audio/aac",
    "audio/flac",
    "video/webm",  # Chrome records voice as video/webm
}


@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe_audio(
    audio: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    audio_bytes = await audio.read()
    if not audio_bytes:
        raise ValidationError("Audio file is empty")

    # H-5: Validate MIME type against allowlist
    content_type = (audio.content_type or "").lower().split(";")[0].strip()
    if content_type not in _ALLOWED_AUDIO_TYPES:
        raise ValidationError(
            f"Unsupported audio format '{content_type}'. "
            f"Accepted: {', '.join(sorted(_ALLOWED_AUDIO_TYPES))}"
        )

    # H-5: Enforce maximum audio file size from config
    max_bytes = settings.stt_max_audio_bytes
    if len(audio_bytes) > max_bytes:
        raise ValidationError(
            f"Audio file too large ({len(audio_bytes):,} bytes). "
            f"Maximum allowed: {max_bytes:,} bytes."
        )

    logger.info(
        "Speech transcribe request user_id=%s filename=%s content_type=%s bytes=%s",
        current_user.id,
        audio.filename,
        content_type,
        len(audio_bytes),
    )

    text, language = await asyncio.to_thread(
        stt_service.transcribe,
        audio_bytes,
        mime_type=audio.content_type,
        filename=audio.filename,
    )
    return TranscribeResponse(
        text=text,
        language=language,
        model=settings.stt_model or settings.gemini_model,
    )

