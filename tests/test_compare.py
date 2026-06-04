"""Tests for compare command (non-interactive parts)."""

from meeting_cli.diff.engine import DiffResult, DiffLevel, align_segments
from meeting_cli.backends.transcriber import Segment


def make_segments(pairs: list[tuple[float, float, str]]) -> list[Segment]:
    return [Segment(start=s, end=e, text=t) for s, e, t in pairs]


class TestCompareIntegration:
    def test_full_alignment_pipeline(self):
        """Test the complete alignment pipeline from two transcript lists."""
        a = make_segments([
            (0.0, 3.0, "大家好欢迎参加会议"),
            (3.0, 8.0, "今天讨论Q2预算分配"),
            (8.0, 15.0, "首先由财务部汇报数据"),
        ])
        b = make_segments([
            (0.0, 3.5, "大家好欢迎参会"),       # 小差异
            (3.5, 8.0, "今天讨论Q2预算分配"),   # 一致
            (8.0, 15.0, "首先由财务部报告"),     # 小差异
        ])
        results = align_segments(a, b)
        assert len(results) == 3
        # The middle segment should be nearly identical
        middle = results[1]
        assert middle.level in (DiffLevel.SAME, DiffLevel.SMALL)

    def test_filter_results_for_review(self):
        """Only SMALL, LARGE, ORPHAN should be shown for review."""
        results = [
            DiffResult(level=DiffLevel.SAME, text_a="a", text_b="a", segment_index=0),
            DiffResult(level=DiffLevel.SMALL, text_a="a", text_b="b", segment_index=1),
            DiffResult(level=DiffLevel.LARGE, text_a="a", text_b="c", segment_index=2),
            DiffResult(level=DiffLevel.ORPHAN, text_a="a", segment_index=3),
        ]
        needs_review = [r for r in results if r.level != DiffLevel.SAME]
        assert len(needs_review) == 3

    def test_build_final_transcript_after_choices(self):
        """Simulate user making choices and building the final transcript."""
        from meeting_cli.diff.reporter import build_final_transcript

        results = [
            DiffResult(
                level=DiffLevel.LARGE,
                start_a=0.0, end_a=3.0, text_a="Q2预算上调15%",
                start_b=0.0, end_b=3.0, text_b="Q2预算上调50%",
                segment_index=0,
            ),
            DiffResult(
                level=DiffLevel.SAME,
                start_a=3.0, end_a=8.0, text_a="财务部汇报数据",
                start_b=3.0, end_b=8.0, text_b="财务部汇报数据",
                segment_index=1,
            ),
        ]
        results[0].user_choice = "manual"
        results[0].user_edited_text = "Q2预算上调15%"
        results[1].user_choice = "auto"

        final = build_final_transcript(results)
        assert "Q2预算上调15%" in final
        assert "Q2预算上调50%" not in final
        assert "财务部汇报数据" in final
