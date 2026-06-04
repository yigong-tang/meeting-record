"""Tests for summarize command and openai_compat backend."""

import pytest
from meeting_cli.backends.openai_compat import OpenAICompatSummarizer, _build_summary_prompt
from meeting_cli.commands.summarize import strip_timestamps


class TestStripTimestamps:
    def test_removes_timestamp_line_prefix(self):
        text = (
            "[00:00:00.000 -> 00:00:03.500] 大家好\n"
            "[00:00:03.500 -> 00:00:08.200] 欢迎参会\n"
        )
        result = strip_timestamps(text)
        assert "大家好" in result
        assert "欢迎参会" in result
        assert "[00:00" not in result

    def test_collapses_multiple_blank_lines(self):
        text = (
            "[00:00:00.000 -> 00:00:03.500] 第一句\n\n\n\n"
            "[00:00:03.500 -> 00:00:08.200] 第二句\n"
        )
        result = strip_timestamps(text)
        # Should not have 3+ consecutive newlines
        assert "\n\n\n" not in result

    def test_preserves_text_content(self):
        text = "[00:01:00.000 -> 00:01:05.000] Q2预算上调15%\n"
        result = strip_timestamps(text)
        assert "Q2预算上调15%" in result

    def test_handles_empty_input(self):
        result = strip_timestamps("")
        assert result == ""


class TestSummarizeCommand:
    def test_summarize_help(self):
        """Verify CLI entry can be imported and has expected interface."""
        from meeting_cli.commands.summarize import summarize
        assert callable(summarize.callback)


class TestOpenAICompatSummarizer:
    def test_name_is_openai(self):
        s = OpenAICompatSummarizer()
        assert s.name == "openai"

    def test_build_prompt_includes_transcript(self):
        """The summarize method should pass the transcript to the API
        with a structured prompt asking for meeting notes."""
        prompt = _build_summary_prompt("测试转写内容")
        assert "测试转写内容" in prompt
        assert "会议纪要" in prompt or "总结" in prompt or "摘要" in prompt

    def test_build_prompt_has_required_sections(self):
        """The prompt should request structured output with
        topics, decisions, action items, and summary."""
        prompt = _build_summary_prompt("test")
        required_keywords = ["议题", "决策", "待办", "摘要"]
        for kw in required_keywords:
            assert kw in prompt, f"Prompt missing keyword: {kw}"
