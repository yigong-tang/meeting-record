"""SenseVoice local transcription backend.

Uses Alibaba FunASR SenseVoiceSmall — a lightweight Chinese-focused model.
Good accuracy, small footprint, suitable for ThinkPad.
"""

import sys
from pathlib import Path

from meeting_cli.backends.transcriber import BaseTranscriber, Segment
from meeting_cli.utils.config import get_model_dir


class SenseVoiceLocalTranscriber(BaseTranscriber):
    """Local SenseVoice ASR using FunASR.

    Requires: pip install funasr modelscope

    Models stored under {model_dir}/SenseVoiceSmall/.
    """

    name = "sensevoice"

    def __init__(self, device: str = "cpu"):
        self.device = device

    def transcribe(self, audio_path: str) -> list[Segment]:
        """Transcribe audio using SenseVoiceSmall.

        Args:
            audio_path: Path to the audio file (mp3/wav).

        Returns:
            List of timestamped Segment objects.
        """
        try:
            from funasr import AutoModel
        except ImportError:
            print(
                "错误: 需要安装 funasr。运行: pip install funasr modelscope",
                file=sys.stderr,
            )
            sys.exit(1)

        # 1. Determine model path (local first, download if needed)
        model_path = _get_or_download_model()

        # 2. Load model
        print(f"加载 SenseVoiceSmall 模型...", file=sys.stderr)
        # FunASR needs model.py in Python path (can't handle absolute paths on Windows)
        sys.path.insert(0, model_path)
        model = AutoModel(
            model=model_path,
            trust_remote_code=True,
            remote_code="model",
            device=self.device,
            disable_update=True,
        )

        # 3. Transcribe
        res = model.generate(
            input=audio_path,
            cache={},
            language="zh",
            use_itn=True,
        )

        # 4. Parse segments
        segments: list[Segment] = []
        if res and len(res) > 0:
            for item in res[0].get("text_with_timestamps", []):
                segments.append(Segment(
                    start=item.get("start", 0.0),
                    end=item.get("end", 0.0),
                    text=item.get("text", "").strip(),
                ))

        # Fallback: if no timestamps, use plain text as one segment
        if not segments and res and len(res) > 0:
            text = res[0].get("text", "")
            if text:
                segments.append(Segment(start=0.0, end=0.0, text=text.strip()))

        return segments


def _get_or_download_model() -> str:
    """Get local model path, downloading if necessary.

    Returns:
        Path string to the model directory.
    """
    local_dir = get_model_dir() / "SenseVoiceSmall"
    model_file = local_dir / "model.pt"

    if model_file.exists():
        print(f"使用本地模型: {local_dir}", file=sys.stderr)
        return str(local_dir)

    # Download to local models dir
    print(f"下载 SenseVoiceSmall 模型到 {local_dir} ...", file=sys.stderr)

    try:
        from modelscope import snapshot_download
    except ImportError:
        print(
            "错误: 需要安装 modelscope。运行: pip install modelscope",
            file=sys.stderr,
        )
        sys.exit(1)

    snapshot_download(
        "iic/SenseVoiceSmall",
        local_dir=str(local_dir),
    )
    return str(local_dir)
