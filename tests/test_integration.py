"""End-to-end integration tests using mock backends."""

import pytest
from pathlib import Path
from click.testing import CliRunner

from meeting_cli.main import cli


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def sample_transcript_a(tmp_path):
    """Create a sample timestamped transcript file."""
    path = tmp_path / "trans-a.txt"
    path.write_text(
        "[00:00:00.000 -> 00:00:03.000] 大家好欢迎\n"
        "[00:00:03.000 -> 00:00:08.000] 讨论Q2预算\n"
        "[00:00:08.000 -> 00:00:15.000] 财务部汇报\n",
        encoding="utf-8",
    )
    return path


@pytest.fixture
def sample_transcript_b(tmp_path):
    """Create another sample transcript with intentional differences."""
    path = tmp_path / "trans-b.txt"
    path.write_text(
        "[00:00:00.000 -> 00:00:03.000] 大家好欢迎\n"
        "[00:00:03.000 -> 00:00:08.500] 讨论Q2预算分配\n"
        "[00:00:08.500 -> 00:00:15.000] 财务部报告\n",
        encoding="utf-8",
    )
    return path


class TestCLIBasics:
    def test_cli_help(self, runner):
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "download" in result.output
        assert "transcribe" in result.output
        assert "compare" in result.output
        assert "summarize" in result.output
        assert "subtitle" in result.output

    def test_download_help(self, runner):
        result = runner.invoke(cli, ["download", "--help"])
        assert result.exit_code == 0

    def test_transcribe_help(self, runner):
        result = runner.invoke(cli, ["transcribe", "--help"])
        assert result.exit_code == 0

    def test_compare_help(self, runner):
        result = runner.invoke(cli, ["compare", "--help"])
        assert result.exit_code == 0

    def test_summarize_help(self, runner):
        result = runner.invoke(cli, ["summarize", "--help"])
        assert result.exit_code == 0

    def test_subtitle_help(self, runner):
        result = runner.invoke(cli, ["subtitle", "--help"])
        assert result.exit_code == 0

    def test_download_dry_run(self, runner):
        result = runner.invoke(
            cli,
            ["download", "--dry-run", "https://www.bilibili.com/video/BV1xx"],
        )
        assert result.exit_code == 0
        assert "yt-dlp" in result.output

    def test_version(self, runner):
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output


class TestComparePipeline:
    def test_compare_with_sample_files(self, runner, tmp_path, sample_transcript_a, sample_transcript_b):
        """End-to-end compare pipeline with sample files."""
        out_dir = tmp_path / "output"
        result = runner.invoke(
            cli,
            [
                "compare",
                str(sample_transcript_a),
                str(sample_transcript_b),
                "-o", str(out_dir),
            ],
            input="a\na\n",  # choose A for all diff segments
        )
        assert result.exit_code == 0
        # Verify output files exist
        final_path = out_dir / "final-transcript.txt"
        assert final_path.exists()
        report_path = out_dir / "diff-report.html"
        assert report_path.exists()
        content = final_path.read_text(encoding="utf-8")
        assert "大家好欢迎" in content

    def test_compare_no_differences(self, runner, tmp_path, sample_transcript_a):
        """Compare a file against itself — should report 'no differences'."""
        out_dir = tmp_path / "output"
        result = runner.invoke(
            cli,
            [
                "compare",
                str(sample_transcript_a),
                str(sample_transcript_a),
                "-o", str(out_dir),
            ],
        )
        assert result.exit_code == 0
        assert "一致" in result.output

    def test_transcribe_requires_backend(self, runner):
        """transcribe without --backend should error."""
        result = runner.invoke(
            cli,
            ["transcribe", "nonexistent.mp3"],
        )
        assert result.exit_code != 0

    def test_summarize_requires_valid_file(self, runner):
        """summarize with missing file should error."""
        result = runner.invoke(
            cli,
            ["summarize", "nonexistent.txt"],
        )
        assert result.exit_code != 0

    def test_compare_outputs_final_transcript_with_correct_format(self, runner, tmp_path, sample_transcript_a, sample_transcript_b):
        """The final transcript should have valid timestamp format."""
        out_dir = tmp_path / "output"
        result = runner.invoke(
            cli,
            [
                "compare",
                str(sample_transcript_a),
                str(sample_transcript_b),
                "-o", str(out_dir),
            ],
            input="a\na\n",
        )
        assert result.exit_code == 0
        final = (out_dir / "final-transcript.txt").read_text(encoding="utf-8")
        # Verify timestamp format
        assert "[" in final and "]" in final
        assert " -> " in final
