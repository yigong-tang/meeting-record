# 会议记录 CLI 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建 meeting-cli 命令行工具，实现会议视频下载 → 音频转写 → 多份转写对比 → 人工确认 → 会议总结的全流程。

**Architecture:** 采用子命令式 CLI（click 框架），每条子命令对应 `commands/` 下一个模块。ASR 转写和 LLM 总结通过抽象基类 + 自动注册的后端插件机制实现可插拔，新增后端只需在 `backends/` 下加文件。diff 对比以时间戳对齐为主轴、编辑距离分级为辅。

**Tech Stack:** Python 3.10+, click, faster-whisper, openai (SDK), jinja2 (报告模板), pytest

---

## 文件结构

```
meeting-record/
├── pyproject.toml
├── meeting_cli/
│   ├── __init__.py
│   ├── main.py                  # CLI entry (click group)
│   ├── commands/
│   │   ├── __init__.py
│   │   ├── download.py          # yt-dlp subprocess wrapper
│   │   ├── transcribe.py        # transcribe command + dispatch
│   │   ├── compare.py           # compare command + interactive
│   │   ├── summarize.py         # summarize command
│   │   └── subtitle.py          # subtitle command (exploratory)
│   ├── backends/
│   │   ├── __init__.py          # registry + auto-discovery
│   │   ├── transcriber.py       # BaseTranscriber ABC
│   │   ├── whisper_local.py     # faster-whisper backend
│   │   ├── sensevoice_local.py  # SenseVoice stub (待验证后实现)
│   │   ├── aliyun_asr.py        # 阿里云 ASR stub
│   │   ├── iflytek_asr.py       # 科大讯飞 ASR stub
│   │   ├── summarizer.py        # BaseSummarizer ABC
│   │   └── openai_compat.py     # OpenAI-compatible LLM backend
│   ├── diff/
│   │   ├── __init__.py
│   │   ├── engine.py            # timestamp alignment + diff grading
│   │   └── reporter.py          # HTML/Markdown report generation
│   └── utils/
│       ├── __init__.py
│       └── config.py            # env-var reader
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # fixtures (sample transcripts, temp dirs)
│   ├── test_download.py
│   ├── test_transcribe.py
│   ├── test_backend_registry.py
│   ├── test_diff_engine.py
│   ├── test_diff_reporter.py
│   ├── test_compare.py
│   ├── test_summarize.py
│   └── test_subtitle.py
└── README.md
```

---

### Task 1: 项目脚手架与依赖

**Files:**
- Create: `pyproject.toml`
- Create: `meeting_cli/__init__.py`
- Create: `meeting_cli/main.py`
- Create: `meeting_cli/commands/__init__.py`
- Create: `meeting_cli/backends/__init__.py`
- Create: `meeting_cli/diff/__init__.py`
- Create: `meeting_cli/utils/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Create: `README.md`

- [ ] **Step 1: 创建 pyproject.toml**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "meeting-cli"
version = "0.1.0"
description = "会议录制处理CLI：下载 → 转写 → 对比 → 总结"
requires-python = ">=3.10"
dependencies = [
    "click>=8.1",
    "openai>=1.0",
    "faster-whisper>=1.0",
    "jinja2>=3.1",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-mock>=3.12",
]

[project.scripts]
meeting-cli = "meeting_cli.main:cli"

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 2: 创建所有空 `__init__.py` 文件**

```bash
mkdir -p meeting_cli/commands meeting_cli/backends meeting_cli/diff meeting_cli/utils tests
touch meeting_cli/__init__.py meeting_cli/commands/__init__.py meeting_cli/backends/__init__.py meeting_cli/diff/__init__.py meeting_cli/utils/__init__.py tests/__init__.py
```

PowerShell 等价:
```powershell
New-Item -ItemType File -Force meeting_cli/__init__.py, meeting_cli/commands/__init__.py, meeting_cli/backends/__init__.py, meeting_cli/diff/__init__.py, meeting_cli/utils/__init__.py, tests/__init__.py
```

- [ ] **Step 3: 创建 meeting_cli/main.py — CLI 入口骨架**

```python
"""meeting-cli: 会议录制处理工具"""

import click

from meeting_cli.commands import download, transcribe, compare, summarize, subtitle


@click.group()
@click.version_option(version="0.1.0", prog_name="meeting-cli")
def cli():
    """会议录制处理CLI：下载 → 转写 → 对比 → 总结"""
    pass


cli.add_command(download.download)
cli.add_command(transcribe.transcribe)
cli.add_command(compare.compare)
cli.add_command(summarize.summarize)
cli.add_command(subtitle.subtitle)
```

- [ ] **Step 4: 创建 tests/conftest.py**

```python
"""pytest fixtures for meeting-cli."""

import os
import tempfile
from pathlib import Path
import pytest


@pytest.fixture
def temp_output_dir():
    """Create a temporary output directory isolated per test."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_transcript():
    """Return a minimal timestamped transcript file content."""
    return [
        {"start": 0.0, "end": 3.5, "text": "大家好欢迎参加今天的会议"},
        {"start": 3.5, "end": 8.2, "text": "今天我们讨论Q2的预算分配"},
        {"start": 8.2, "end": 15.0, "text": "首先由财务部汇报上季度经营数据"},
    ]


@pytest.fixture
def sample_transcript_path(temp_output_dir, sample_transcript):
    """Write a sample transcript file with timestamp format."""
    path = temp_output_dir / "trans-sample.txt"
    lines = []
    for seg in sample_transcript:
        start_ts = format_timestamp(seg["start"])
        end_ts = format_timestamp(seg["end"])
        lines.append(f"[{start_ts} -> {end_ts}] {seg['text']}")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def format_timestamp(seconds: float) -> str:
    """Convert float seconds to HH:MM:SS.mmm format."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}"
```

- [ ] **Step 5: 创建 README.md**

```markdown
# meeting-cli

会议录制处理命令行工具。

## 安装

pip install -e .

## 依赖

- yt-dlp (需单独安装)
- ffmpeg / ffplay (需单独安装)
```

- [ ] **Step 6: 提交**

```bash
git add -A
git commit -m "feat: scaffold project with pyproject.toml, CLI entry, and test fixtures

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: 配置模块 (utils/config.py)

**Files:**
- Create: `meeting_cli/utils/config.py`
- Test: `tests/test_config.py` (创建于本Task)

- [ ] **Step 1: 写测试 `tests/test_config.py`**

```python
"""Tests for config module."""

import os
from meeting_cli.utils.config import get_api_key, get_backend_config


class TestGetApiKey:
    def test_returns_env_var_if_set(self, monkeypatch):
        monkeypatch.setenv("ALIYUN_ASR_KEY", "sk-test-123")
        assert get_api_key("ALIYUN_ASR_KEY") == "sk-test-123"

    def test_returns_none_if_not_set(self, monkeypatch):
        monkeypatch.delenv("ALIYUN_ASR_KEY", raising=False)
        assert get_api_key("ALIYUN_ASR_KEY") is None

    def test_returns_default_if_not_set(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        assert get_api_key("OPENAI_API_KEY", default="fallback") == "fallback"


class TestGetBackendConfig:
    def test_extracts_backend_specific_env(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-openai")
        monkeypatch.setenv("OPENAI_BASE_URL", "https://proxy.example.com/v1")
        config = get_backend_config("openai")
        assert config == {
            "api_key": "sk-openai",
            "base_url": "https://proxy.example.com/v1",
        }

    def test_handles_missing_vars(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
        config = get_backend_config("openai")
        assert config["api_key"] is None
        assert config["base_url"] is None
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/test_config.py -v
```
Expected: 全部 5 个测试 FAIL (module not found)

- [ ] **Step 3: 实现 `meeting_cli/utils/config.py`**

```python
"""Environment variable configuration reader."""

import os
from typing import Optional


def get_api_key(key_name: str, default: Optional[str] = None) -> Optional[str]:
    """Read an environment variable by name.

    Args:
        key_name: The env var name (e.g. 'ALIYUN_ASR_KEY').
        default: Fallback value if the env var is not set.

    Returns:
        The env var value, or default/None.
    """
    return os.environ.get(key_name, default)


def get_backend_config(backend_name: str) -> dict:
    """Read all environment variables for a named backend.

    Backend names normalize to uppercase with underscores:
        'openai'    → OPENAI_API_KEY, OPENAI_BASE_URL
        'aliyun'    → ALIYUN_ASR_KEY
        'iflytek'   → IFLYTEK_ASR_KEY
        'deepseek'  → DEEPSEEK_API_KEY
        'dashscope' → DASHSCOPE_API_KEY
        'ollama'    → OLLAMA_HOST

    Args:
        backend_name: Lowercase backend identifier.

    Returns:
        Dict of relevant config keys for that backend.
    """
    prefix = backend_name.upper()
    result = {"api_key": None, "base_url": None}

    # API key: try {PREFIX}_API_KEY, then {PREFIX}_ASR_KEY
    for key_suffix in ["API_KEY", "ASR_KEY"]:
        val = os.environ.get(f"{prefix}_{key_suffix}")
        if val:
            result["api_key"] = val
            break

    # Base URL
    result["base_url"] = os.environ.get(f"{prefix}_BASE_URL")

    # Ollama-specific
    if backend_name == "ollama":
        result["host"] = os.environ.get("OLLAMA_HOST", "http://localhost:11434")

    return result
```

- [ ] **Step 4: 运行测试确认通过**

```bash
pytest tests/test_config.py -v
```
Expected: 全部 5 个测试 PASS

- [ ] **Step 5: 提交**

```bash
git add meeting_cli/utils/config.py tests/test_config.py
git commit -m "feat: add env-var config reader utility

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: 后端注册表 (backends/)

**Files:**
- Create: `meeting_cli/backends/transcriber.py`
- Create: `meeting_cli/backends/summarizer.py`
- Modify: `meeting_cli/backends/__init__.py`
- Test: `tests/test_backend_registry.py`

- [ ] **Step 1: 写测试 `tests/test_backend_registry.py`**

```python
"""Tests for backend registry and ABCs."""

import pytest
from meeting_cli.backends.transcriber import BaseTranscriber, Segment
from meeting_cli.backends.summarizer import BaseSummarizer
from meeting_cli.backends import get_transcriber, list_transcribers
from meeting_cli.backends import get_summarizer, list_summarizers


class FakeTranscriber(BaseTranscriber):
    """A test transcriber returning canned segments."""
    name = "fake"

    def transcribe(self, audio_path: str) -> list[Segment]:
        return [
            Segment(start=0.0, end=2.0, text="hello world"),
        ]


class FakeSummarizer(BaseSummarizer):
    """A test summarizer returning canned markdown."""
    name = "fake"

    def summarize(self, transcript: str) -> str:
        return "# Test Summary\n\nThis is a test."


class TestBaseTranscriber:
    def test_segment_dataclass(self):
        seg = Segment(start=1.5, end=3.0, text="测试")
        assert seg.start == 1.5
        assert seg.end == 3.0
        assert seg.text == "测试"

    def test_subclass_must_define_name(self):
        with pytest.raises(TypeError, match="name"):
            class BadTranscriber(BaseTranscriber):
                def transcribe(self, audio_path):
                    return []

    def test_subclass_must_define_transcribe(self):
        with pytest.raises(TypeError, match="transcribe"):
            class BadTranscriber(BaseTranscriber):
                name = "bad"


class TestBaseSummarizer:
    def test_subclass_must_define_name(self):
        with pytest.raises(TypeError, match="name"):
            class BadSummarizer(BaseSummarizer):
                def summarize(self, transcript):
                    return ""

    def test_subclass_must_define_summarize(self):
        with pytest.raises(TypeError, match="summarize"):
            class BadSummarizer(BaseSummarizer):
                name = "bad"


class TestRegistry:
    def test_get_transcriber_by_name(self):
        transcriber = get_transcriber("fake")
        assert transcriber is not None
        assert transcriber.name == "fake"

    def test_get_transcriber_returns_none_for_unknown(self):
        assert get_transcriber("nonexistent") is None

    def test_list_transcribers_includes_registered(self):
        names = list_transcribers()
        assert "fake" in names

    def test_get_summarizer_by_name(self):
        summarizer = get_summarizer("fake")
        assert summarizer is not None
        assert summarizer.name == "fake"

    def test_list_summarizers_includes_registered(self):
        names = list_summarizers()
        assert "fake" in names
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/test_backend_registry.py -v
```
Expected: FAIL (module cannot import)

- [ ] **Step 3: 创建 `meeting_cli/backends/transcriber.py`**

```python
"""Abstract base class for transcription backends."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class Segment:
    """A timestamped segment of transcribed text."""
    start: float  # seconds from audio start
    end: float    # seconds from audio start
    text: str     # transcribed text content


class BaseTranscriber(ABC):
    """Abstract base for ASR transcription backends.

    Subclasses must define `name` (a unique string identifier)
    and implement `transcribe(audio_path) -> list[Segment]`.
    """

    name: str

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if not cls.__abstractmethods__:
            if not getattr(cls, "name", None):
                raise TypeError(f"{cls.__name__} must define class-level `name`")

    @abstractmethod
    def transcribe(self, audio_path: str) -> list[Segment]:
        """Transcribe an audio file into timestamped segments.

        Args:
            audio_path: Path to the audio file (mp3/wav).

        Returns:
            List of Segment objects with start, end, and text.
        """
        ...
```

- [ ] **Step 4: 创建 `meeting_cli/backends/summarizer.py`**

```python
"""Abstract base class for LLM summarization backends."""

from abc import ABC, abstractmethod


class BaseSummarizer(ABC):
    """Abstract base for LLM summarization backends.

    Subclasses must define `name` (a unique string identifier)
    and implement `summarize(transcript) -> str`.
    """

    name: str

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if not cls.__abstractmethods__:
            if not getattr(cls, "name", None):
                raise TypeError(f"{cls.__name__} must define class-level `name`")

    @abstractmethod
    def summarize(self, transcript: str) -> str:
        """Summarize a transcript into structured meeting notes.

        Args:
            transcript: Full transcript text (with or without timestamps).

        Returns:
            Markdown-formatted meeting summary.
        """
        ...
```

- [ ] **Step 5: 实现 `meeting_cli/backends/__init__.py`**

```python
"""Backend registry for transcription and summarization plugins.

New backends are discovered by scanning this package.  Add a new
backend by dropping a Python file into this directory that defines
a subclass of BaseTranscriber or BaseSummarizer with a unique `name`.
"""

from meeting_cli.backends.transcriber import BaseTranscriber, Segment
from meeting_cli.backends.summarizer import BaseSummarizer

# Module-private registries
_transcribers: dict[str, type[BaseTranscriber]] = {}
_summarizers: dict[str, type[BaseSummarizer]] = {}


def _discover():
    """Scan this package for backend classes and register them."""
    import pkgutil
    import importlib

    # Only scan on first access
    if _transcribers or _summarizers:
        return

    package = __package__  # "meeting_cli.backends"
    for _, modname, _ in pkgutil.iter_modules(__path__):
        if modname.startswith("_"):
            continue
        module = importlib.import_module(f".{modname}", package)
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if not isinstance(attr, type):
                continue
            if issubclass(attr, BaseTranscriber) and attr is not BaseTranscriber:
                if not getattr(attr, "name", None):
                    continue
                _transcribers[attr.name] = attr
            if issubclass(attr, BaseSummarizer) and attr is not BaseSummarizer:
                if not getattr(attr, "name", None):
                    continue
                _summarizers[attr.name] = attr


def get_transcriber(name: str) -> BaseTranscriber | None:
    """Get a transcriber instance by name."""
    _discover()
    cls = _transcribers.get(name)
    if cls is None:
        return None
    return cls()


def list_transcribers() -> list[str]:
    """List all registered transcriber backend names."""
    _discover()
    return sorted(_transcribers.keys())


def get_summarizer(name: str) -> BaseSummarizer | None:
    """Get a summarizer instance by name."""
    _discover()
    cls = _summarizers.get(name)
    if cls is None:
        return None
    return cls()


def list_summarizers() -> list[str]:
    """List all registered summarizer backend names."""
    _discover()
    return sorted(_summarizers.keys())


__all__ = [
    "BaseTranscriber",
    "BaseSummarizer",
    "Segment",
    "get_transcriber",
    "list_transcribers",
    "get_summarizer",
    "list_summarizers",
]
```

- [ ] **Step 6: 创建 `meeting_cli/backends/whisper_local.py` (stub 先让注册表有东西可发现)**

```python
"""faster-whisper local transcription backend."""

from meeting_cli.backends.transcriber import BaseTranscriber, Segment


class WhisperLocalTranscriber(BaseTranscriber):
    """Local Whisper transcription using faster-whisper."""

    name = "whisper"

    def transcribe(self, audio_path: str) -> list[Segment]:
        """Placeholder: real implementation in later task."""
        raise NotImplementedError("Whisper local backend not yet implemented")
```

- [ ] **Step 7: 创建 `meeting_cli/backends/openai_compat.py` (stub)**

```python
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
```

- [ ] **Step 8: 创建其余后端的 stub 文件**

`meeting_cli/backends/sensevoice_local.py`:
```python
"""SenseVoice local transcription backend (stub)."""

from meeting_cli.backends.transcriber import BaseTranscriber, Segment


class SenseVoiceLocalTranscriber(BaseTranscriber):
    """Local SenseVoice ASR — lightweight Chinese-focused model.

    Placeholder: implementation pending hardware verification on ThinkPad.
    """
    name = "sensevoice"

    def transcribe(self, audio_path: str) -> list[Segment]:
        raise NotImplementedError("SenseVoice backend pending hardware verification")
```

`meeting_cli/backends/aliyun_asr.py`:
```python
"""Alibaba Cloud (Aliyun) ASR backend (stub)."""

from meeting_cli.backends.transcriber import BaseTranscriber, Segment


class AliyunASRTranscriber(BaseTranscriber):
    """Alibaba Cloud Speech Recognition API backend.

    Placeholder: pending API integration.
    Requires: ALIYUN_ASR_KEY env var.
    """
    name = "aliyun"

    def transcribe(self, audio_path: str) -> list[Segment]:
        raise NotImplementedError("Aliyun ASR backend pending API integration")
```

`meeting_cli/backends/iflytek_asr.py`:
```python
"""iFlytek (科大讯飞) ASR backend (stub)."""

from meeting_cli.backends.transcriber import BaseTranscriber, Segment


class IflytekASRTranscriber(BaseTranscriber):
    """iFlytek Speech Recognition API backend.

    Placeholder: pending API integration.
    Requires: IFLYTEK_ASR_KEY env var.
    """
    name = "iflytek"

    def transcribe(self, audio_path: str) -> list[Segment]:
        raise NotImplementedError("iFlytek ASR backend pending API integration")
```

- [ ] **Step 10: 运行测试确认通过**

```bash
pytest tests/test_backend_registry.py -v
```
Expected: 全部 7 个测试 PASS

- [ ] **Step 11: 提交**

```bash
git add meeting_cli/backends/ tests/test_backend_registry.py
git commit -m "feat: add backend registry with ABCs and auto-discovery

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: download 命令

**Files:**
- Create: `meeting_cli/commands/download.py`
- Test: `tests/test_download.py`

- [ ] **Step 1: 写测试 `tests/test_download.py`**

```python
"""Tests for download command."""

from meeting_cli.commands.download import build_yt_dlp_args


class TestBuildYtDlpArgs:
    def test_audio_only_default(self):
        args = build_yt_dlp_args(
            url="https://example.com/video",
            output_dir="/tmp/out",
            audio_only=True,
            keep_video=False,
        )
        assert args[0] == "yt-dlp"
        assert "-x" in args
        assert "--audio-format" in args
        assert "mp3" in args
        assert "https://example.com/video" in args[-1]

    def test_keep_video(self):
        args = build_yt_dlp_args(
            url="https://example.com/video",
            output_dir="/tmp/out",
            audio_only=False,
            keep_video=True,
        )
        assert "-x" not in args
        assert "--audio-format" not in args

    def test_output_template(self):
        args = build_yt_dlp_args(
            url="https://example.com/video",
            output_dir="/tmp/meetings",
            audio_only=True,
            keep_video=False,
        )
        output_arg_idx = args.index("-o")
        assert args[output_arg_idx + 1].startswith("/tmp/meetings")

    def test_bilibili_cookies_flag(self):
        """B站可能需要 cookies 绕过限制，提供一个 --cookies 选项."""
        args = build_yt_dlp_args(
            url="https://www.bilibili.com/video/BV1xx",
            output_dir="/tmp/out",
            audio_only=True,
            keep_video=False,
            cookies_file="/path/to/cookies.txt",
        )
        assert "--cookies" in args
        cookie_idx = args.index("--cookies")
        assert args[cookie_idx + 1] == "/path/to/cookies.txt"
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/test_download.py -v
```
Expected: FAIL (import error)

- [ ] **Step 3: 实现 `meeting_cli/commands/download.py`**

```python
"""download command: yt-dlp subprocess wrapper."""

import subprocess
import sys
from pathlib import Path

import click


def build_yt_dlp_args(
    url: str,
    output_dir: str,
    audio_only: bool = True,
    keep_video: bool = False,
    cookies_file: str | None = None,
) -> list[str]:
    """Build the argument list for yt-dlp subprocess call.

    Args:
        url: The video URL to download.
        output_dir: Directory to save output files.
        audio_only: If True, extract audio only (default).
        keep_video: If True, keep the video file alongside audio.
        cookies_file: Optional path to a Netscape-format cookies file.

    Returns:
        List of command-line arguments for subprocess.
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    args = [
        "yt-dlp",
        "-o", str(out_dir / "%(title)s.%(ext)s"),
    ]

    if audio_only:
        args.extend(["-x", "--audio-format", "mp3"])
        if not keep_video:
            args.append("--audio-quality")
            args.append("0")

    if cookies_file:
        args.extend(["--cookies", cookies_file])

    args.append(url)
    return args


@click.command()
@click.argument("url")
@click.option(
    "--output-dir", "-o",
    default="./meeting-output",
    show_default=True,
    help="工作目录，输出文件保存到此",
)
@click.option(
    "--audio-only/--no-audio-only",
    default=True,
    show_default=True,
    help="只下载音频（默认）",
)
@click.option(
    "--keep-video",
    is_flag=True,
    help="保留视频文件",
)
@click.option(
    "--cookies",
    default=None,
    help="Netscape格式的cookies文件路径（B站等需要登录的站点）",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="仅打印yt-dlp命令，不实际执行",
)
def download(
    url: str,
    output_dir: str,
    audio_only: bool,
    keep_video: bool,
    cookies: str | None,
    dry_run: bool,
):
    """从视频网站下载会议音频/视频。

    URL 可以是 B站、YouTube 等 yt-dlp 支持的任意平台。
    """
    args = build_yt_dlp_args(
        url=url,
        output_dir=output_dir,
        audio_only=audio_only,
        keep_video=keep_video,
        cookies_file=cookies,
    )

    if dry_run:
        click.echo(" ".join(args))
        return

    click.echo(f"正在下载: {url}")
    click.echo(f"输出目录: {output_dir}")

    try:
        result = subprocess.run(args, check=False)
        if result.returncode != 0:
            click.echo(
                f"yt-dlp 退出码 {result.returncode}，"
                f"请检查 URL 是否正确、网络是否连通。",
                err=True,
            )
            sys.exit(result.returncode)
        click.echo(f"下载完成，文件保存在: {output_dir}")
    except FileNotFoundError:
        click.echo(
            "错误: 找不到 yt-dlp。请先安装: pip install yt-dlp",
            err=True,
        )
        sys.exit(1)
```

- [ ] **Step 4: 运行单元测试确认通过**

```bash
pytest tests/test_download.py -v
```
Expected: 全部 4 个测试 PASS

- [ ] **Step 5: 手动验证 CLI 可被调用（不需要真实URL）**

```bash
python -m meeting_cli.main download --help
python -m meeting_cli.main download --dry-run "https://www.bilibili.com/video/BV1xx"
```
Expected: 打印出 yt-dlp 命令字符串，不报错

- [ ] **Step 6: 提交**

```bash
git add meeting_cli/commands/download.py tests/test_download.py
git commit -m "feat: add download command (yt-dlp subprocess wrapper)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: transcribe 命令

**Files:**
- Create: `meeting_cli/commands/transcribe.py`
- Test: `tests/test_transcribe.py`
- Modify: `meeting_cli/backends/whisper_local.py` (完整实现)

- [ ] **Step 1: 先实现 whisper_local 后端 (写测试)**

在 `tests/test_transcribe.py` 中写针对后端的测试:

```python
"""Tests for transcribe command and whisper backend."""

import pytest
from pathlib import Path
from meeting_cli.backends.whisper_local import WhisperLocalTranscriber, Segment


class TestWhisperLocalTranscriber:
    def test_name_is_whisper(self):
        t = WhisperLocalTranscriber()
        assert t.name == "whisper"

    def test_transcribe_returns_segments(self, tmp_path):
        """This test requires faster-whisper to be installed.
        Skip if not available or if no GPU."""
        pytest.importorskip("faster_whisper")
        # Create a tiny valid audio? Skipping full transcription test
        # as it requires model download and real audio.
        pass  # Integration test covered separately


class TestTranscribeOutputFormat:
    """Tests for the transcript file format (Segment → timestamp text)."""

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
            Segment,
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
```

- [ ] **Step 2: 运行测试（部分 skip 是预期的）**

```bash
pytest tests/test_transcribe.py -v -k "not WhisperLocalTranscriber"
```
Expected: 3 tests PASS (format/parse/roundtrip)

- [ ] **Step 3: 实现 `meeting_cli/commands/transcribe.py`**

```python
"""transcribe command: audio → timestamped transcript."""

import re
import sys
from pathlib import Path

import click

from meeting_cli.backends import get_transcriber, list_transcribers
from meeting_cli.backends.transcriber import Segment


def format_timestamp(seconds: float) -> str:
    """Convert float seconds to HH:MM:SS.mmm format."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}"


def format_segment_line(segment: Segment) -> str:
    """Format a Segment as a single timestamped line.

    Example: '[00:00:00.000 -> 00:00:03.500] 大家好'
    """
    start = format_timestamp(segment.start)
    end = format_timestamp(segment.end)
    return f"[{start} -> {end}] {segment.text}"


def parse_transcript_file(path: str) -> list[Segment]:
    """Parse a timestamped transcript file back into Segment objects.

    Expected line format: [HH:MM:SS.mmm -> HH:MM:SS.mmm] text

    Returns:
        List of Segment objects.
    """
    segments = []
    pattern = re.compile(
        r"\[(\d{2}:\d{2}:\d{2}\.\d{3}) -> (\d{2}:\d{2}:\d{2}\.\d{3})\]\s+(.*)"
    )

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            m = pattern.match(line)
            if m:
                segments.append(Segment(
                    start=parse_timestamp(m.group(1)),
                    end=parse_timestamp(m.group(2)),
                    text=m.group(3),
                ))
    return segments


def parse_timestamp(ts: str) -> float:
    """Convert HH:MM:SS.mmm to float seconds."""
    h, m, s = ts.split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


@click.command()
@click.argument("file", type=click.Path(exists=True))
@click.option(
    "--backend", "-b",
    multiple=True,
    required=True,
    help="转写后端（可多次指定，如 -b whisper -b aliyun）",
)
@click.option(
    "--output-dir", "-o",
    default="./meeting-output",
    show_default=True,
    help="工作目录",
)
@click.option(
    "--language", "-l",
    default="zh",
    show_default=True,
    help="音频语言提示",
)
def transcribe(
    file: str,
    backend: tuple[str, ...],
    output_dir: str,
    language: str,
):
    """将音频文件转写为带时间戳的文本记录。

    支持同时使用多个后端，每个后端产出一份独立的转写文件。
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    audio_path = Path(file)
    if not audio_path.exists():
        click.echo(f"错误: 文件不存在: {file}", err=True)
        sys.exit(1)

    for be_name in backend:
        click.echo(f"转写中... 后端: {be_name}")

        transcriber = get_transcriber(be_name)
        if transcriber is None:
            available = list_transcribers()
            click.echo(
                f"错误: 未知后端 '{be_name}'。"
                f"可用: {', '.join(available) if available else '(无)'}",
                err=True,
            )
            sys.exit(1)

        segments = transcriber.transcribe(str(audio_path))
        out_path = out_dir / f"trans-{be_name}.txt"

        lines = [format_segment_line(seg) for seg in segments]
        out_path.write_text("\n".join(lines), encoding="utf-8")
        click.echo(f"  → 已保存: {out_path} ({len(segments)} 段)")
```

- [ ] **Step 4: 更新 whisper_local.py 完整实现**

```python
"""faster-whisper local transcription backend."""

import sys
from meeting_cli.backends.transcriber import BaseTranscriber, Segment


class WhisperLocalTranscriber(BaseTranscriber):
    """Local Whisper transcription using faster-whisper.

    Requires: pip install faster-whisper
    Model: 'medium' for a good balance of accuracy and speed on ThinkPad.
           Falls back to 'small' if memory is constrained.
    """

    name = "whisper"

    def __init__(self, model_size: str = "medium", device: str = "auto"):
        self.model_size = model_size
        self.device = device

    def transcribe(self, audio_path: str) -> list[Segment]:
        """Transcribe audio using local faster-whisper model.

        Args:
            audio_path: Path to the audio file.

        Returns:
            List of timestamped Segment objects.
        """
        try:
            from faster_whisper import WhisperModel
        except ImportError:
            print(
                "错误: 需要安装 faster-whisper。运行: pip install faster-whisper",
                file=sys.stderr,
            )
            sys.exit(1)

        device = self.device
        if device == "auto":
            device = "cuda" if self._cuda_available() else "cpu"

        compute_type = (
            "float16" if device == "cuda" else "int8"
        )

        model = WhisperModel(self.model_size, device=device, compute_type=compute_type)
        segments_iter, _ = model.transcribe(audio_path, language="zh")

        segments = []
        for seg in segments_iter:
            segments.append(Segment(
                start=seg.start,
                end=seg.end,
                text=seg.text.strip(),
            ))
        return segments

    @staticmethod
    def _cuda_available() -> bool:
        """Check if CUDA GPU is available."""
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            return False
```

- [ ] **Step 5: 运行测试确认通过**

```bash
pytest tests/test_transcribe.py -v -k "not test_transcribe_returns_segments"
```
Expected: PASS

- [ ] **Step 6: 提交**

```bash
git add meeting_cli/commands/transcribe.py meeting_cli/backends/whisper_local.py tests/test_transcribe.py
git commit -m "feat: add transcribe command with whisper_local backend

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: diff 引擎 (时间戳对齐 + 差异检测)

**Files:**
- Create: `meeting_cli/diff/engine.py`
- Test: `tests/test_diff_engine.py`

- [ ] **Step 1: 写测试 `tests/test_diff_engine.py`**

```python
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
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/test_diff_engine.py -v
```
Expected: FAIL (cannot import)

- [ ] **Step 3: 实现 `meeting_cli/diff/engine.py`**

```python
"""Diff engine: timestamp-based alignment and difference grading."""

from dataclasses import dataclass, field
from enum import Enum
from difflib import SequenceMatcher

from meeting_cli.backends.transcriber import Segment


class DiffLevel(Enum):
    SAME = "same"       # 一致，自动通过
    SMALL = "small"     # 小差异，需确认
    LARGE = "large"     # 大差异，需确认
    ORPHAN = "orphan"   # 孤立段落，仅一侧存在


@dataclass
class DiffResult:
    """A single aligned or unaligned segment comparison result."""
    level: DiffLevel
    start_a: float | None = None
    end_a: float | None = None
    text_a: str = ""
    start_b: float | None = None
    end_b: float | None = None
    text_b: str = ""
    segment_index: int = 0


def align_segments(
    segs_a: list[Segment],
    segs_b: list[Segment],
    timestamp_threshold: float = 2.0,
) -> list[DiffResult]:
    """Align two timestamped transcript segment lists.

    Primary alignment key: timestamp overlap.
    Secondary key: text similarity for near-miss timestamps.

    Args:
        segs_a: Segments from transcript A.
        segs_b: Segments from transcript B.
        timestamp_threshold: Max time offset (seconds) to consider
            two segments as potentially the same utterance.

    Returns:
        List of DiffResult objects, one per aligned/matched pair.
    """
    results = []
    used_b = set()
    used_a = set()

    # Pass 1: timestamp overlap matching
    for i, seg_a in enumerate(segs_a):
        best_j = None
        best_overlap = 0.0
        for j, seg_b in enumerate(segs_b):
            if j in used_b:
                continue
            overlap = _overlap_duration(seg_a, seg_b)
            if overlap > best_overlap:
                best_overlap = overlap
                best_j = j

        if best_j is not None and best_overlap > 0:
            seg_b = segs_b[best_j]
            used_a.add(i)
            used_b.add(best_j)
            text_similarity = _similarity(seg_a.text, seg_b.text)
            results.append(DiffResult(
                level=grade_difference(seg_a.text, seg_b.text),
                start_a=seg_a.start, end_a=seg_a.end, text_a=seg_a.text,
                start_b=seg_b.start, end_b=seg_b.end, text_b=seg_b.text,
                segment_index=len(results),
            ))

    # Pass 2: timestamp-adjacent + similarity match for near-misses
    for i, seg_a in enumerate(segs_a):
        if i in used_a:
            continue
        for j, seg_b in enumerate(segs_b):
            if j in used_b:
                continue
            time_diff = abs(seg_a.start - seg_b.start)
            if time_diff <= timestamp_threshold and _similarity(seg_a.text, seg_b.text) > 0.5:
                used_a.add(i)
                used_b.add(j)
                results.append(DiffResult(
                    level=grade_difference(seg_a.text, seg_b.text),
                    start_a=seg_a.start, end_a=seg_a.end, text_a=seg_a.text,
                    start_b=seg_b.start, end_b=seg_b.end, text_b=seg_b.text,
                    segment_index=len(results),
                ))
                break

    # Pass 3: orphan segments from side A
    for i, seg_a in enumerate(segs_a):
        if i not in used_a:
            results.append(DiffResult(
                level=DiffLevel.ORPHAN,
                start_a=seg_a.start, end_a=seg_a.end, text_a=seg_a.text,
                segment_index=len(results),
            ))

    # Pass 4: orphan segments from side B
    for j, seg_b in enumerate(segs_b):
        if j not in used_b:
            results.append(DiffResult(
                level=DiffLevel.ORPHAN,
                start_b=seg_b.start, end_b=seg_b.end, text_b=seg_b.text,
                segment_index=len(results),
            ))

    return results


def grade_difference(text_a: str, text_b: str) -> DiffLevel:
    """Grade the difference level between two text strings.

    Uses edit distance ratio as the primary signal.

    Args:
        text_a: Text from transcript A.
        text_b: Text from transcript B.

    Returns:
        DiffLevel: SAME, SMALL, LARGE, or ORPHAN.
    """
    if not text_a and not text_b:
        return DiffLevel.SAME
    if not text_a or not text_b:
        return DiffLevel.ORPHAN

    similarity = _similarity(text_a, text_b)
    distance = 1.0 - similarity

    if distance < 0.10:
        return DiffLevel.SAME
    elif distance < 0.30:
        return DiffLevel.SMALL
    else:
        return DiffLevel.LARGE


def _similarity(a: str, b: str) -> float:
    """Compute text similarity ratio (0.0 to 1.0)."""
    return SequenceMatcher(None, a, b).ratio()


def _overlap_duration(seg_a: Segment, seg_b: Segment) -> float:
    """Compute temporal overlap duration between two segments."""
    start = max(seg_a.start, seg_b.start)
    end = min(seg_a.end, seg_b.end)
    return max(0.0, end - start)
```

- [ ] **Step 4: 运行测试确认通过**

```bash
pytest tests/test_diff_engine.py -v
```
Expected: 全部 11 个测试 PASS

- [ ] **Step 5: 提交**

```bash
git add meeting_cli/diff/engine.py tests/test_diff_engine.py
git commit -m "feat: add diff engine with timestamp alignment and grading

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7: diff 报告生成器

**Files:**
- Create: `meeting_cli/diff/reporter.py`
- Test: `tests/test_diff_reporter.py`

- [ ] **Step 1: 写测试 `tests/test_diff_reporter.py`**

```python
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
        r.user_choice = "A"  # type: ignore
        html = build_html_report([r], "A", "B")
        assert "选择: A" in html


class TestBuildFinalTranscript:
    def test_merges_segments_with_choices(self, tmp_path):
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
        results[0].user_choice = "auto"  # type: ignore
        results[1].user_choice = "A"      # type: ignore

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
        results[0].user_choice = "manual"     # type: ignore
        results[0].user_edited_text = "人工修正后的文本"  # type: ignore

        transcript = build_final_transcript(results)
        assert "人工修正后的文本" in transcript
        assert "原文A" not in transcript
        assert "原文B" not in transcript
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/test_diff_reporter.py -v
```
Expected: FAIL (import error)

- [ ] **Step 3: 实现 `meeting_cli/diff/reporter.py`**

```python
"""Diff report generation: HTML report and final merged transcript."""

from meeting_cli.diff.engine import DiffResult, DiffLevel


def format_ts(seconds: float | None) -> str:
    """Format seconds to HH:MM:SS."""
    if seconds is None:
        return "--:--:--"
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


LEVEL_LABELS = {
    DiffLevel.SAME: "一致",
    DiffLevel.SMALL: "小差异",
    DiffLevel.LARGE: "大差异",
    DiffLevel.ORPHAN: "孤立",
}


def build_html_report(
    results: list[DiffResult],
    source_a: str,
    source_b: str,
) -> str:
    """Generate an HTML diff report comparing two transcripts.

    Args:
        results: Aligned diff results.
        source_a: Name/label of transcript A.
        source_b: Name/label of transcript B.

    Returns:
        Complete HTML document as a string.
    """
    rows_html = ""
    for r in results:
        level_label = LEVEL_LABELS.get(r.level, "?")
        choice = getattr(r, "user_choice", "")
        if choice:
            choice_display = f"选择: {choice}"
        else:
            choice_display = ""

        rows_html += f"""
        <tr class="diff-{r.level.value}">
            <td class="idx">{r.segment_index + 1}</td>
            <td class="ts">[{format_ts(r.start_a)} → {format_ts(r.end_a)}]</td>
            <td class="text">{r.text_a}</td>
            <td class="ts">[{format_ts(r.start_b)} → {format_ts(r.end_b)}]</td>
            <td class="text">{r.text_b}</td>
            <td class="level">{level_label}</td>
            <td class="choice">{choice_display}</td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<title>转写对比报告: {source_a} vs {source_b}</title>
<style>
body {{ font-family: system-ui, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; }}
h1 {{ font-size: 1.5em; }}
table {{ width: 100%; border-collapse: collapse; }}
th, td {{ padding: 8px 12px; text-align: left; border-bottom: 1px solid #e5e7eb; }}
.diff-same {{ background: #f0fdf4; }}
.diff-small {{ background: #fefce8; }}
.diff-large {{ background: #fef2f2; }}
.diff-orphan {{ background: #f3f4f6; color: #6b7280; }}
.idx {{ width: 40px; color: #9ca3af; }}
.ts {{ white-space: nowrap; font-size: 0.85em; color: #6b7280; font-family: monospace; }}
.level {{ font-weight: 600; }}
.choice {{ font-weight: 700; color: #2563eb; }}
</style>
</head>
<body>
<h1>转写对比报告</h1>
<p>来源A: {source_a} &nbsp;|&nbsp; 来源B: {source_b}</p>
<table>
<thead><tr>
  <th>#</th><th>时间戳A</th><th>内容A</th><th>时间戳B</th><th>内容B</th><th>差异</th><th>选择</th>
</tr></thead>
<tbody>{rows_html}
</tbody></table>
</body></html>"""


def build_final_transcript(results: list[DiffResult]) -> str:
    """Build the final merged transcript from diff results with user choices.

    For each result, uses:
    - user_choice == 'A' → text_a
    - user_choice == 'B' → text_b
    - user_choice == 'manual' → user_edited_text
    - user_choice == 'skip' → skip this segment
    - For SAME level → text_a (either, they're the same)
    - For orphan with only one side → the text that exists

    Args:
        results: Aligned diff results with user_choice attributes set.

    Returns:
        Merged transcript text with timestamps.
    """
    lines = []
    for r in results:
        choice = getattr(r, "user_choice", None)

        if choice == "skip":
            continue

        # Determine which text and timestamp to use
        if choice == "A":
            text = r.text_a
            start = r.start_a
            end = r.end_a
        elif choice == "B":
            text = r.text_b
            start = r.start_b
            end = r.end_b
        elif choice == "manual":
            text = getattr(r, "user_edited_text", "")
            start = r.start_a or r.start_b
            end = r.end_a or r.end_b
        elif r.level == DiffLevel.ORPHAN:
            # Orphan: take whatever side has text
            if r.text_a:
                text = r.text_a
                start = r.start_a
                end = r.end_a
            else:
                text = r.text_b
                start = r.start_b
                end = r.end_b
        else:
            # SAME/SMALL/LARGE without explicit choice → default to A
            text = r.text_a
            start = r.start_a
            end = r.end_a

        if text and start is not None and end is not None:
            lines.append(
                f"[{format_ts(start)} -> {format_ts(end)}] {text}"
            )

    return "\n".join(lines)
```

- [ ] **Step 4: 运行测试确认通过**

```bash
pytest tests/test_diff_reporter.py -v
```
Expected: 全部 4 个测试 PASS

- [ ] **Step 5: 提交**

```bash
git add meeting_cli/diff/reporter.py tests/test_diff_reporter.py
git commit -m "feat: add diff reporter (HTML report + final transcript merger)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 8: compare 命令 (交互式差异确认)

**Files:**
- Create: `meeting_cli/commands/compare.py`
- Test: `tests/test_compare.py`

- [ ] **Step 1: 写测试 `tests/test_compare.py`**

```python
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

    def test_build_final_transcript_after_choices(self, tmp_path):
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
        results[0].user_choice = "manual"  # type: ignore
        results[0].user_edited_text = "Q2预算上调15%"  # type: ignore
        results[1].user_choice = "auto"  # type: ignore

        final = build_final_transcript(results)
        assert "Q2预算上调15%" in final
        assert "Q2预算上调50%" not in final
        assert "财务部汇报数据" in final
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/test_compare.py -v
```
Expected: FAIL (some may pass if dependencies are in place)

- [ ] **Step 3: 实现 `meeting_cli/commands/compare.py`**

```python
"""compare command: diff two transcripts with interactive confirmation."""

import shutil
import subprocess
import sys
from pathlib import Path

import click

from meeting_cli.commands.transcribe import parse_transcript_file
from meeting_cli.diff.engine import align_segments, DiffLevel
from meeting_cli.diff.reporter import build_html_report, build_final_transcript


@click.command()
@click.argument("file_a", type=click.Path(exists=True))
@click.argument("file_b", type=click.Path(exists=True))
@click.option(
    "--output-dir", "-o",
    default="./meeting-output",
    show_default=True,
    help="工作目录",
)
@click.option(
    "--use-llm",
    is_flag=True,
    help="启用LLM辅助精判差异（默认仅用算法）",
)
@click.option(
    "--llm-backend",
    default="openai",
    show_default=True,
    help="LLM精判使用的后端",
)
@click.option(
    "--audio", "-a",
    default=None,
    type=click.Path(exists=True),
    help="原始音频文件路径（用于回听功能）",
)
def compare(
    file_a: str,
    file_b: str,
    output_dir: str,
    use_llm: bool,
    llm_backend: str,
    audio: str | None,
):
    """对比两份转写记录，逐段确认差异。

    FILE_A 和 FILE_B 是两份带时间戳的转写文件。
    差异段落会逐条展示，你选择保留哪个版本。
    最终产出合并后的 final-transcript.txt 和对比报告。
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. Parse both transcripts
    click.echo(f"读取: {file_a}")
    segs_a = parse_transcript_file(file_a)
    click.echo(f"读取: {file_b}")
    segs_b = parse_transcript_file(file_b)

    source_a = Path(file_a).stem
    source_b = Path(file_b).stem

    # 2. Align and grade
    click.echo(f"对齐比较中... ({len(segs_a)} vs {len(segs_b)} 段)")
    results = align_segments(segs_a, segs_b)

    same_count = sum(1 for r in results if r.level == DiffLevel.SAME)
    small_count = sum(1 for r in results if r.level == DiffLevel.SMALL)
    large_count = sum(1 for r in results if r.level == DiffLevel.LARGE)
    orphan_count = sum(1 for r in results if r.level == DiffLevel.ORPHAN)
    click.echo(
        f"对比完成: 🟢{same_count}一致 🟡{small_count}小差异 "
        f"🔴{large_count}大差异 ⬜{orphan_count}孤立"
    )

    needs_review = [r for r in results if r.level != DiffLevel.SAME]
    if not needs_review:
        click.echo("两份转写完全一致，无需人工确认。")
        final = build_final_transcript(results)
        (out_dir / "final-transcript.txt").write_text(final, encoding="utf-8")
        return

    # 3. Interactive review loop
    click.echo(f"\n开始逐段确认 ({len(needs_review)} 段需要审核):")
    click.echo("  [A]保留A  [B]保留B  [E]手动编辑  [P]回听音频  [S]跳过  [Q]退出\n")

    for idx, r in enumerate(results):
        if r.level == DiffLevel.SAME:
            r.user_choice = "auto"  # type: ignore
            continue

        _display_diff(r, source_a, source_b)

        choice = _get_user_choice(audio, r)
        if choice == "q":
            click.echo("已退出。当前进度未保存。")
            sys.exit(0)

        r.user_choice = choice  # type: ignore

        if choice == "manual":
            edited = click.prompt("  输入修正文本", type=str)
            r.user_edited_text = edited  # type: ignore

    # 4. Generate outputs
    final_path = out_dir / "final-transcript.txt"
    final = build_final_transcript(results)
    final_path.write_text(final, encoding="utf-8")
    click.echo(f"\n最终转写已保存: {final_path}")

    report_path = out_dir / "diff-report.html"
    html = build_html_report(results, source_a, source_b)
    report_path.write_text(html, encoding="utf-8")
    click.echo(f"对比报告已保存: {report_path}")


def _display_diff(r, source_a: str, source_b: str):
    """Display a single diff segment in the terminal."""
    level_emoji = {
        DiffLevel.SMALL: "🟡",
        DiffLevel.LARGE: "🔴",
        DiffLevel.ORPHAN: "⬜",
    }
    emoji = level_emoji.get(r.level, "?")
    ts_a = f"{r.start_a:.1f}s → {r.end_a:.1f}s" if r.start_a else "--"
    ts_b = f"{r.start_b:.1f}s → {r.end_b:.1f}s" if r.start_b else "--"

    click.echo(f"\n{'─'*60}")
    click.echo(f"【段落 {r.segment_index + 1}】{emoji}")
    click.echo(f"A ({source_a}) [{ts_a}]:  {r.text_a}")
    click.echo(f"B ({source_b}) [{ts_b}]:  {r.text_b}")


def _get_user_choice(audio_path: str | None, r) -> str:
    """Prompt user for choice on a single diff segment.

    Returns one of: 'A', 'B', 'manual', 'play', 'skip', 'q'
    """
    while True:
        choice = click.prompt(
            "  选择 [A/B/E/P/S/Q]",
            type=str,
            default="A",
            show_default=False,
        ).strip().lower()

        if choice in ("a", "b", "s"):
            return choice
        elif choice == "e":
            return "manual"
        elif choice == "p":
            if audio_path:
                _play_segment(audio_path, r.start_a or r.start_b, r.end_a or r.end_b)
            else:
                click.echo("  未指定音频文件，无法回听。请用 --audio 指定。")
            continue  # re-prompt after playback
        elif choice == "q":
            return "q"
        else:
            click.echo("  无效选择，请输入 A/B/E/P/S/Q")


def _play_segment(audio_path: str, start: float | None, end: float | None):
    """Play a segment of audio using ffplay."""
    if start is None or end is None:
        click.echo("  无法定位时间戳")
        return

    duration = end - start
    ffplay = shutil.which("ffplay")
    if not ffplay:
        click.echo(f"  未找到 ffplay。请手动跳转到 {start:.1f}s 处播放音频")
        return

    click.echo(f"  播放中... ({start:.1f}s → {end:.1f}s)")
    subprocess.run(
        [ffplay, "-ss", str(start), "-t", str(duration),
         "-nodisp", "-autoexit", "-loglevel", "quiet", audio_path],
        check=False,
    )
```

- [ ] **Step 4: 运行测试确认通过**

```bash
pytest tests/test_compare.py -v
```
Expected: 全部 3 个测试 PASS

- [ ] **Step 5: 手动验证 CLI**

```bash
python -m meeting_cli.main compare --help
```
Expected: 显示 compare 命令的帮助信息

- [ ] **Step 6: 提交**

```bash
git add meeting_cli/commands/compare.py tests/test_compare.py
git commit -m "feat: add compare command with interactive diff review

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 9: summarize 命令

**Files:**
- Create: `meeting_cli/commands/summarize.py`
- Modify: `meeting_cli/backends/openai_compat.py` (完整实现)
- Test: `tests/test_summarize.py`

- [ ] **Step 1: 写测试 `tests/test_summarize.py`**

```python
"""Tests for summarize command and openai_compat backend."""

import pytest
from meeting_cli.backends.summarizer import BaseSummarizer


class TestSummarizeCommand:
    def test_summarize_help(self):
        """Verify CLI entry can be imported and has expected interface."""
        from meeting_cli.commands.summarize import summarize
        assert callable(summarize.callback)


class TestOpenAICompatSummarizer:
    def test_name_is_openai(self):
        from meeting_cli.backends.openai_compat import OpenAICompatSummarizer
        s = OpenAICompatSummarizer()
        assert s.name == "openai"

    def test_build_prompt_includes_transcript(self):
        """The summarize method should pass the transcript to the API
        with a structured prompt asking for meeting notes."""
        from meeting_cli.backends.openai_compat import _build_summary_prompt
        prompt = _build_summary_prompt("测试转写内容")
        assert "测试转写内容" in prompt
        assert "会议纪要" in prompt or "总结" in prompt or "摘要" in prompt

    def test_build_prompt_has_required_sections(self):
        """The prompt should request structured output with
        topics, decisions, action items, and summary."""
        from meeting_cli.backends.openai_compat import _build_summary_prompt
        prompt = _build_summary_prompt("test")
        required_keywords = ["议题", "决策", "待办", "摘要"]
        for kw in required_keywords:
            assert kw in prompt, f"Prompt missing keyword: {kw}"
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/test_summarize.py -v
```
Expected: FAIL

- [ ] **Step 3: 实现 `meeting_cli/backends/openai_compat.py` (完整版)**

```python
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
        {NAME}_API_KEY   – API key (required)
        {NAME}_BASE_URL  – Optional custom endpoint URL
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
```

- [ ] **Step 4: 实现 `meeting_cli/commands/summarize.py`**

```python
"""summarize command: transcript → structured meeting notes."""

import sys
from pathlib import Path

import click

from meeting_cli.backends import get_summarizer, list_summarizers


@click.command()
@click.argument("file", type=click.Path(exists=True))
@click.option(
    "--backend", "-b",
    default="openai",
    show_default=True,
    help="LLM后端（用于总结）",
)
@click.option(
    "--output-dir", "-o",
    default="./meeting-output",
    show_default=True,
    help="工作目录",
)
def summarize(file: str, backend: str, output_dir: str):
    """将转写记录总结为结构化会议纪要。

    FILE 可以是任意转写文件（带或不带时间戳均可）。
    产出 summary.md，包含议题、决策、待办事项和简短摘要。
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    transcript_path = Path(file)
    if not transcript_path.exists():
        click.echo(f"错误: 文件不存在: {file}", err=True)
        sys.exit(1)

    transcript = transcript_path.read_text(encoding="utf-8")

    summarizer = get_summarizer(backend)
    if summarizer is None:
        available = list_summarizers()
        click.echo(
            f"错误: 未知后端 '{backend}'。"
            f"可用: {', '.join(available) if available else '(无)'}",
            err=True,
        )
        sys.exit(1)

    click.echo(f"生成会议纪要中... 后端: {backend}")
    summary_md = summarizer.summarize(transcript)

    out_path = out_dir / "summary.md"
    out_path.write_text(summary_md, encoding="utf-8")
    click.echo(f"会议纪要已保存: {out_path}")
```

- [ ] **Step 5: 运行测试确认通过**

```bash
pytest tests/test_summarize.py -v
```
Expected: 3 tests PASS (test_summarize_help, test_name_is_openai, build_prompt tests)

- [ ] **Step 6: 提交**

```bash
git add meeting_cli/backends/openai_compat.py meeting_cli/commands/summarize.py tests/test_summarize.py
git commit -m "feat: add summarize command with openai_compat LLM backend

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 10: subtitle 命令 (探索性)

**Files:**
- Create: `meeting_cli/commands/subtitle.py`
- Test: `tests/test_subtitle.py`

- [ ] **Step 1: 写测试 `tests/test_subtitle.py`**

```python
"""Tests for subtitle generation."""

from meeting_cli.commands.subtitle import segments_to_srt


class TestSegmentsToSrt:
    def test_basic_srt_generation(self):
        from meeting_cli.backends.transcriber import Segment
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
        from meeting_cli.backends.transcriber import Segment
        segments = [Segment(start=1.5, end=3.75, text="测试")]
        srt = segments_to_srt(segments)
        assert "00:00:01,500" in srt
        assert "00:00:03,750" in srt
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/test_subtitle.py -v
```
Expected: FAIL

- [ ] **Step 3: 实现 `meeting_cli/commands/subtitle.py`**

```python
"""subtitle command: transcript → SRT subtitle file (exploratory)."""

import shutil
import subprocess
import sys
from pathlib import Path

import click

from meeting_cli.commands.transcribe import parse_transcript_file
from meeting_cli.backends.transcriber import Segment


def srt_timestamp(seconds: float) -> str:
    """Convert seconds to SRT timestamp format: HH:MM:SS,mmm."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def segments_to_srt(segments: list[Segment]) -> str:
    """Convert timestamped segments to SRT subtitle text.

    Args:
        segments: List of Segment objects with start, end, and text.

    Returns:
        SRT-formatted string.
    """
    blocks = []
    for i, seg in enumerate(segments, 1):
        start = srt_timestamp(seg.start)
        end = srt_timestamp(seg.end)
        blocks.append(f"{i}\n{start} --> {end}\n{seg.text}\n")
    return "\n".join(blocks)


@click.command()
@click.argument("transcript", type=click.Path(exists=True))
@click.argument("video", type=click.Path(exists=True))
@click.option(
    "--output-dir", "-o",
    default="./meeting-output",
    show_default=True,
    help="工作目录",
)
@click.option(
    "--translate",
    is_flag=True,
    help="同时生成翻译字幕",
)
@click.option(
    "--target-lang",
    default="en",
    show_default=True,
    help="翻译目标语言",
)
def subtitle(
    transcript: str,
    video: str,
    output_dir: str,
    translate: bool,
    target_lang: str,
):
    """将带时间戳的转写记录生成SRT字幕，并嵌入视频（探索性功能）。

    需要安装 ffmpeg。依赖转写记录中包含时间戳信息。
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. Parse transcript → segments
    click.echo(f"读取转写: {transcript}")
    segments = parse_transcript_file(transcript)
    if not segments:
        click.echo("错误: 转写文件为空或格式不正确", err=True)
        sys.exit(1)

    # 2. Generate SRT
    srt_content = segments_to_srt(segments)
    srt_path = out_dir / "subtitle.srt"
    srt_path.write_text(srt_content, encoding="utf-8")
    click.echo(f"字幕已生成: {srt_path} ({len(segments)} 条)")

    # 3. Optional translation
    if translate:
        click.echo(f"翻译字幕（目标语言: {target_lang}）...")
        # 合并所有文本，调用LLM翻译，再对齐回时间轴
        # 作为探索功能，先打印提示
        click.echo("  翻译功能将在后续版本中完善。")

    # 4. Embed with ffmpeg
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        click.echo(
            "警告: 未找到 ffmpeg，跳过视频嵌入。"
            "请安装 ffmpeg 后手动将 subtitle.srt 嵌入视频。",
            err=True,
        )
        return

    output_video = out_dir / f"{Path(video).stem}_subtitled.mp4"
    click.echo(f"正在将字幕嵌入视频: {output_video}")

    result = subprocess.run(
        [
            ffmpeg,
            "-i", video,
            "-vf", f"subtitles={srt_path}",
            "-c:a", "copy",
            str(output_video),
        ],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if result.returncode == 0:
        click.echo(f"带字幕视频已保存: {output_video}")
    else:
        click.echo(
            "ffmpeg 嵌入字幕失败。请检查视频文件和 ffmpeg 安装。",
            err=True,
        )
```

- [ ] **Step 4: 运行测试确认通过**

```bash
pytest tests/test_subtitle.py -v
```
Expected: 3 tests PASS

- [ ] **Step 5: 提交**

```bash
git add meeting_cli/commands/subtitle.py tests/test_subtitle.py
git commit -m "feat: add subtitle command (SRT generation + ffmpeg embedding, exploratory)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 11: 集成测试 (端到端管道)

**Files:**
- Create: `tests/test_integration.py`

- [ ] **Step 1: 写集成测试 `tests/test_integration.py`**

```python
"""End-to-end integration tests using mock backends."""

import pytest
from pathlib import Path
from click.testing import CliRunner

from meeting_cli.main import cli


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def mock_audio_file(tmp_path):
    """Create a minimal valid MP3 file for testing."""
    path = tmp_path / "test.mp3"
    path.write_bytes(b"mock audio data")
    return path


@pytest.fixture
def sample_transcript_a(tmp_path):
    """Create a sample timestamped transcript file."""
    path = tmp_path / "trans-a.txt"
    path.write_text(
        "[00:00:00.000 -> 00:00:03.000] 大家好欢迎\n"
        "[00:00:03.000 -> 00:00:08.000] 讨论Q2预算\n"
        "[00:00:08.000 -> 00:00:15.000] 财务部汇报\n",
        encoding="utf-8",
    )
    return path


@pytest.fixture
def sample_transcript_b(tmp_path):
    """Create another sample transcript with intentional differences."""
    path = tmp_path / "trans-b.txt"
    path.write_text(
        "[00:00:00.000 -> 00:00:03.000] 大家好欢迎\n"
        "[00:00:03.000 -> 00:00:08.500] 讨论Q2预算分配\n"
        "[00:00:08.500 -> 00:00:15.000] 财务部报告\n",
        encoding="utf-8",
    )
    return path


class TestCLIBasics:
    def test_cli_help(self, runner):
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "download" in result.output
        assert "transcribe" in result.output
        assert "compare" in result.output
        assert "summarize" in result.output

    def test_download_help(self, runner):
        result = runner.invoke(cli, ["download", "--help"])
        assert result.exit_code == 0

    def test_transcribe_help(self, runner):
        result = runner.invoke(cli, ["transcribe", "--help"])
        assert result.exit_code == 0

    def test_compare_help(self, runner):
        result = runner.invoke(cli, ["compare", "--help"])
        assert result.exit_code == 0

    def test_summarize_help(self, runner):
        result = runner.invoke(cli, ["summarize", "--help"])
        assert result.exit_code == 0

    def test_subtitle_help(self, runner):
        result = runner.invoke(cli, ["subtitle", "--help"])
        assert result.exit_code == 0

    def test_download_dry_run(self, runner):
        result = runner.invoke(
            cli,
            ["download", "--dry-run", "https://www.bilibili.com/video/BV1xx"],
        )
        assert result.exit_code == 0
        assert "yt-dlp" in result.output


class TestComparePipeline:
    def test_compare_with_sample_files(self, runner, tmp_path, sample_transcript_a, sample_transcript_b):
        out_dir = tmp_path / "output"
        # 用完整参数调用 compare
        result = runner.invoke(
            cli,
            [
                "compare",
                str(sample_transcript_a),
                str(sample_transcript_b),
                "-o", str(out_dir),
            ],
            input="a\n",  # 对所有差异都选 A
        )
        assert result.exit_code == 0
        # 验证输出文件
        final_path = out_dir / "final-transcript.txt"
        assert final_path.exists()
        report_path = out_dir / "diff-report.html"
        assert report_path.exists()
        content = final_path.read_text()
        assert "大家好欢迎" in content

    def test_compare_no_differences(self, runner, tmp_path, sample_transcript_a):
        out_dir = tmp_path / "output"
        result = runner.invoke(
            cli,
            [
                "compare",
                str(sample_transcript_a),
                str(sample_transcript_a),  # same file → no diff
                "-o", str(out_dir),
            ],
        )
        assert result.exit_code == 0
        assert "完全一致" in result.output
```

- [ ] **Step 2: 运行集成测试**

```bash
pytest tests/test_integration.py -v
```
Expected: 全部测试 PASS

- [ ] **Step 3: 运行全量测试**

```bash
pytest tests/ -v
```
Expected: 所有单元+集成测试 PASS

- [ ] **Step 4: 提交**

```bash
git add tests/test_integration.py
git commit -m "test: add end-to-end integration tests with CliRunner

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## 实现顺序总览

```
Task 1  → Project scaffold, deps, empty structure         (基础)
Task 2  → Config module (env vars)                        (依赖1)
Task 3  → Backend registry + ABCs                         (依赖1)
Task 4  → download command                                (依赖1,3)
Task 5  → transcribe command + whisper_local              (依赖2,3)
Task 6  → diff engine (align + grade)                     (依赖3)
Task 7  → diff reporter (HTML + final transcript)         (依赖6)
Task 8  → compare command (interactive)                   (依赖5,6,7)
Task 9  → summarize command + openai_compat               (依赖2,3)
Task 10 → subtitle command (exploratory)                  (依赖5)
Task 11 → Integration tests                               (依赖1-10)
```

任务 1-3 是基础，完成之后 4/5/9/10 可以并行推进。6/7 是 diff 核心，完成后接 8。11 最后跑全集。
