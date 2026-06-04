"""pytest fixtures for meeting-cli."""

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
