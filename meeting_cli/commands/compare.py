"""compare command: diff two transcripts with interactive confirmation."""

import shutil
import subprocess
import sys
from pathlib import Path

import click

from meeting_cli.commands.transcribe import parse_transcript_file
from meeting_cli.diff.engine import align_segments, DiffLevel
from meeting_cli.diff.reporter import build_html_report, build_final_transcript


@click.command()
@click.argument("file_a", type=click.Path(exists=True))
@click.argument("file_b", type=click.Path(exists=True))
@click.option(
    "--output-dir", "-o",
    default="./meeting-output",
    show_default=True,
    help="工作目录",
)
@click.option(
    "--use-llm",
    is_flag=True,
    help="启用LLM辅助精判差异（默认仅用算法）",
)
@click.option(
    "--llm-backend",
    default="openai",
    show_default=True,
    help="LLM精判使用的后端",
)
@click.option(
    "--audio", "-a",
    default=None,
    type=click.Path(exists=True),
    help="原始音频文件路径（用于回听功能）",
)
def compare(
    file_a: str,
    file_b: str,
    output_dir: str,
    use_llm: bool,
    llm_backend: str,
    audio: str | None,
):
    """对比两份转写记录，逐段确认差异。

    FILE_A 和 FILE_B 是两份带时间戳的转写文件。
    差异段落会逐条展示，你选择保留哪个版本。
    最终产出合并后的 final-transcript.txt 和对比报告 diff-report.html。
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. Parse both transcripts
    click.echo(f"读取: {file_a}")
    segs_a = parse_transcript_file(file_a)
    click.echo(f"读取: {file_b}")
    segs_b = parse_transcript_file(file_b)

    source_a = Path(file_a).stem
    source_b = Path(file_b).stem

    # 2. Align and grade
    click.echo(f"对齐比较中... ({len(segs_a)} vs {len(segs_b)} 段)")
    results = align_segments(segs_a, segs_b)

    same_count = sum(1 for r in results if r.level == DiffLevel.SAME)
    small_count = sum(1 for r in results if r.level == DiffLevel.SMALL)
    large_count = sum(1 for r in results if r.level == DiffLevel.LARGE)
    orphan_count = sum(1 for r in results if r.level == DiffLevel.ORPHAN)
    click.echo(
        f"对比完成:  一致{same_count}  小差异{small_count} "
        f" 大差异{large_count}  孤立{orphan_count}"
    )

    needs_review = [r for r in results if r.level != DiffLevel.SAME]
    if not needs_review:
        click.echo("两份转写完全一致，无需人工确认。")
        final = build_final_transcript(results)
        (out_dir / "final-transcript.txt").write_text(final, encoding="utf-8")
        return

    # 3. Interactive review loop
    click.echo(f"\n开始逐段确认 ({len(needs_review)} 段需要审核):")
    click.echo("  [A]保留A  [B]保留B  [E]手动编辑  [P]回听音频  [S]跳过  [Q]退出\n")

    for r in results:
        if r.level == DiffLevel.SAME:
            r.user_choice = "auto"
            continue

        _display_diff(r, source_a, source_b)

        choice = _get_user_choice(audio, r)
        if choice == "q":
            click.echo("已退出。当前进度未保存。")
            sys.exit(0)

        r.user_choice = choice

        if choice == "manual":
            edited = click.prompt("  输入修正文本", type=str)
            r.user_edited_text = edited

    # 4. Generate outputs
    final_path = out_dir / "final-transcript.txt"
    final = build_final_transcript(results)
    final_path.write_text(final, encoding="utf-8")
    click.echo(f"\n最终转写已保存: {final_path}")

    report_path = out_dir / "diff-report.html"
    html = build_html_report(results, source_a, source_b)
    report_path.write_text(html, encoding="utf-8")
    click.echo(f"对比报告已保存: {report_path}")


def _display_diff(r, source_a: str, source_b: str):
    """Display a single diff segment in the terminal."""
    level_emoji = {
        DiffLevel.SMALL: "  小差异",
        DiffLevel.LARGE: "  大差异",
        DiffLevel.ORPHAN: "  孤立",
    }
    emoji = level_emoji.get(r.level, "?")
    ts_a = f"{r.start_a:.1f}s -> {r.end_a:.1f}s" if r.start_a else "--"
    ts_b = f"{r.start_b:.1f}s -> {r.end_b:.1f}s" if r.start_b else "--"

    click.echo(f"\n{'='*60}")
    click.echo(f"【段落 {r.segment_index + 1}】{emoji}")
    click.echo(f"A ({source_a}) [{ts_a}]:  {r.text_a}")
    click.echo(f"B ({source_b}) [{ts_b}]:  {r.text_b}")


def _get_user_choice(audio_path: str | None, r) -> str:
    """Prompt user for choice on a single diff segment.

    Returns one of: 'A', 'B', 'manual', 'skip', 'q'
    """
    while True:
        choice = click.prompt(
            "  选择 [A/B/E/P/S/Q]",
            type=str,
            default="A",
            show_default=False,
        ).strip().lower()

        if choice in ("a", "b", "s"):
            return choice
        elif choice == "e":
            return "manual"
        elif choice == "p":
            if audio_path:
                _play_segment(audio_path, r.start_a or r.start_b, r.end_a or r.end_b)
            else:
                click.echo("  未指定音频文件，无法回听。请用 --audio 指定。")
            continue  # re-prompt after playback
        elif choice == "q":
            return "q"
        else:
            click.echo("  无效选择，请输入 A/B/E/P/S/Q")


def _play_segment(audio_path: str, start: float | None, end: float | None):
    """Play a segment of audio using ffplay."""
    if start is None or end is None:
        click.echo("  无法定位时间戳")
        return

    duration = end - start
    ffplay = shutil.which("ffplay")
    if not ffplay:
        click.echo(f"  未找到 ffplay。请手动跳转到 {start:.1f}s 处播放音频")
        return

    click.echo(f"  播放中... ({start:.1f}s -> {end:.1f}s)")
    subprocess.run(
        [ffplay, "-ss", str(start), "-t", str(duration),
         "-nodisp", "-autoexit", "-loglevel", "quiet", audio_path],
        check=False,
    )
