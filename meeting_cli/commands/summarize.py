"""summarize command: transcript -> structured meeting notes."""

import sys
from pathlib import Path

import click

from meeting_cli.backends import get_summarizer, list_summarizers


@click.command()
@click.argument("file", type=click.Path(exists=True))
@click.option(
    "--backend", "-b",
    default="openai",
    show_default=True,
    help="LLM后端（用于总结）",
)
@click.option(
    "--output-dir", "-o",
    default="./meeting-output",
    show_default=True,
    help="工作目录",
)
def summarize(file: str, backend: str, output_dir: str):
    """将转写记录总结为结构化会议纪要。

    FILE 可以是任意转写文件（带或不带时间戳均可）。
    产出 summary.md，包含议题、决策、待办事项和简短摘要。
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    transcript_path = Path(file)
    if not transcript_path.exists():
        click.echo(f"错误: 文件不存在: {file}", err=True)
        sys.exit(1)

    transcript = transcript_path.read_text(encoding="utf-8")

    summarizer = get_summarizer(backend)
    if summarizer is None:
        available = list_summarizers()
        click.echo(
            f"错误: 未知后端 '{backend}'。"
            f"可用: {', '.join(available) if available else '(无)'}",
            err=True,
        )
        sys.exit(1)

    click.echo(f"生成会议纪要中... 后端: {backend}")
    summary_md = summarizer.summarize(transcript)

    out_path = out_dir / "summary.md"
    out_path.write_text(summary_md, encoding="utf-8")
    click.echo(f"会议纪要已保存: {out_path}")
