#!/usr/bin/env python3
"""
Render a textual visualization of analysis processing times.

The script expects a path to an analysis JSON payload (like the files under
`data/storage/analyses/`). It extracts section-level and sub-section level
processing times and prints a sorted breakdown so we can quickly diagnose
slow stages in the pipeline.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

BAR_WIDTH_SECTION = 40
BAR_WIDTH_SUBSECTION = 28


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Visualize processing-time breakdown for an analysis response."
    )
    parser.add_argument(
        "analysis_file",
        type=Path,
        help="Path to the analysis JSON file.",
    )
    parser.add_argument(
        "--sort",
        choices=("time", "name"),
        default="time",
        help="Sort sections by total time (default) or alphabetically.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Only display the top N sections after sorting.",
    )
    return parser.parse_args()


def safe_get(container: dict[str, Any], *path: str) -> Any | None:
    current: Any = container
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current


def load_structured_data(payload: dict[str, Any]) -> dict[str, Any]:
    candidates = (
        safe_get(payload, "full_results", "structured_data"),
        payload.get("structured_data"),
        safe_get(payload, "analysis_response", "structured_data"),
    )
    for candidate in candidates:
        if isinstance(candidate, dict):
            return candidate
    raise ValueError("Could not locate structured_data in the supplied analysis file.")


def gather_sections(structured: dict[str, Any]) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    for entry in structured.get("section_analyses", []) or []:
        section = {
            "name": entry.get("section_name", "Unnamed section"),
            "time": entry.get("processing_time_ms"),
            "sub_sections": [
                {
                    "name": sub.get("sub_section_name", "Unnamed sub-section"),
                    "time": sub.get("processing_time_ms"),
                }
                for sub in (entry.get("sub_sections") or [])
                if sub.get("processing_time_ms") is not None
            ],
        }

        # Only include sub-sections with a recorded processing time.
        section["sub_sections"] = [
            s for s in section["sub_sections"] if s["time"] is not None
        ]
        sections.append(section)
    return sections


def format_duration(ms: int | None) -> str:
    if ms is None:
        return "n/a"
    seconds = ms / 1000
    if seconds >= 60:
        minutes = int(seconds // 60)
        rem = seconds % 60
        if rem >= 1:
            return f"{minutes}m {rem:04.1f}s"
        return f"{minutes}m"
    return f"{seconds:0.2f}s"


def render_bar(value: int | None, max_value: int, width: int) -> str:
    if value is None or value <= 0 or max_value <= 0:
        return ""
    portion = value / max_value
    filled = max(1, int(round(portion * width)))
    filled = min(filled, width)
    return "#" * filled


def percent(part: int | None, whole: int) -> str:
    if part is None or whole <= 0:
        return "n/a"
    return f"{(part / whole) * 100:5.1f}%"


def resolve_total_ms(structured: dict[str, Any], payload: dict[str, Any]) -> int | None:
    total = structured.get("total_processing_time_ms")
    if isinstance(total, int):
        return total
    duration_seconds = safe_get(payload, "summary", "processing", "duration_seconds")
    if isinstance(duration_seconds, (int | float)):
        return int(duration_seconds * 1000)
    return None


def main() -> None:
    args = parse_args()
    if not args.analysis_file.exists():
        raise SystemExit(f"File not found: {args.analysis_file}")

    payload = json.loads(args.analysis_file.read_text())
    structured = load_structured_data(payload)
    sections = gather_sections(structured)

    if not sections:
        raise SystemExit("No section analyses with processing times found.")

    total_ms = resolve_total_ms(structured, payload)
    sections_with_time = [s for s in sections if s["time"] is not None]
    inferred_total = sum(s["time"] for s in sections_with_time)
    percent_total = inferred_total or total_ms or 0
    section_max = max((s["time"] or 0) for s in sections)

    if args.sort == "time":
        sections.sort(key=lambda s: (s["time"] or 0), reverse=True)
    else:
        sections.sort(key=lambda s: s["name"])

    if args.limit is not None:
        sections = sections[: args.limit]

    analysis_id = payload.get("analysis_id", "unknown")
    analysis_type = payload.get("analysis_type", "unknown")
    print(f"Analysis: {analysis_id} ({analysis_type})")
    print(f"Source:  {args.analysis_file}")
    if total_ms is not None:
        print(f"Total processing time: {format_duration(total_ms)}")
    else:
        print(f"Total processing time: inferred {format_duration(inferred_total)}")
    if total_ms is not None and inferred_total and total_ms != inferred_total:
        print(
            f"Section times sum to {format_duration(inferred_total)}; "
            "percentages use that baseline."
        )
    print()
    print("Section breakdown:")

    for section in sections:
        section_time = section["time"]
        bar = render_bar(section_time, section_max, BAR_WIDTH_SECTION)
        pct = percent(section_time, percent_total) if percent_total else "n/a"
        print(f"- {section['name']}")
        print(f"    {format_duration(section_time):>12} | {pct:>6} | {bar}")

        if section["sub_sections"]:
            max_sub_time = max((sub["time"] or 0) for sub in section["sub_sections"])
            for sub in section["sub_sections"]:
                sub_bar = render_bar(sub["time"], max_sub_time, BAR_WIDTH_SUBSECTION)
                sub_pct = (
                    percent(sub["time"], percent_total) if percent_total else "n/a"
                )
                print(
                    f"      - {sub['name']}: {format_duration(sub['time']):>10} | {sub_pct:>6} | {sub_bar}"
                )
        print()


if __name__ == "__main__":
    main()
