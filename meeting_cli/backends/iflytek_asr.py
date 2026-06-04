"""iFlytek (科大讯飞) ASR backend (stub)."""

from meeting_cli.backends.transcriber import BaseTranscriber, Segment


class IflytekASRTranscriber(BaseTranscriber):
    """iFlytek Speech Recognition API backend.

    Placeholder: pending API integration.
    Requires: IFLYTEK_ASR_KEY env var.
    """

    name = "iflytek"

    def transcribe(self, audio_path: str) -> list[Segment]:
        raise NotImplementedError("iFlytek ASR backend pending API integration")
