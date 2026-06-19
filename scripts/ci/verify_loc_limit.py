#!/usr/bin/env python3
"""Verify a hard max-LOC limit on logic code.

Run: uv run python scripts/ci/verify_loc_limit.py
Exits non-zero if any non-test .py source exceeds MAX_LOC logical lines.

Tests are excepted (test files and any path under tests/). Blank lines and
comment-only lines are not counted (they are not logic). The intent is to keep
logic modules small and forceful about splitting; see CONTEXT.md quality-gates.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SRC_ROOT = REPO_ROOT / "packages" / "twat" / "src"
MAX_LOC = 500


def _logical_lines(text: str) -> int:
    """Count non-blank, non-comment lines."""
    count = 0
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            continue
        count += 1
    return count


def main() -> int:
    if not SRC_ROOT.exists():
        print(f"LOC limit OK (no source at {SRC_ROOT}).")
        return 0
    issues: list[str] = []
    for py in SRC_ROOT.rglob("*.py"):
        rel = py.relative_to(REPO_ROOT)
        # tests are excepted
        if "tests" in py.parts:
            continue
        try:
            text = py.read_text(encoding="utf-8")
        except OSError as e:
            issues.append(f"{rel}: unreadable: {e}")
            continue
        loc = _logical_lines(text)
        if loc > MAX_LOC:
            issues.append(f"{rel}: {loc} logical lines > {MAX_LOC} limit")
    if issues:
        print(
            f"LOC limit check failed (max {MAX_LOC} logic lines, tests excepted):", file=sys.stderr
        )
        for i in issues:
            print(f"  - {i}", file=sys.stderr)
        return 1
    print(f"LOC limit OK (max {MAX_LOC}, tests excepted).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
