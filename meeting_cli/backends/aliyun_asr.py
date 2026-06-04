"""Alibaba Cloud (Aliyun) ASR backend (stub)."""

from meeting_cli.backends.transcriber import BaseTranscriber, Segment


class AliyunASRTranscriber(BaseTranscriber):
    """Alibaba Cloud Speech Recognition API backend.

    Placeholder: pending API integration.
    Requires: ALIYUN_ASR_KEY env var.
    """

    name = "aliyun"

    def transcribe(self, audio_path: str) -> list[Segment]:
        raise NotImplementedError("Aliyun ASR backend pending API integration")
