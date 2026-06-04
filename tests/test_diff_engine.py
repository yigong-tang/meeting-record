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
    def test_identical_content(self):
        """Same text content → all SAME."""
        a = make_segments([(0, 2, "你好"), (2, 5, "世界")])
        b = make_segments([(0, 2, "你好"), (2, 5, "世界")])
        results = align_segments(a, b)
        for r in results:
            assert r.level == DiffLevel.SAME

    def test_text_diff_detected(self):
        """Different text → not SAME."""
        a = make_segments([(0, 3, "预算上调15%")])
        b = make_segments([(0, 3, "预算上调50%")])
        results = align_segments(a, b)
        assert any(r.level != DiffLevel.SAME for r in results)

    def test_diff_segmentation_still_aligns(self):
        """Different segment boundaries, same content → aligns correctly."""
        a = make_segments([(0.0, 4.0, "我们决定将预算上调")])
        b = make_segments([
            (0.0, 2.0, "我们决定"),
            (2.0, 4.0, "将预算上调"),
        ])
        results = align_segments(a, b)
        # Since content is identical, should all be SAME
        assert all(r.level == DiffLevel.SAME for r in results)

    def test_orphan_segment_in_one_side(self):
        """Extra text only in B → ORPHAN."""
        a = make_segments([(0, 2, "第一句")])
        b = make_segments([(0, 2, "第一句"), (3, 5, "多出来的")])
        results = align_segments(a, b)
        orphans = [r for r in results if r.level == DiffLevel.ORPHAN]
        assert len(orphans) == 1

    def test_mismatched_content_with_diff(self):
        """Same structure, partially different text — differences detected."""
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
        assert len(results) > 0
        # At least one result should not be SAME (text differs)
        levels = [r.level for r in results]
        non_same = [l for l in levels if l != DiffLevel.SAME]
        assert len(non_same) > 0


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
