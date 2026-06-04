"""compare command: diff two transcripts with optional interactive review."""

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
    "--interactive", "-i",
    is_flag=True,
    help="手动逐段审核差异（默认：算法自动决策）",
)
@click.option(
    "--use-llm",
    is_flag=True,
    help="启用LLM辅助精判差异语义等价（默认仅用算法）",
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
    help="原始音频文件路径（用于回听，需 --interactive）",
)
def compare(
    file_a: str,
    file_b: str,
    output_dir: str,
    interactive: bool,
    use_llm: bool,
    llm_backend: str,
    audio: str | None,
):
    """对比两份转写记录，产出合并结果和对比报告。

    \b
    默认：纯算法自动决策，直接产出 final-transcript.txt + diff-report.html
    --interactive：手动逐段审核差异
    --use-llm：LLM辅助判断差异是否为同义改写

    FILE_A 和 FILE_B 是两份带时间戳的转写文件。
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

    # 3. LLM-assisted judging (if enabled)
    if use_llm:
        _llm_judge(results, llm_backend)

    # 4. Decide: interactive or auto
    if interactive:
        _interactive_review(results, source_a, source_b, audio, segs_a, segs_b)
    else:
        _auto_decide(results)

    # 5. Generate outputs
    final_path = out_dir / "final-transcript.txt"
    final = build_final_transcript(results)
    final_path.write_text(final, encoding="utf-8")
    click.echo(f"\n最终转写已保存: {final_path}")

    report_path = out_dir / "diff-report.html"
    html = build_html_report(results, source_a, source_b)
    report_path.write_text(html, encoding="utf-8")
    click.echo(f"对比报告已保存: {report_path}")


def _auto_decide(results):
    """Automatically decide: prefer A when both sides exist, take the
    non-empty side for orphans, keep SAME as-is."""
    for r in results:
        if r.level == DiffLevel.SAME:
            r.user_choice = "auto"
        elif r.level == DiffLevel.ORPHAN:
            # Take whichever side has content
            r.user_choice = "A" if r.text_a else "B"
        else:
            # SMALL / LARGE: default to A
            r.user_choice = "A"


def _llm_judge(results, llm_backend: str):
    """Use LLM to re-judge diff segments: if two texts are semantically
    equivalent, downgrade the diff level to SAME.

    Current: prints notice. Full implementation pending backend integration.
    """
    click.echo(f"LLM 精判: 后端 '{llm_backend}' 尚未实现，使用算法结果。")


def _interactive_review(results, source_a, source_b, audio, segs_a, segs_b):
    """Interactive diff review at paragraph level."""
    needs_review = [r for r in results if r.level != DiffLevel.SAME]
    if not needs_review:
        click.echo("两份转写完全一致，无需人工确认。")
        return

    click.echo(f"\n开始逐段确认 ({len(needs_review)} 段需要审核):")
    click.echo("  [A]保留A  [B]保留B  [E]手动编辑  [P]回听音频  [S]跳过  [Q]退出\n")

    for r in results:
        if r.level == DiffLevel.SAME:
            r.user_choice = "auto"
            continue

        _display_diff(r, source_a, source_b)

        choice = _get_user_choice(audio, r, segs_a, segs_b)
        if choice == "q":
            click.echo("已退出。当前进度未保存。")
            sys.exit(0)

        r.user_choice = choice

        if choice == "manual":
            edited = click.prompt("  输入修正文本", type=str)
            r.user_edited_text = edited


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


def _get_user_choice(audio_path: str | None, r, segs_a, segs_b) -> str:
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
                _play_segment(audio_path, r, segs_a, segs_b)
            else:
                click.echo("  未指定音频文件，无法回听。请用 --audio 指定。")
            continue
        elif choice == "q":
            return "q"
        else:
            click.echo("  无效选择，请输入 A/B/E/P/S/Q")


def _play_segment(audio_path: str, r, segs_a, segs_b):
    """Play the original audio segments referenced by this DiffResult.

    Uses seg_indices to locate the precise original segments,
    avoiding the merged span's exaggerated time range.
    """
    # Prefer A-side segments if available, otherwise B-side
    indices = r.seg_indices_a if r.seg_indices_a else r.seg_indices_b
    source_segs = segs_a if r.seg_indices_a else segs_b

    if not indices or not source_segs:
        click.echo("  无法定位原始音频段落")
        return

    start = source_segs[indices[0]].start
    end = source_segs[indices[-1]].end

    duration = end - start
    ffplay = shutil.which("ffplay")
    if not ffplay:
        click.echo(f"  未找到 ffplay。请手动跳转到 {start:.1f}s 处播放音频")
        return

    # Cap playback at 15 seconds to avoid overly long replays
    if duration > 15:
        end = start + 15
        duration = 15
        click.echo(f"  播放中... ({start:.1f}s -> {end:.1f}s, 已截断)")
    else:
        click.echo(f"  播放中... ({start:.1f}s -> {end:.1f}s)")
    subprocess.run(
        [ffplay, "-ss", str(start), "-t", str(duration),
         "-nodisp", "-autoexit", "-loglevel", "quiet", audio_path],
        check=False,
    )
