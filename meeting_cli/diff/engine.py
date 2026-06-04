"""Diff engine: text-content-based alignment and difference grading."""

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
) -> list[DiffResult]:
    """Align two transcript segment lists by text content.

    Instead of relying on timestamps (which differ between models),
    this concatentes all text from each side and uses
    SequenceMatcher to find matching / differing blocks,
    then maps those blocks back to the original segments.

    Args:
        segs_a: Segments from transcript A.
        segs_b: Segments from transcript B.

    Returns:
        List of DiffResult objects.
    """
    # 1. Build full texts and position-to-segment maps
    full_a, a_spans = _build_text_and_spans(segs_a)
    full_b, b_spans = _build_text_and_spans(segs_b)

    # 2. Run SequenceMatcher on full texts
    matcher = SequenceMatcher(None, full_a, full_b)
    opcodes = matcher.get_opcodes()

    # 3. Create raw DiffResults from opcodes
    raw_results: list[DiffResult] = []

    for tag, a1, a2, b1, b2 in opcodes:
        seg_indices_a = _spans_in_range(a_spans, a1, a2)
        seg_indices_b = _spans_in_range(b_spans, b1, b2)

        text_a = full_a[a1:a2]
        text_b = full_b[b1:b2]

        start_a = segs_a[seg_indices_a[0]].start if seg_indices_a else None
        end_a = segs_a[seg_indices_a[-1]].end if seg_indices_a else None
        start_b = segs_b[seg_indices_b[0]].start if seg_indices_b else None
        end_b = segs_b[seg_indices_b[-1]].end if seg_indices_b else None

        if tag == "equal":
            level = DiffLevel.SAME
        elif tag == "delete":
            level = DiffLevel.ORPHAN
        elif tag == "insert":
            level = DiffLevel.ORPHAN
        else:  # replace
            level = grade_difference(text_a, text_b)

        # Skip empty fragments
        if not text_a and not text_b:
            continue

        raw_results.append(DiffResult(
            level=level,
            start_a=start_a, end_a=end_a, text_a=text_a,
            start_b=start_b, end_b=end_b, text_b=text_b,
            segment_index=len(raw_results),
        ))

    # 4. Merge adjacent same-level fragments to reduce noise
    return _merge_adjacent(raw_results)


def _build_text_and_spans(segs: list[Segment]) -> tuple[str, list[tuple[int, int]]]:
    """Build concatenated text and a list of (start_char, end_char) spans per segment."""
    text = ""
    spans = []
    for seg in segs:
        spans.append((len(text), len(text) + len(seg.text)))
        text += seg.text
    return text, spans


def _spans_in_range(spans: list[tuple[int, int]], start: int, end: int) -> list[int]:
    """Return indices of spans that overlap with [start, end)."""
    indices = []
    for i, (s, e) in enumerate(spans):
        if s < end and e > start:
            indices.append(i)
    return indices


def _merge_adjacent(results: list[DiffResult]) -> list[DiffResult]:
    """Merge adjacent DiffResults to produce cleaner segment-level output.

    Character-level diffs alternate between tiny SAME/DIFF fragments
    (e.g. "会"(SAME) → "议"(ORPHAN) → "今天"(SAME)).
    We merge small alternations into larger blocks.
    """
    if not results:
        return []

    # Group into runs: merge consecutive fragments where at least
    # one side's text is short (< 10 chars) into the surrounding context.
    merged: list[DiffResult] = []
    i = 0
    while i < len(results):
        r = results[i]
        # If this fragment is tiny on both sides, merge with the next one
        if len(r.text_a) < 5 and len(r.text_b) < 5 and i + 1 < len(results):
            next_r = results[i + 1]
            r = DiffResult(
                level=_worse_level(r.level, next_r.level),
                start_a=r.start_a or next_r.start_a,
                end_a=next_r.end_a or r.end_a,
                text_a=r.text_a + next_r.text_a,
                start_b=r.start_b or next_r.start_b,
                end_b=next_r.end_b or r.end_b,
                text_b=r.text_b + next_r.text_b,
                segment_index=r.segment_index,
            )
            i += 1

        merged.append(r)
        i += 1

    # Second pass: merge adjacent same-level fragments
    if not merged:
        return []

    final: list[DiffResult] = []
    current = merged[0]
    for next_r in merged[1:]:
        if current.level == next_r.level:
            current.text_a += next_r.text_a
            current.text_b += next_r.text_b
            current.end_a = next_r.end_a or current.end_a
            current.end_b = next_r.end_b or current.end_b
        else:
            final.append(current)
            current = next_r
    final.append(current)

    # Re-index
    for idx, r in enumerate(final):
        r.segment_index = idx

    return final


def _worse_level(a: DiffLevel, b: DiffLevel) -> DiffLevel:
    """Return the more severe of two diff levels."""
    order = {DiffLevel.SAME: 0, DiffLevel.SMALL: 1, DiffLevel.LARGE: 2, DiffLevel.ORPHAN: 3}
    return a if order[a] >= order[b] else b


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
