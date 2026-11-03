"""Versioned prompt loader for the translation stage (F5-AG-01)."""

from __future__ import annotations

import re
from pathlib import Path


def load_prompt(path: str | Path) -> tuple[str, str]:
    """Load a versioned prompt file and return (content, version).

    Version is extracted from the filename pattern ``<name>.<version>.<ext>``,
    e.g. ``translate_page.v1.txt`` → ``"v1"``.  Falls back to ``"unknown"``
    when the pattern does not match.
    """
    p = Path(path)
    content: str = p.read_text(encoding="utf-8")
    m = re.search(r"\.(v\d+)\.\w+$", p.name)
    version: str = m.group(1) if m else "unknown"
    return content, version
