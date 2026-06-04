"""Tests for download command."""

from meeting_cli.commands.download import build_yt_dlp_args


class TestBuildYtDlpArgs:
    def test_audio_only_default(self):
        args = build_yt_dlp_args(
            url="https://example.com/video",
            output_dir="/tmp/out",
            audio_only=True,
            keep_video=False,
        )
        assert args[0] == "yt-dlp"
        assert "-x" in args
        assert "--audio-format" in args
        assert "mp3" in args
        assert "https://example.com/video" in args[-1]

    def test_keep_video(self):
        args = build_yt_dlp_args(
            url="https://example.com/video",
            output_dir="/tmp/out",
            audio_only=False,
            keep_video=True,
        )
        assert "-x" not in args
        assert "--audio-format" not in args

    def test_output_template(self):
        args = build_yt_dlp_args(
            url="https://example.com/video",
            output_dir="/tmp/meetings",
            audio_only=True,
            keep_video=False,
        )
        output_arg_idx = args.index("-o")
        output_path = args[output_arg_idx + 1]
        # Normalise path separators for cross-platform (Windows vs Unix)
        assert output_path.replace("\\", "/").startswith("/tmp/meetings")

    def test_bilibili_cookies_flag(self):
        args = build_yt_dlp_args(
            url="https://www.bilibili.com/video/BV1xx",
            output_dir="/tmp/out",
            audio_only=True,
            keep_video=False,
            cookies_file="/path/to/cookies.txt",
        )
        assert "--cookies" in args
        cookie_idx = args.index("--cookies")
        assert args[cookie_idx + 1] == "/path/to/cookies.txt"
