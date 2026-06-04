"""Tests for diff engine: alignment and difference grading."""

import pytest
from meeting_cli.backends.transcriber import Segment
from meeting_cli.diff.engine import (
    align_segments,
    grade_difference,
    DiffResult,
    DiffLevel,
)


def make_segments(pairs: list[tuple[float, float, str]]) -> list[Segment]:
    """Helper: create segments from (start, end, text) tuples."""
    return [Segment(start=s, end=e, text=t) for s, e, t in pairs]


class TestAlignSegments:
    def test_identical_timestamps_direct_match(self):
        a = make_segments([(0, 2, "你好"), (2, 5, "世界")])
        b = make_segments([(0, 2, "你好"), (2, 5, "世界")])
        results = align_segments(a, b)
        assert len(results) == 2
        assert results[0].level == DiffLevel.SAME

    def test_text_diff_detected(self):
        a = make_segments([(0, 3, "预算上调15%")])
        b = make_segments([(0, 3, "预算上调50%")])
        results = align_segments(a, b)
        assert len(results) == 1
        assert results[0].level != DiffLevel.SAME

    def test_timestamp_offset_within_threshold(self):
        """Slightly offset timestamps should still align."""
        a = make_segments([(0.0, 2.0, "大家好")])
        b = make_segments([(0.5, 2.3, "大家好")])
        results = align_segments(a, b)
        assert len(results) == 1
        assert results[0].level == DiffLevel.SAME

    def test_orphan_segment_in_one_side(self):
        """A segment missing from one side becomes orphan."""
        a = make_segments([(0, 2, "第一句")])
        b = make_segments([(0, 2, "第一句"), (3, 5, "多出来的")])
        results = align_segments(a, b)
        assert len(results) == 2
        orphans = [r for r in results if r.level == DiffLevel.ORPHAN]
        assert len(orphans) == 1
        assert orphans[0].text_b == "多出来的"

    def test_mismatched_count_with_diff(self):
        """Whisper splits into 3 segments, Aliyun into 2."""
        a = make_segments([
            (0, 2, "我们决定"),
            (2, 4, "将预算"),
            (4, 6, "上调15%"),
        ])
        b = make_segments([
            (0, 3, "我们决定将预算"),
            (3, 6, "上调50%"),
        ])
        results = align_segments(a, b)
        # Should produce some alignment, detecting text differences
        assert len(results) > 0
        levels = [r.level for r in results]
        assert DiffLevel.LARGE in levels or DiffLevel.SMALL in levels


class TestGradeDifference:
    def test_identical_text_is_same(self):
        result = grade_difference("大家好欢迎", "大家好欢迎")
        assert result == DiffLevel.SAME

    def test_small_difference(self):
        """Minor wording difference."""
        result = grade_difference(
            "我们决定将Q2预算上调15%",
            "我们决定将Q2预算上调大约15%",
        )
        assert result == DiffLevel.SMALL

    def test_large_difference(self):
        """Significant numerical difference."""
        result = grade_difference(
            "我们决定将Q2预算上调15%",
            "我们决定将Q2预算上调50%",
        )
        assert result == DiffLevel.LARGE

    def test_completely_different(self):
        result = grade_difference("今天天气很好", "预算需要大幅削减")
        assert result == DiffLevel.LARGE

    def test_one_side_empty_is_orphan(self):
        result = grade_difference("", "孤单的一句")
        assert result == DiffLevel.ORPHAN

    def test_both_empty_handled(self):
        result = grade_difference("", "")
        assert result == DiffLevel.SAME
