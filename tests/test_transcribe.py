"""Tests for transcribe command and whisper backend."""

import pytest
from pathlib import Path
from meeting_cli.backends.whisper_local import WhisperLocalTranscriber
from meeting_cli.backends.transcriber import Segment


class TestWhisperLocalTranscriber:
    def test_name_is_whisper(self):
        t = WhisperLocalTranscriber()
        assert t.name == "whisper"

    def test_transcribe_requires_faster_whisper(self, tmp_path):
        """Creating a transcriber with invalid model should still work."""
        t = WhisperLocalTranscriber(model_size="tiny")
        assert t.model_size == "tiny"


class TestTranscribeOutputFormat:
    """Tests for the transcript file format (Segment -> timestamp text)."""

    def test_format_segment_to_line(self):
        from meeting_cli.commands.transcribe import format_segment_line

        seg = Segment(start=0.0, end=3.5, text="大家好")
        line = format_segment_line(seg)
        assert line == "[00:00:00.000 -> 00:00:03.500] 大家好"

    def test_format_segment_with_hours(self):
        from meeting_cli.commands.transcribe import format_segment_line

        seg = Segment(start=3661.0, end=3665.5, text="测试")
        line = format_segment_line(seg)
        assert line == "[01:01:01.000 -> 01:01:05.500] 测试"


class TestParseTranscriptFile:
    """Tests for reading transcript files back in."""

    def test_parse_timestamped_transcript(self, sample_transcript_path):
        from meeting_cli.commands.transcribe import parse_transcript_file
        segments = parse_transcript_file(str(sample_transcript_path))
        assert len(segments) == 3
        assert segments[0].text == "大家好欢迎参加今天的会议"
        assert segments[0].start == 0.0
        assert segments[0].end == 3.5

    def test_roundtrip(self, tmp_path):
        """Write segments out, parse them back, should be identical."""
        from meeting_cli.commands.transcribe import (
            format_segment_line,
            parse_transcript_file,
        )
        original = [
            Segment(start=0.0, end=2.0, text="第一句"),
            Segment(start=2.0, end=4.0, text="第二句"),
        ]
        path = tmp_path / "test.txt"
        lines = [format_segment_line(s) for s in original]
        path.write_text("\n".join(lines), encoding="utf-8")

        parsed = parse_transcript_file(str(path))
        assert len(parsed) == 2
        assert parsed[0].text == original[0].text
        assert parsed[1].text == original[1].text

    def test_parse_skips_empty_lines(self, tmp_path):
        """Empty lines should be ignored."""
        from meeting_cli.commands.transcribe import parse_transcript_file
        path = tmp_path / "with-blanks.txt"
        path.write_text(
            "[00:00:00.000 -> 00:00:02.000] 第一句\n\n[00:00:02.000 -> 00:00:04.000] 第二句\n\n",
            encoding="utf-8",
        )
        segments = parse_transcript_file(str(path))
        assert len(segments) == 2
