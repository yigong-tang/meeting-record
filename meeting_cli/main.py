"""meeting-cli: 会议录制处理工具"""

import click

from meeting_cli.commands import download, transcribe, compare, summarize, subtitle


@click.group()
@click.version_option(version="0.1.0", prog_name="meeting-cli")
def cli():
    """会议录制处理CLI：下载 → 转写 → 对比 → 总结"""
    pass


cli.add_command(download.download)
cli.add_command(transcribe.transcribe)
cli.add_command(compare.compare)
cli.add_command(summarize.summarize)
cli.add_command(subtitle.subtitle)
