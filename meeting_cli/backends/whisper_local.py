"""faster-whisper local transcription backend."""

import sys

from meeting_cli.backends.transcriber import BaseTranscriber, Segment
from meeting_cli.utils.config import get_model_dir


class WhisperLocalTranscriber(BaseTranscriber):
    """Local Whisper transcription using faster-whisper.

    Requires: pip install faster-whisper.

    Models are stored under {model_dir}/faster-whisper/.
    Available sizes: tiny, small, medium, large-v3.
    """

    name = "whisper"

    def __init__(self, model_size: str = "medium", device: str = "auto"):
        self.model_size = model_size
        self.device = device

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

        # 模型统一存到项目本地 models 目录
        download_root = str(get_model_dir() / "faster-whisper")
        print(f"模型目录: {download_root}", file=sys.stderr)

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
