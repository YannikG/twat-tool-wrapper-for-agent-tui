#!/usr/bin/env python3
"""Verify docs integrity: internal markdown links resolve and spec frontmatter is valid.

Run: uv run python scripts/ci/verify_docs.py
Exits non-zero on any violation.

Ponytail: stdlib only, no markdown dep. Scans *.md under the repo (docs/, root
CONTEXT.md, ADRs). Checks:
  - every `[text](rel/path.md)`-style link resolves to an existing file
  - every spec under docs/specs/** has frontmatter with `status:` and `entity:`
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
MD_FILES = list(REPO_ROOT.rglob("*.md"))

_IGNORE_DIRS = {".git", ".venv", "node_modules", "__pycache__", ".tmp"}


def _markdown_files() -> list[Path]:
    out: list[Path] = []
    for p in MD_FILES:
        rel = p.relative_to(REPO_ROOT)
        if any(part in _IGNORE_DIRS for part in rel.parts):
            continue
        out.append(p)
    return out


def check_links(file: Path) -> list[str]:
    text = file.read_text(encoding="utf-8")
    issues: list[str] = []
    for m in LINK_RE.finditer(text):
        target = m.group(1).strip()
        if target.startswith(("http://", "https://", "#", "mailto:")):
            continue
        # strip anchor
        path_part = target.split("#", 1)[0]
        if not path_part:
            continue
        resolved = (file.parent / path_part).resolve()
        if not resolved.exists():
            issues.append(f"{file.relative_to(REPO_ROOT)}: broken link -> {target}")
    return issues


def check_spec_frontmatter(file: Path) -> list[str]:
    rel = file.relative_to(REPO_ROOT)
    if rel.parts[0:2] != ("docs", "specs"):
        return []
    text = file.read_text(encoding="utf-8")
    m = FRONTMATTER_RE.match(text)
    if not m:
        return [f"{rel}: missing YAML frontmatter"]
    fm = m.group(1)
    issues: list[str] = []
    if not re.search(r"^status:\s*\S+", fm, re.MULTILINE):
        issues.append(f"{rel}: frontmatter missing 'status'")
    if not re.search(r"^entity:\s*\S+", fm, re.MULTILINE):
        issues.append(f"{rel}: frontmatter missing 'entity'")
    return issues


def main() -> int:
    issues: list[str] = []
    files = _markdown_files()
    if not (REPO_ROOT / "CONTEXT.md").exists():
        issues.append("CONTEXT.md missing at repo root")
    for f in files:
        issues.extend(check_links(f))
        issues.extend(check_spec_frontmatter(f))
    if issues:
        print("Docs verification failed:", file=sys.stderr)
        for i in issues:
            print(f"  - {i}", file=sys.stderr)
        return 1
    print(f"Docs OK ({len(files)} markdown files checked).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
