"""subtitle command: transcript -> SRT subtitle file (exploratory)."""

import shutil
import subprocess
import sys
from pathlib import Path

import click

from meeting_cli.commands.transcribe import parse_transcript_file
from meeting_cli.backends.transcriber import Segment


def srt_timestamp(seconds: float) -> str:
    """Convert seconds to SRT timestamp format: HH:MM:SS,mmm."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def segments_to_srt(segments: list[Segment]) -> str:
    """Convert timestamped segments to SRT subtitle text.

    Args:
        segments: List of Segment objects with start, end, and text.

    Returns:
        SRT-formatted string.
    """
    blocks = []
    for i, seg in enumerate(segments, 1):
        start = srt_timestamp(seg.start)
        end = srt_timestamp(seg.end)
        blocks.append(f"{i}\n{start} --> {end}\n{seg.text}\n")
    return "\n".join(blocks)


@click.command()
@click.argument("transcript", type=click.Path(exists=True))
@click.argument("video", type=click.Path(exists=True))
@click.option(
    "--output-dir", "-o",
    default="./meeting-output",
    show_default=True,
    help="工作目录",
)
@click.option(
    "--translate",
    is_flag=True,
    help="同时生成翻译字幕",
)
@click.option(
    "--target-lang",
    default="en",
    show_default=True,
    help="翻译目标语言",
)
@click.option(
    "--soft",
    is_flag=True,
    help="软字幕（秒出，播放器可开关；默认硬字幕烧录到画面）",
)
def subtitle(
    transcript: str,
    video: str,
    output_dir: str,
    translate: bool,
    target_lang: str,
    soft: bool,
):
    """将带时间戳的转写记录生成SRT字幕，并嵌入视频（探索性功能）。

    需要安装 ffmpeg。依赖转写记录中包含时间戳信息。
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. Parse transcript -> segments
    click.echo(f"读取转写: {transcript}")
    segments = parse_transcript_file(transcript)
    if not segments:
        click.echo("错误: 转写文件为空或格式不正确", err=True)
        sys.exit(1)

    # 2. Generate SRT
    srt_content = segments_to_srt(segments)
    srt_path = out_dir / "subtitle.srt"
    srt_path.write_text(srt_content, encoding="utf-8")
    click.echo(f"字幕已生成: {srt_path} ({len(segments)} 条)")

    # 3. Optional translation
    if translate:
        click.echo(f"翻译字幕（目标语言: {target_lang}）...")
        click.echo("  翻译功能将在后续版本中完善。")

    # 4. Embed with ffmpeg
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        click.echo(
            "警告: 未找到 ffmpeg，跳过视频嵌入。"
            "请安装 ffmpeg 后手动将 subtitle.srt 嵌入视频。",
            err=True,
        )
        return

    output_video = out_dir / f"{Path(video).stem}_subtitled.mp4"

    if soft:
        # 软字幕：添加独立字幕轨，不重编码，秒级完成
        click.echo(f"正在添加软字幕: {output_video}")
        result = subprocess.run(
            [
                ffmpeg,
                "-i", video,
                "-i", str(srt_path),
                "-c", "copy",
                "-c:s", "mov_text",
                "-map", "0:v:0",
                "-map", "0:a:0",
                "-map", "1:s:0",
                str(output_video),
            ],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    else:
        # 硬字幕：烧录到画面，需重编码，慢但兼容所有播放器
        click.echo(f"正在烧录硬字幕: {output_video} (需重编码，请耐心等待)")
        result = subprocess.run(
            [
                ffmpeg,
                "-i", video,
                "-vf", f"subtitles={srt_path}",
                "-c:a", "copy",
                str(output_video),
            ],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    if result.returncode == 0:
        click.echo(f"带字幕视频已保存: {output_video}")
    else:
        click.echo(
            "ffmpeg 嵌入字幕失败。请检查视频文件和 ffmpeg 安装。\n"
            f"  SRT 字幕已保存: {srt_path}",
            err=True,
        )
