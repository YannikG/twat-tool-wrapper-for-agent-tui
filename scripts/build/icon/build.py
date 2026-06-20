#!/usr/bin/env python3
"""Regenerate assets/icon/icon.icns and icon.ico from the package PNG."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
PNG = ROOT / "packages/twat/src/twat/ui/assets/icon.png"
OUT = ROOT / "assets/icon"
ICONSET = OUT / "icon.iconset"


def main() -> int:
    if not PNG.is_file():
        print(f"missing source icon: {PNG}", file=sys.stderr)
        return 1
    OUT.mkdir(parents=True, exist_ok=True)
    shutil.copy2(PNG, OUT / "icon.png")

    if ICONSET.exists():
        shutil.rmtree(ICONSET)
    ICONSET.mkdir()
    for size in (16, 32, 128, 256, 512):
        for scale, px in ((1, size), (2, size * 2)):
            out = ICONSET / f"icon_{size}x{size}{'' if scale == 1 else '@2x'}.png"
            subprocess.run(
                ["sips", "-z", str(px), str(px), str(PNG), "--out", str(out)],
                check=True,
                stdout=subprocess.DEVNULL,
            )
    subprocess.run(
        ["iconutil", "-c", "icns", str(ICONSET), "-o", str(OUT / "icon.icns")],
        check=True,
    )
    shutil.rmtree(ICONSET)

    img = Image.open(PNG)
    img.save(
        OUT / "icon.ico",
        format="ICO",
        sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    print(f"wrote {OUT / 'icon.icns'} and {OUT / 'icon.ico'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
