#!/usr/bin/env python3
"""Build a PyInstaller bundle for TWAT (macOS .app / Linux dir / Windows .exe).

Run from repo root: uv run python scripts/build/pyinstaller/build.py
Requires dev deps: uv sync --group dev
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "packages/twat/src"
MAIN = SRC / "twat/__main__.py"


def main() -> int:
    if not MAIN.is_file():
        print(f"entry not found: {MAIN}", file=sys.stderr)
        return 1
    for name in ("dist", "build"):
        path = ROOT / name
        if path.exists():
            shutil.rmtree(path)
    spec = ROOT / "scripts/build/pyinstaller/twat.spec"
    cmd = [sys.executable, "-m", "PyInstaller", str(spec), "--noconfirm", "--clean"]
    print("Running:", " ".join(cmd))
    subprocess.run(cmd, cwd=ROOT, check=True)
    print(f"Done. See {ROOT / 'dist'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
