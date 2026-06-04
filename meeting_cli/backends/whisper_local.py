"""faster-whisper local transcription backend."""

from meeting_cli.backends.transcriber import BaseTranscriber, Segment


class WhisperLocalTranscriber(BaseTranscriber):
    """Local Whisper transcription using faster-whisper."""

    name = "whisper"

    def transcribe(self, audio_path: str) -> list[Segment]:
        """Placeholder: real implementation in later task."""
        raise NotImplementedError("Whisper local backend not yet implemented")
