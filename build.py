from __future__ import annotations

import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PyQt6.QtGui import QGuiApplication, QIcon, QPixmap

from app_meta import APP_NAME, APP_VERSION


ROOT = Path(__file__).resolve().parent
DIST_DIR = ROOT / "dist"
BUILD_DIR = ROOT / "build"
ASSETS_DIR = ROOT / "assets"
ICON_PNG = ASSETS_DIR / "icon.png"
ICON_SVG = ASSETS_DIR / "icon.svg"


def ensure_icon(target_os: str) -> Path | None:
    if target_os == "Windows":
        ico_path = ASSETS_DIR / "icon.ico"
        if ico_path.exists():
            return ico_path
        return _create_ico(ico_path)
    if target_os == "Darwin":
        icns_path = ASSETS_DIR / "icon.icns"
        if icns_path.exists():
            return icns_path
        return _create_icns(icns_path)
    return ICON_PNG if ICON_PNG.exists() else None


def _create_ico(output_path: Path) -> Path | None:
    pixmap = _load_pixmap()
    if pixmap is None:
        return None
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pixmap.save(str(output_path), "ICO")
    return output_path if output_path.exists() else None


def _create_icns(output_path: Path) -> Path | None:
    if not ICON_PNG.exists():
        return None
    iconutil = shutil.which("iconutil")
    if not iconutil:
        return None

    with tempfile.TemporaryDirectory() as temp_dir:
        iconset = Path(temp_dir) / "ClickForge.iconset"
        iconset.mkdir(parents=True, exist_ok=True)
        sizes = [16, 32, 64, 128, 256, 512]
        pixmap = _load_pixmap()
        if pixmap is None:
            return None
        for size in sizes:
            pixmap.scaled(size, size).save(str(iconset / f"icon_{size}x{size}.png"), "PNG")
            double = size * 2
            pixmap.scaled(double, double).save(str(iconset / f"icon_{size}x{size}@2x.png"), "PNG")
        subprocess.run([iconutil, "-c", "icns", str(iconset), "-o", str(output_path)], check=True)
    return output_path if output_path.exists() else None


def _load_pixmap() -> QPixmap | None:
    if ICON_SVG.exists():
        return QIcon(str(ICON_SVG)).pixmap(512, 512)
    if ICON_PNG.exists():
        return QPixmap(str(ICON_PNG))
    return None


def build() -> int:
    app = QGuiApplication.instance() or QGuiApplication([])
    _ = app
    system = platform.system()
    icon_path = ensure_icon(system)
    dist_name = f"{APP_NAME}.exe" if system == "Windows" else f"{APP_NAME}.app" if system == "Darwin" else "clickforge"

    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--distpath",
        str(DIST_DIR),
        "--workpath",
        str(BUILD_DIR / "work"),
        "--specpath",
        str(BUILD_DIR / "spec"),
        "--name",
        APP_NAME if system != "Linux" else "clickforge",
        str(ROOT / "main.py"),
    ]

    if system == "Darwin":
        command.append("--windowed")
    else:
        command.extend(["--onefile", "--windowed"])

    data_sep = ";" if system == "Windows" else ":"
    command.extend(["--add-data", f"{ROOT / 'ui' / 'styles.qss'}{data_sep}ui"])
    command.extend(["--add-data", f"{ASSETS_DIR}{data_sep}assets"])

    if icon_path:
        command.extend(["--icon", str(icon_path)])

    print(f"Building {APP_NAME} v{APP_VERSION} ({dist_name}) for {system}...")
    try:
        subprocess.run(command, cwd=ROOT, check=True)
    except subprocess.CalledProcessError as exc:
        if system == "Windows" and icon_path and "--icon" in command:
            print("Icon injection was blocked by Windows. Retrying build without the embedded icon...")
            retry_command = command[:]
            icon_index = retry_command.index("--icon")
            retry_command[icon_index + 1] = "NONE"
            subprocess.run(retry_command, cwd=ROOT, check=True)
        else:
            raise exc

    print(f"Build completed in: {DIST_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(build())
