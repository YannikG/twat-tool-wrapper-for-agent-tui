#!/usr/bin/env python3
"""Verify architecture guardrails: core must not import PySide6.

Run: uv run python scripts/ci/verify_doc_guardrails.py
Exits non-zero if any module under the core path imports PySide6 or Qt.

Core lives at packages/twat/src/twat/core/** (created in later slices). Until
core exists, this is a no-op pass. The check runs on actual source so it stays
honest as the codebase grows.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
# Layers that must stay free of UI bindings: core (domain) and app (services).
# The UI layer (twat.ui.*) and the composition root (twat.__main__) may import Qt.
CORE_ROOTS = [
    REPO_ROOT / "packages" / "twat" / "src" / "twat" / "core",
    REPO_ROOT / "packages" / "twat" / "src" / "twat" / "app",
]
FORBIDDEN = ("PySide6", "PyQt", "shiboken")


def main() -> int:
    if not any(p.exists() for p in CORE_ROOTS):
        print("Guardrails OK (no core/app path yet).")
        return 0
    issues: list[str] = []
    for core_root in CORE_ROOTS:
        if not core_root.exists():
            continue
        for py in core_root.rglob("*.py"):
            rel = py.relative_to(REPO_ROOT)
            try:
                text = py.read_text(encoding="utf-8")
            except OSError as e:
                issues.append(f"{rel}: unreadable: {e}")
                continue
            for lineno, line in enumerate(text.splitlines(), 1):
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                if any(f in line for f in FORBIDDEN) and ("import" in line):
                    issues.append(f"{rel}:{lineno}: layer imports UI binding: {stripped}")
    if issues:
        print("Guardrail check failed (core/app must not import PySide6):", file=sys.stderr)
        for i in issues:
            print(f"  - {i}", file=sys.stderr)
        return 1
    print("Guardrails OK.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
