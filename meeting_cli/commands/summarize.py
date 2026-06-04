"""summarize command: transcript -> merged text + structured meeting notes."""

import re
import sys
from pathlib import Path

import click

from meeting_cli.backends import get_summarizer, list_summarizers


def strip_timestamps(text: str) -> str:
    """Remove timestamp prefixes, merge into continuous paragraphs.

    Input:  '[00:00:00.000 -> 00:00:03.500] 大家好，欢迎参加\n'
    Output: '大家好，欢迎参加\\n'
    """
    # Remove "[HH:MM:SS -> HH:MM:SS] " or "[HH:MM:SS.mmm -> HH:MM:SS.mmm] " prefixes
    stripped = re.sub(
        r"\[\d{2}:\d{2}:\d{2}(?:\.\d{3})? -> \d{2}:\d{2}:\d{2}(?:\.\d{3})?\]\s*",
        "",
        text,
    )
    # Collapse multiple blank lines
    stripped = re.sub(r"\n{3,}", "\n\n", stripped)
    return stripped.strip()


@click.command()
@click.argument("file", type=click.Path(exists=True))
@click.option(
    "--backend", "-b",
    default="openai",
    show_default=True,
    help="LLM后端（用于总结）；若不指定则不调用大模型",
)
@click.option(
    "--output-dir", "-o",
    default="./meeting-output",
    show_default=True,
    help="工作目录",
)
def summarize(file: str, backend: str, output_dir: str):
    """将转写记录总结为结构化会议纪要。

    先去时间戳合并为连续文本，然后调用 LLM 生成纪要。
    总是产出 merged-transcript.txt；LLM 可用时追加 summary.md。
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    transcript_path = Path(file)
    if not transcript_path.exists():
        click.echo(f"错误: 文件不存在: {file}", err=True)
        sys.exit(1)

    raw = transcript_path.read_text(encoding="utf-8")

    # 1. Strip timestamps & merge
    merged = strip_timestamps(raw)
    merged_path = out_dir / "merged-transcript.txt"
    merged_path.write_text(merged, encoding="utf-8")
    click.echo(f"合并文本已保存: {merged_path} ({len(raw)}→{len(merged)} 字符)")

    # 2. Try LLM summarization
    if not backend:
        click.echo("未指定后端，跳过总结。")
        return

    summarizer = get_summarizer(backend)
    if summarizer is None:
        available = list_summarizers()
        click.echo(
            f"警告: 未知后端 '{backend}'，仅输出了合并文本。"
            f"可用后端: {', '.join(available) if available else '(无)'}",
            err=True,
        )
        return

    click.echo(f"生成会议纪要中... 后端: {backend}")
    try:
        summary_md = summarizer.summarize(merged)
        if summary_md:
            out_path = out_dir / "summary.md"
            out_path.write_text(summary_md, encoding="utf-8")
            click.echo(f"会议纪要已保存: {out_path}")
        else:
            click.echo("警告: 大模型返回空结果，仅输出了合并文本。", err=True)
    except Exception as e:
        click.echo(
            f"警告: 大模型调用失败 ({e})，仅输出了合并文本。",
            err=True,
        )
