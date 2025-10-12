"""
Shared summary helper utilities extracted from the legacy WorkerService.

These helpers provide deterministic text normalisation and list handling
behaviour used by the analysis summary collaborator. Keeping them in a
separate module allows other collaborators (or tests) to reuse the exact
string munging semantics without depending on WorkerService internals.
"""

from __future__ import annotations

import re
from typing import Any

__all__ = [
    "append_unique",
    "clean_text",
    "clip_summary_text",
    "coerce_float",
    "ensure_string_list",
    "slugify_identifier",
]


def clean_text(value: Any) -> str | None:
    """Normalise textual content to a compact string."""

    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        return text or None
    return str(value)


def coerce_float(value: Any) -> float | None:
    """Best-effort conversion of heterogeneous numeric inputs."""

    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def slugify_identifier(value: str | None) -> str:
    """Generate a slug suitable for identifier usage."""

    if not value:
        return ""
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def ensure_string_list(candidate: Any) -> list[str]:
    """Return a cleaned list of strings for curated collections."""

    if not isinstance(candidate, list):
        return []
    items: list[str] = []
    for value in candidate:
        if isinstance(value, str):
            text = value.strip()
            if text:
                items.append(text)
    return items


def append_unique(
    items: list[str],
    candidate: Any,
    *,
    limit: int | None = None,
) -> None:
    """Append cleaned string candidates while avoiding duplicates."""

    if limit is not None and len(items) >= limit:
        return

    text = clean_text(candidate)
    if not text or text in items:
        return

    if limit is not None and len(items) >= limit:
        return
    items.append(text)


def clip_summary_text(
    value: str | None,
    *,
    max_chars: int = 280,
) -> str | None:
    """Trim narrative strings to the summary segment constraints."""

    text = clean_text(value)
    if text is None:
        return None

    if len(text) <= max_chars:
        return text

    sentences = re.split(r"(?<=[.!?])\s+", text)
    clipped = ""
    for sentence in sentences:
        if not sentence:
            continue
        candidate = sentence if not clipped else f"{clipped} {sentence}"
        if len(candidate) > max_chars:
            break
        clipped = candidate

    if clipped:
        return clipped

    return text[: max_chars - 1].rstrip() + "…"
