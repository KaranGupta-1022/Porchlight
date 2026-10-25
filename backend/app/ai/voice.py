"""Voice interface used by the upload route."""

from app.ai import provider


def transcribe(audio_bytes: bytes, mime_type: str) -> tuple[str, bool]:
    result = provider.transcribe(audio_bytes, mime_type)
    return str(result.value), result.degraded
