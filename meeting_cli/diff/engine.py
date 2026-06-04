"""Diff engine: timestamp-based alignment and difference grading."""

from dataclasses import dataclass, field
from enum import Enum
from difflib import SequenceMatcher

from meeting_cli.backends.transcriber import Segment


class DiffLevel(Enum):
    SAME = "same"  # 一致，自动通过
    SMALL = "small"  # 小差异，需确认
    LARGE = "large"  # 大差异，需确认
    ORPHAN = "orphan"  # 孤立段落，仅一侧存在


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
    results: list[DiffResult] = []
    used_b: set[int] = set()
    used_a: set[int] = set()

    # Pass 1: timestamp overlap matching
    for i, seg_a in enumerate(segs_a):
        best_j: int | None = None
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
            results.append(DiffResult(
                level=grade_difference(seg_a.text, seg_b.text),
                start_a=seg_a.start,
                end_a=seg_a.end,
                text_a=seg_a.text,
                start_b=seg_b.start,
                end_b=seg_b.end,
                text_b=seg_b.text,
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
                    start_a=seg_a.start,
                    end_a=seg_a.end,
                    text_a=seg_a.text,
                    start_b=seg_b.start,
                    end_b=seg_b.end,
                    text_b=seg_b.text,
                    segment_index=len(results),
                ))
                break

    # Pass 3: orphan segments from side A
    for i, seg_a in enumerate(segs_a):
        if i not in used_a:
            results.append(DiffResult(
                level=DiffLevel.ORPHAN,
                start_a=seg_a.start,
                end_a=seg_a.end,
                text_a=seg_a.text,
                segment_index=len(results),
            ))

    # Pass 4: orphan segments from side B
    for j, seg_b in enumerate(segs_b):
        if j not in used_b:
            results.append(DiffResult(
                level=DiffLevel.ORPHAN,
                start_b=seg_b.start,
                end_b=seg_b.end,
                text_b=seg_b.text,
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

    edit_dist = _edit_distance(text_a, text_b)
    max_len = max(len(text_a), len(text_b))
    if max_len == 0:
        return DiffLevel.SAME
    distance = edit_dist / max_len

    if distance < 0.05:
        return DiffLevel.SAME
    elif distance < 0.14:
        return DiffLevel.SMALL
    else:
        return DiffLevel.LARGE


def _similarity(a: str, b: str) -> float:
    """Compute text similarity ratio (0.0 to 1.0)."""
    return SequenceMatcher(None, a, b).ratio()


def _edit_distance(a: str, b: str) -> int:
    """Compute character-level edit distance via SequenceMatcher opcodes."""
    matcher = SequenceMatcher(None, a, b)
    distance = 0
    for tag, a1, a2, b1, b2 in matcher.get_opcodes():
        if tag == "replace":
            distance += max(a2 - a1, b2 - b1)
        elif tag == "delete":
            distance += a2 - a1
        elif tag == "insert":
            distance += b2 - b1
    return distance


def _overlap_duration(seg_a: Segment, seg_b: Segment) -> float:
    """Compute temporal overlap duration between two segments."""
    start = max(seg_a.start, seg_b.start)
    end = min(seg_a.end, seg_b.end)
    return max(0.0, end - start)
