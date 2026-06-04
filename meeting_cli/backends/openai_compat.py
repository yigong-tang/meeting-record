"""OpenAI-compatible LLM summarization backend.

Works with any OpenAI-compatible API endpoint including:

- OpenAI (api.openai.com)
- DeepSeek (api.deepseek.com)
- DashScope / Qwen (dashscope.aliyuncs.com)
- Local Ollama (localhost:11434)
"""

from meeting_cli.backends.summarizer import BaseSummarizer


class OpenAICompatSummarizer(BaseSummarizer):
    """Summarizer backed by any OpenAI-compatible chat completions API."""

    name = "openai"

    def summarize(self, transcript: str) -> str:
        """Placeholder: real implementation in later task."""
        raise NotImplementedError("OpenAI-compat summarizer not yet implemented")
