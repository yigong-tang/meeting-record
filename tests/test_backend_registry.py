"""Tests for backend registry, ABCs, and stub backends."""

import pytest
from meeting_cli.backends.transcriber import BaseTranscriber, Segment
from meeting_cli.backends.summarizer import BaseSummarizer
from meeting_cli.backends import (
    get_transcriber,
    list_transcribers,
    get_summarizer,
    list_summarizers,
)


# ---------------------------------------------------------------------------
# Segment dataclass
# ---------------------------------------------------------------------------

class TestSegment:
    def test_fields(self):
        seg = Segment(start=1.5, end=3.0, text="hello")
        assert seg.start == 1.5
        assert seg.end == 3.0
        assert seg.text == "hello"

    def test_repr(self):
        seg = Segment(0.0, 1.0, "test")
        assert "Segment(" in repr(seg)


# ---------------------------------------------------------------------------
# ABC enforcement — BaseTranscriber
# ---------------------------------------------------------------------------

class TestBaseTranscriberABC:
    def test_subclass_must_define_name(self):
        with pytest.raises(TypeError, match="name"):
            class BadTranscriber(BaseTranscriber):  # type: ignore[no-redef]
                def transcribe(self, audio_path):
                    return []

    def test_subclass_must_implement_transcribe(self):
        with pytest.raises(TypeError, match="transcribe"):
            class BadTranscriber(BaseTranscriber):  # type: ignore[no-redef]
                name = "bad"


# ---------------------------------------------------------------------------
# ABC enforcement — BaseSummarizer
# ---------------------------------------------------------------------------

class TestBaseSummarizerABC:
    def test_subclass_must_define_name(self):
        with pytest.raises(TypeError, match="name"):
            class BadSummarizer(BaseSummarizer):  # type: ignore[no-redef]
                def summarize(self, transcript):
                    return ""

    def test_subclass_must_implement_summarize(self):
        with pytest.raises(TypeError, match="summarize"):
            class BadSummarizer(BaseSummarizer):  # type: ignore[no-redef]
                name = "bad"


# ---------------------------------------------------------------------------
# Registry — transcribers
# ---------------------------------------------------------------------------

class TestTranscriberRegistry:
    def test_get_whisper(self):
        transcriber = get_transcriber("whisper")
        assert transcriber is not None
        assert transcriber.name == "whisper"
        # Verify it's the correct class
        from meeting_cli.backends.whisper_local import WhisperLocalTranscriber
        assert isinstance(transcriber, WhisperLocalTranscriber)

    def test_get_sensevoice(self):
        transcriber = get_transcriber("sensevoice")
        assert transcriber is not None
        assert transcriber.name == "sensevoice"

    def test_get_aliyun(self):
        transcriber = get_transcriber("aliyun")
        assert transcriber is not None
        assert transcriber.name == "aliyun"

    def test_get_iflytek(self):
        transcriber = get_transcriber("iflytek")
        assert transcriber is not None
        assert transcriber.name == "iflytek"

    def test_get_nonexistent_returns_none(self):
        assert get_transcriber("nonexistent") is None

    def test_list_transcribers_includes_all_stubs(self):
        names = list_transcribers()
        assert "whisper" in names
        assert "sensevoice" in names
        assert "aliyun" in names
        assert "iflytek" in names

    def test_returns_new_instance_each_call(self):
        t1 = get_transcriber("whisper")
        t2 = get_transcriber("whisper")
        assert t1 is not t2

    def test_transcriber_raises_not_implemented(self):
        transcriber = get_transcriber("whisper")
        with pytest.raises(NotImplementedError):
            transcriber.transcribe("dummy.wav")


# ---------------------------------------------------------------------------
# Registry — summarizers
# ---------------------------------------------------------------------------

class TestSummarizerRegistry:
    def test_get_openai(self):
        summarizer = get_summarizer("openai")
        assert summarizer is not None
        assert summarizer.name == "openai"
        from meeting_cli.backends.openai_compat import OpenAICompatSummarizer
        assert isinstance(summarizer, OpenAICompatSummarizer)

    def test_get_nonexistent_returns_none(self):
        assert get_summarizer("nonexistent") is None

    def test_list_summarizers_includes_openai(self):
        names = list_summarizers()
        assert "openai" in names

    def test_returns_new_instance_each_call(self):
        s1 = get_summarizer("openai")
        s2 = get_summarizer("openai")
        assert s1 is not s2

    def test_summarizer_raises_not_implemented(self):
        summarizer = get_summarizer("openai")
        with pytest.raises(NotImplementedError):
            summarizer.summarize("test transcript")
