"""faster-whisper local transcription backend."""

import sys
from pathlib import Path

from meeting_cli.backends.transcriber import BaseTranscriber, Segment
from meeting_cli.utils.config import get_model_dir


class WhisperLocalTranscriber(BaseTranscriber):
    """Local Whisper transcription using faster-whisper.

    Requires: pip install faster-whisper

    Model search order:
      1. {model_dir}/faster-whisper/{model_size}/  (local models dir)
      2. HuggingFace hub cache / download            (fallback)

    Model: 'medium' for a good balance of accuracy and speed on ThinkPad.
           Falls back to 'small' if memory is constrained.
    """

    name = "whisper"

    def __init__(self, model_size: str = "medium", device: str = "auto"):
        self.model_size = model_size
        self.device = device

    def _resolve_model_path(self) -> str | None:
        """Check if model exists in local models directory.

        Returns:
            Path to local model dir if found, None to use HF cache fallback.
        """
        local = get_model_dir() / "faster-whisper" / self.model_size
        # faster-whisper models contain model.bin and config.json
        if local.is_dir() and (local / "model.bin").exists():
            return str(local)
        return None

    def transcribe(self, audio_path: str) -> list[Segment]:
        """Transcribe audio using local faster-whisper model.

        Args:
            audio_path: Path to the audio file.

        Returns:
            List of timestamped Segment objects.
        """
        try:
            from faster_whisper import WhisperModel
        except ImportError:
            print(
                "错误: 需要安装 faster-whisper。运行: pip install faster-whisper",
                file=sys.stderr,
            )
            sys.exit(1)

        device = self.device
        if device == "auto":
            device = "cuda" if self._cuda_available() else "cpu"

        compute_type = (
            "float16" if device == "cuda" else "int8"
        )

        # 本地 models 目录优先，没有则回退到 HF 缓存/下载
        download_root = self._resolve_model_path()
        if download_root:
            print(f"使用本地模型: {download_root}", file=sys.stderr)
        else:
            print(
                f"本地未找到 {self.model_size} 模型，"
                f"将从 HuggingFace 缓存加载或下载",
                file=sys.stderr,
            )

        model = WhisperModel(
            self.model_size,
            device=device,
            compute_type=compute_type,
            download_root=download_root,
        )
        segments_iter, _ = model.transcribe(audio_path, language="zh")

        segments = []
        for seg in segments_iter:
            segments.append(Segment(
                start=seg.start,
                end=seg.end,
                text=seg.text.strip(),
            ))
        return segments

    @staticmethod
    def _cuda_available() -> bool:
        """Check if CUDA GPU is available."""
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            return False
