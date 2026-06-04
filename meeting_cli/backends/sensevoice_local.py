"""SenseVoice local transcription backend (stub)."""

from meeting_cli.backends.transcriber import BaseTranscriber, Segment


class SenseVoiceLocalTranscriber(BaseTranscriber):
    """Local SenseVoice ASR — lightweight Chinese-focused model.

    Placeholder: implementation pending hardware verification on ThinkPad.
    """

    name = "sensevoice"

    def transcribe(self, audio_path: str) -> list[Segment]:
        raise NotImplementedError("SenseVoice backend pending hardware verification")
