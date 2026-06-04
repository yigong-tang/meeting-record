"""transcribe command: audio -> timestamped transcript."""

import re
import sys
from pathlib import Path

import click

from meeting_cli.backends import get_transcriber, list_transcribers
from meeting_cli.backends.transcriber import Segment


def format_timestamp(seconds: float) -> str:
    """Convert float seconds to HH:MM:SS.mmm format."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}"


def format_segment_line(segment: Segment) -> str:
    """Format a Segment as a single timestamped line.

    Example: '[00:00:00.000 -> 00:00:03.500] 大家好'
    """
    start = format_timestamp(segment.start)
    end = format_timestamp(segment.end)
    return f"[{start} -> {end}] {segment.text}"


def parse_transcript_file(path: str) -> list[Segment]:
    """Parse a timestamped transcript file back into Segment objects.

    Expected line format: [HH:MM:SS.mmm -> HH:MM:SS.mmm] text

    Returns:
        List of Segment objects.
    """
    segments = []
    pattern = re.compile(
        r"\[(\d{2}:\d{2}:\d{2}\.\d{3}) -> (\d{2}:\d{2}:\d{2}\.\d{3})\]\s+(.*)"
    )

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            m = pattern.match(line)
            if m:
                segments.append(Segment(
                    start=parse_timestamp(m.group(1)),
                    end=parse_timestamp(m.group(2)),
                    text=m.group(3),
                ))
    return segments


def parse_timestamp(ts: str) -> float:
    """Convert HH:MM:SS.mmm to float seconds."""
    h, m, s = ts.split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


@click.command()
@click.argument("file", type=click.Path(exists=True))
@click.option(
    "--backend", "-b",
    multiple=True,
    required=True,
    help="转写后端（可多次指定，如 -b whisper -b aliyun）",
)
@click.option(
    "--output-dir", "-o",
    default="./meeting-output",
    show_default=True,
    help="工作目录",
)
@click.option(
    "--language", "-l",
    default="zh",
    show_default=True,
    help="音频语言提示",
)
@click.option(
    "--model-size", "-m",
    default=None,
    help="模型大小（whisper 后端可用: tiny, small, medium, large-v3）",
)
def transcribe(
    file: str,
    backend: tuple[str, ...],
    output_dir: str,
    language: str,
    model_size: str | None,
):
    """将音频文件转写为带时间戳的文本记录。

    支持同时使用多个后端，每个后端产出一份独立的转写文件。
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    audio_path = Path(file)
    if not audio_path.exists():
        click.echo(f"错误: 文件不存在: {file}", err=True)
        sys.exit(1)

    for be_name in backend:
        click.echo(f"转写中... 后端: {be_name}")

        transcriber = get_transcriber(be_name)
        if transcriber is None:
            available = list_transcribers()
            click.echo(
                f"错误: 未知后端 '{be_name}'。"
                f"可用: {', '.join(available) if available else '(无)'}",
                err=True,
            )
            sys.exit(1)

        # 如果后端支持 model_size，传入用户选择的值
        if model_size and hasattr(transcriber, "model_size"):
            transcriber.model_size = model_size

        segments = transcriber.transcribe(str(audio_path))

        # 文件名包含后端名和模型大小，避免不同模型互相覆盖
        size = getattr(transcriber, "model_size", "")
        suffix = f"-{size}" if size else ""
        out_path = out_dir / f"trans-{be_name}{suffix}.txt"

        lines = [format_segment_line(seg) for seg in segments]
        out_path.write_text("\n".join(lines), encoding="utf-8")
        click.echo(f"  -> 已保存: {out_path} ({len(segments)} 段)")
