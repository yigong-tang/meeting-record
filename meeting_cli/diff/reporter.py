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
            <td class="ts">[{format_ts(r.start_a)} -> {format_ts(r.end_a)}]</td>
            <td class="text">{r.text_a}</td>
            <td class="ts">[{format_ts(r.start_b)} -> {format_ts(r.end_b)}]</td>
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
    - user_choice == 'A' -> text_a
    - user_choice == 'B' -> text_b
    - user_choice == 'manual' -> user_edited_text
    - user_choice == 'skip' -> skip this segment
    - For SAME level -> text_a (either, they're the same)
    - For orphan with only one side -> the text that exists

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
            # SAME/SMALL/LARGE without explicit choice -> default to A
            text = r.text_a
            start = r.start_a
            end = r.end_a

        if text and start is not None and end is not None:
            lines.append(
                f"[{format_ts(start)} -> {format_ts(end)}] {text}"
            )

    return "\n".join(lines)
