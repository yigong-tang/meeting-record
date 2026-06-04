"""Tests for diff report generation."""

from meeting_cli.diff.engine import DiffResult, DiffLevel
from meeting_cli.diff.reporter import build_html_report, build_final_transcript


class TestBuildHtmlReport:
    def test_generates_valid_html_with_all_levels(self, tmp_path):
        results = [
            DiffResult(
                level=DiffLevel.SAME,
                start_a=0.0, end_a=2.0, text_a="一致段落",
                start_b=0.0, end_b=2.0, text_b="一致段落",
                segment_index=0,
            ),
            DiffResult(
                level=DiffLevel.LARGE,
                start_a=3.0, end_a=5.0, text_a="版本A",
                start_b=3.0, end_b=5.0, text_b="版本B",
                segment_index=1,
            ),
        ]
        html = build_html_report(
            results, "trans-whisper.txt", "trans-aliyun.txt"
        )
        assert "<html" in html
        assert "trans-whisper.txt" in html
        assert "trans-aliyun.txt" in html
        assert "一致段落" in html
        assert "版本A" in html
        assert "版本B" in html

    def test_includes_user_choices_when_provided(self):
        """When a DiffResult has user_choice set, include it in the report."""
        r = DiffResult(
            level=DiffLevel.SMALL,
            start_a=0.0, end_a=2.0, text_a="A版文本",
            start_b=0.0, end_b=2.0, text_b="B版文本",
            segment_index=0,
        )
        r.user_choice = "A"
        html = build_html_report([r], "A", "B")
        assert "选择: A" in html


class TestBuildFinalTranscript:
    def test_merges_segments_with_choices(self):
        results = [
            DiffResult(
                level=DiffLevel.SAME,
                start_a=0.0, end_a=2.0, text_a="第一段",
                start_b=0.0, end_b=2.0, text_b="第一段",
                segment_index=0,
            ),
            DiffResult(
                level=DiffLevel.LARGE,
                start_a=2.0, end_a=5.0, text_a="A版第二段",
                start_b=2.0, end_b=5.0, text_b="B版第二段",
                segment_index=1,
            ),
        ]
        results[0].user_choice = "auto"
        results[1].user_choice = "A"

        transcript = build_final_transcript(results)
        assert "第一段" in transcript
        assert "A版第二段" in transcript
        assert "B版第二段" not in transcript

    def test_custom_edit_used_in_merge(self):
        results = [
            DiffResult(
                level=DiffLevel.LARGE,
                start_a=0.0, end_a=3.0, text_a="原文A",
                start_b=0.0, end_b=3.0, text_b="原文B",
                segment_index=0,
            ),
        ]
        results[0].user_choice = "manual"
        results[0].user_edited_text = "人工修正后的文本"

        transcript = build_final_transcript(results)
        assert "人工修正后的文本" in transcript
        assert "原文A" not in transcript
        assert "原文B" not in transcript

    def test_skip_removes_segment(self):
        results = [
            DiffResult(
                level=DiffLevel.ORPHAN,
                start_a=0.0, end_a=2.0, text_a="多余的段",
                segment_index=0,
            ),
        ]
        results[0].user_choice = "skip"
        transcript = build_final_transcript(results)
        assert "多余的段" not in transcript
