"""OpenAI-compatible LLM summarization backend.

Works with any OpenAI-compatible API endpoint including:
- OpenAI (api.openai.com)
- DeepSeek (api.deepseek.com)
- DashScope / Qwen (dashscope.aliyuncs.com)
- Local Ollama (localhost:11434)
"""

import sys
from meeting_cli.backends.summarizer import BaseSummarizer
from meeting_cli.utils.config import get_backend_config


SUMMARY_SYSTEM_PROMPT = """你是一个专业的会议纪要助手。请根据以下会议转写记录生成结构化的会议纪要。

要求：
1. 提取基本信息（如可从内容推断日期、参会人等）
2. 列出主要议题，每个议题下列出讨论要点
3. 提取所有明确的关键决策
4. 提取所有待办事项，包括负责人和截止日期（如果提及）
5. 在文末附上一段话的简短摘要

输出格式：纯 Markdown，不要包含代码块标记。"""


def _build_summary_prompt(transcript: str) -> str:
    """Build the full prompt for the LLM summarization call.

    Args:
        transcript: The full meeting transcript text.

    Returns:
        A prompt string ready to send as a user message.
    """
    return (
        f"请为以下会议转写记录生成结构化纪要：\n\n"
        f"{transcript}\n\n"
        f"请按以下结构输出：\n"
        f"## 基本信息\n"
        f"## 主要议题\n"
        f"## 关键决策\n"
        f"## 待办事项\n"
        f"## 简短摘要"
    )


class OpenAICompatSummarizer(BaseSummarizer):
    """Summarizer backed by any OpenAI-compatible chat completions API.

    Configuration via environment variables:
        {NAME}_API_KEY   -- API key (required)
        {NAME}_BASE_URL  -- Optional custom endpoint URL
    """

    name = "openai"

    def __init__(self, backend_name: str = "openai"):
        """Initialize with config for a named backend.

        Args:
            backend_name: Slug used to look up env vars
                (e.g. 'openai', 'deepseek', 'dashscope').
        """
        self.backend_name = backend_name
        config = get_backend_config(backend_name)
        self.api_key = config["api_key"]
        self.base_url = config["base_url"]

    def summarize(self, transcript: str) -> str:
        """Summarize a transcript using the configured LLM backend.

        Args:
            transcript: Full meeting transcript.

        Returns:
            Markdown-formatted meeting summary.
        """
        if not self.api_key:
            print(
                f"错误: 未设置 {self.backend_name.upper()}_API_KEY 环境变量",
                file=sys.stderr,
            )
            sys.exit(1)

        try:
            from openai import OpenAI
        except ImportError:
            print(
                "错误: 需要安装 openai。运行: pip install openai",
                file=sys.stderr,
            )
            sys.exit(1)

        client_kwargs = {"api_key": self.api_key}
        if self.base_url:
            client_kwargs["base_url"] = self.base_url

        client = OpenAI(**client_kwargs)

        response = client.chat.completions.create(
            model="gpt-4o-mini",  # 默认轻量模型，可通过环境变量覆盖
            messages=[
                {"role": "system", "content": SUMMARY_SYSTEM_PROMPT},
                {"role": "user", "content": _build_summary_prompt(transcript)},
            ],
            temperature=0.3,
        )
        return response.choices[0].message.content or ""
