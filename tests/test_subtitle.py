"""Tests for subtitle generation."""

from meeting_cli.commands.subtitle import segments_to_srt
from meeting_cli.backends.transcriber import Segment


class TestSegmentsToSrt:
    def test_basic_srt_generation(self):
        segments = [
            Segment(start=0.0, end=2.5, text="第一句台词"),
            Segment(start=2.5, end=5.0, text="第二句台词"),
        ]
        srt = segments_to_srt(segments)
        assert "1\n" in srt
        assert "00:00:00,000 --> 00:00:02,500" in srt
        assert "第一句台词" in srt
        assert "2\n" in srt
        assert "00:00:02,500 --> 00:00:05,000" in srt
        assert "第二句台词" in srt

    def test_empty_segments(self):
        srt = segments_to_srt([])
        assert srt == ""

    def test_srt_timestamp_format(self):
        """SRT uses comma for milliseconds, not period."""
        segments = [Segment(start=1.5, end=3.75, text="测试")]
        srt = segments_to_srt(segments)
        assert "00:00:01,500" in srt
        assert "00:00:03,750" in srt
