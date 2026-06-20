# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for TWAT."""

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

ROOT = Path(SPECPATH).resolve().parents[2]
SRC = ROOT / "packages/twat/src"
ICON_PNG = SRC / "twat/ui/assets/icon.png"
ICON_ICNS = ROOT / "assets/icon/icon.icns"
ICON_ICO = ROOT / "assets/icon/icon.ico"

datas: list = [(str(ICON_PNG), "twat/ui/assets")]
binaries: list = []
hiddenimports = ["twat"]

for pkg in ("PySide6", "termqt"):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

if sys.platform == "win32":
    d, b, h = collect_all("pywinpty")
    datas += d
    binaries += b
    hiddenimports += h

a = Analysis(
    [str(SRC / "twat/__main__.py")],
    pathex=[str(SRC)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

_bundle_icon = str(ICON_ICNS) if sys.platform == "darwin" and ICON_ICNS.is_file() else None
_exe_icon = str(ICON_ICO) if sys.platform == "win32" and ICON_ICO.is_file() else _bundle_icon

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="twat",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=_exe_icon,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="twat",
)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="twat.app",
        icon=_bundle_icon,
        bundle_identifier="dev.twat.app",
    )
