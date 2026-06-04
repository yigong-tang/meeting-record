"""download command: yt-dlp subprocess wrapper."""

import shutil
import subprocess
import sys
from pathlib import Path

import click

# Browser-like User-Agent，B站等平台需要，不影响其他站点
_DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
    "Referer": "https://www.bilibili.com",
}


def _check_ffmpeg():
    """Check if ffmpeg is available in PATH. Warn if not."""
    if shutil.which("ffmpeg") is None:
        click.echo(
            "警告: 未找到 ffmpeg。部分视频的音视频流将无法自动合并。\n"
            "  安装: winget install ffmpeg (Windows) 或 apt install ffmpeg (Linux)",
            err=True,
        )


def _cleanup_streams(output_dir: str):
    """Remove intermediate stream files left by yt-dlp.

    yt-dlp downloads separate audio/video streams then merges them.
    With --keep-video, these intermediate .f*.mp4 / .f*.m4a files
    are preserved alongside the final merged output. Clean them up.
    """
    out = Path(output_dir)
    for pattern in ["*.f*.mp4", "*.f*.m4a"]:
        for f in out.glob(pattern):
            f.unlink()


def build_yt_dlp_args(
    url: str,
    output_dir: str,
    audio_only: bool = True,
    keep_video: bool = False,
    cookies_file: str | None = None,
) -> list[str]:
    """Build the argument list for yt-dlp subprocess call.

    Args:
        url: The video URL to download.
        output_dir: Directory to save output files.
        audio_only: If True, extract audio only (default).
        keep_video: If True, keep the video file alongside audio.
        cookies_file: Optional path to a Netscape-format cookies file.

    Returns:
        List of command-line arguments for subprocess.
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    args = [
        "yt-dlp",
        "-o", str(out_dir / "%(title)s.%(ext)s"),
    ]

    # 默认浏览器 User-Agent（B站等平台需要）
    for header, value in _DEFAULT_HEADERS.items():
        args.extend(["--add-header", f"{header}:{value}"])

    if audio_only:
        args.extend(["-x", "--audio-format", "mp3"])
        if keep_video:
            args.append("--keep-video")  # 提取音频后保留合并后的视频
        else:
            args.append("--audio-quality")
            args.append("0")

    if cookies_file:
        args.extend(["--cookies", cookies_file])

    args.append(url)
    return args


@click.command()
@click.argument("url")
@click.option(
    "--output-dir", "-o",
    default="./meeting-output",
    show_default=True,
    help="工作目录，输出文件保存到此",
)
@click.option(
    "--audio-only/--no-audio-only",
    default=True,
    show_default=True,
    help="只下载音频（默认）",
)
@click.option(
    "--keep-video",
    is_flag=True,
    help="保留视频文件",
)
@click.option(
    "--cookies",
    default=None,
    help="Netscape格式的cookies文件路径（B站等需要登录的站点）",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="仅打印yt-dlp命令，不实际执行",
)
def download(
    url: str,
    output_dir: str,
    audio_only: bool,
    keep_video: bool,
    cookies: str | None,
    dry_run: bool,
):
    """从视频网站下载会议音频/视频。

    URL 可以是 B站、YouTube 等 yt-dlp 支持的任意平台。

    \b
    示例:
      meeting-cli download BV1xx -o my-meeting
      meeting-cli download BV1xx --no-audio-only --keep-video -o my-meeting
      meeting-cli download BV1xx --cookies cookies.txt
    """
    args = build_yt_dlp_args(
        url=url,
        output_dir=output_dir,
        audio_only=audio_only,
        keep_video=keep_video,
        cookies_file=cookies,
    )

    if dry_run:
        click.echo(" ".join(args))
        return

    _check_ffmpeg()

    click.echo(f"正在下载: {url}")
    click.echo(f"输出目录: {output_dir}")

    try:
        result = subprocess.run(args, check=False)
        if result.returncode != 0:
            click.echo(
                f"yt-dlp 退出码 {result.returncode}，"
                f"请检查 URL 是否正确、网络是否连通。",
                err=True,
            )
            sys.exit(result.returncode)
        _cleanup_streams(output_dir)
        click.echo(f"下载完成，文件保存在: {output_dir}")
    except FileNotFoundError:
        click.echo(
            "错误: 找不到 yt-dlp。请先安装: pip install yt-dlp",
            err=True,
        )
        sys.exit(1)
