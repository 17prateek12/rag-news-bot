import logging
import mimetypes

from google.genai import types

from app.config import settings
from app.core.exceptions import SpeechToTextError, ValidationError
from app.core.gemini_client import get_gemini_client

logger = logging.getLogger(__name__)

ALLOWED_AUDIO_MIME_TYPES = {
    "audio/webm",
    "audio/wav",
    "audio/x-wav",
    "audio/mpeg",
    "audio/mp3",
    "audio/ogg",
    "audio/mp4",
    "audio/m4a",
    "audio/x-m4a",
}

TRANSCRIBE_PROMPT = (
    "Transcribe the spoken words in this audio accurately. "
    "Return only the transcript text with no labels, timestamps, or commentary. "
    "If the audio is silent or unintelligible, return an empty string."
)


class STTService:
    def _model_name(self) -> str:
        return settings.stt_model or settings.gemini_model

    def _resolve_mime_type(self, mime_type: str | None, filename: str | None) -> str:
        if mime_type:
            normalized = mime_type.split(";", 1)[0].strip().lower()
            if normalized in ALLOWED_AUDIO_MIME_TYPES:
                return normalized

        if filename:
            guessed, _ = mimetypes.guess_type(filename)
            if guessed and guessed.lower() in ALLOWED_AUDIO_MIME_TYPES:
                return guessed.lower()

        raise ValidationError(
            "Unsupported audio format",
            details={
                "mime_type": mime_type,
                "filename": filename,
                "allowed_mime_types": sorted(ALLOWED_AUDIO_MIME_TYPES),
            },
        )

    def transcribe(
        self,
        audio_bytes: bytes,
        *,
        mime_type: str | None = None,
        filename: str | None = None,
    ) -> tuple[str, str | None]:
        if not settings.stt_enabled:
            raise ValidationError("Speech-to-text is disabled")

        if not audio_bytes:
            raise ValidationError("Audio file is empty")

        if len(audio_bytes) > settings.stt_max_audio_bytes:
            raise ValidationError(
                "Audio file is too large",
                details={
                    "size_bytes": len(audio_bytes),
                    "max_bytes": settings.stt_max_audio_bytes,
                },
            )

        resolved_mime = self._resolve_mime_type(mime_type, filename)
        model = self._model_name()
        logger.info(
            "STT transcribe model=%s mime=%s bytes=%s filename=%s",
            model,
            resolved_mime,
            len(audio_bytes),
            filename,
        )

        try:
            client = get_gemini_client()
            response = client.models.generate_content(
                model=model,
                contents=[
                    types.Part.from_bytes(data=audio_bytes, mime_type=resolved_mime),
                    types.Part.from_text(text=TRANSCRIBE_PROMPT),
                ],
                config=types.GenerateContentConfig(
                    temperature=0,
                    max_output_tokens=settings.stt_max_output_tokens,
                ),
            )
            text = (response.text or "").strip()
        except ValidationError:
            raise
        except Exception as exc:
            logger.exception("Speech transcription failed model=%s", model)
            raise SpeechToTextError(
                "Speech transcription failed",
                details={"model": model, "mime_type": resolved_mime},
                cause=exc,
            ) from exc

        if not text:
            raise ValidationError(
                "Could not transcribe audio",
                details={"hint": "Audio may be silent, too short, or unintelligible"},
            )

        logger.info("STT transcribe complete chars=%s", len(text))
        return text, None


stt_service = STTService()
