"""STDP PyInstaller Build Script.

Builds the STDP application into a standalone executable bundle
using PyInstaller --onedir mode. All Python dependencies (PyQt6,
PyQt6-WebEngine, requests, bs4, psutil, vdf, pydantic) are bundled
so the end user does NOT need Python installed.

Usage:
    python build_exe.py
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
DIST_DIR = PROJECT_ROOT / "dist"
BUILD_DIR = PROJECT_ROOT / "build"
SPEC_FILE = PROJECT_ROOT / "STDP.spec"


def ensure_pyinstaller() -> None:
    """Install PyInstaller if it is not already available."""
    try:
        import PyInstaller  # noqa: F401
        print("[OK] PyInstaller is already installed.")
    except ImportError:
        print("[..] Installing PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        print("[OK] PyInstaller installed.")


def clean_previous_build() -> None:
    """Remove previous build artifacts."""
    for d in (DIST_DIR, BUILD_DIR):
        if d.exists():
            print(f"[..] Cleaning {d}...")
            shutil.rmtree(d, ignore_errors=True)
    if SPEC_FILE.exists():
        try:
            SPEC_FILE.unlink()
        except Exception:
            pass


def build(mode: str = "onedir") -> None:
    """Run PyInstaller to create the STDP executable bundle.
    
    Args:
        mode: 'onedir' for a directory bundle (used for Inno Setup installer).
    """
    ensure_pyinstaller()
    clean_previous_build()

    main_script = str(PROJECT_ROOT / "main.py")

    # Data files to bundle inside the executable directory
    datas = [
        (str(PROJECT_ROOT / "config.json"), "."),
    ]
    if (PROJECT_ROOT / "bundled_installers").exists():
        datas.append((str(PROJECT_ROOT / "bundled_installers"), "bundled_installers"))
    if (PROJECT_ROOT / "UnRAR.exe").exists():
        datas.append((str(PROJECT_ROOT / "UnRAR.exe"), "."))
    if (PROJECT_ROOT / "st-setup-1.8.30.exe").exists():
        datas.append((str(PROJECT_ROOT / "st-setup-1.8.30.exe"), "."))

    # Hidden imports that PyInstaller might miss
    hidden_imports = [
        "PyQt6.QtCore",
        "PyQt6.QtGui",
        "PyQt6.QtWidgets",
        "PyQt6.QtWebEngineWidgets",
        "PyQt6.QtWebEngineCore",
        "PyQt6.QtWebChannel",
        "PyQt6.QtNetwork",
        "PyQt6.QtPositioning",
        "PyQt6.QtPrintSupport",
        "requests",
        "bs4",
        "psutil",
        "vdf",
        "pydantic",
        "pydantic.deprecated.decorator",
        "src",
        "src.core",
        "src.core.config",
        "src.core.events",
        "src.core.logger",
        "src.core.models",
        "src.depotbox",
        "src.depotbox.client",
        "src.depotbox.downloader",
        "src.depotbox.extractor",
        "src.onlinefix",
        "src.onlinefix.installer",
        "src.steam",
        "src.steam.acf_builder",
        "src.steam.depotcache_manager",
        "src.steam.detector",
        "src.steam.key_injector",
        "src.steam.process_manager",
        "src.steam.vdf_parser",
        "src.ui",
        "src.ui.main_window",
        "src.ui.browser_view",
        "src.ui.health_view",
        "src.ui.onlinefix_view",
        "src.ui.settings_view",
        "src.ui.theme",
        "src.ui.workers",
        "src.ui.adblocker",
        "src.ui.components",
        "src.ui.components.disk_selector",
        "src.ui.components.dropzone",
        "src.ui.components.game_card",
        "src.ui.components.log_console",
        "src.unlockers",
        "src.unlockers.base",
        "src.unlockers.factory",
        "src.unlockers.greenluma_adapter",
        "src.unlockers.steamtools_adapter",
    ]

    # Exclude unused large modules to dramatically reduce build size
    excludes = [
        "tkinter",
        "unittest",
        "test",
        "pdb",
        "idlelib",
        "PyQt6.QtBluetooth",
        "PyQt6.QtSensors",
        "PyQt6.QtSpatialAudio",
        "PyQt6.QtMultimedia",
        "PyQt6.QtMultimediaWidgets",
        "PyQt6.QtNfc",
        "PyQt6.QtHelp",
        "PyQt6.QtRemoteObjects",
        "PyQt6.QtSerialPort",
        "PyQt6.QtTextToSpeech",
        "PyQt6.QtStateMachine",
        "PyQt6.QtSql",
        "PyQt6.QtDesigner",
        "PyQt6.QtPdf",
        "PyQt6.QtPdfWidgets",
        "PyQt6.QtQuick3D",
        "PyQt6.QAxContainer",
        "PyQt6.QtOpenGLWidgets",
    ]

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onedir",
        "--name", "STDP",
        "--windowed",                 # No console window for GUI app
        "--icon", "NONE",             # No custom icon
    ]

    # Add data files
    separator = ";" if sys.platform == "win32" else ":"
    for src, dst in datas:
        cmd.extend(["--add-data", f"{src}{separator}{dst}"])

    # Add hidden imports
    for hi in hidden_imports:
        cmd.extend(["--hidden-import", hi])

    # Add exclusions
    for exc in excludes:
        cmd.extend(["--exclude-module", exc])

    # Collect submodules and binaries for key packages
    for pkg in ["pydantic", "requests", "bs4"]:
        cmd.extend(["--collect-all", pkg])

    cmd.append(main_script)

    print(f"[..] Running PyInstaller (ONEDIR mode for Installer)...")
    print(f"    Command: {' '.join(cmd[:6])}...")
    subprocess.check_call(cmd, cwd=str(PROJECT_ROOT))

    exe_path = DIST_DIR / "STDP" / "STDP.exe"
    if exe_path.exists():
        pre_size_mb = sum(f.stat().st_size for f in (DIST_DIR / "STDP").rglob("*") if f.is_file()) / (1024 * 1024)
        print(f"[..] Raw PyInstaller Bundle Size: {pre_size_mb:.1f} MB")
        print("[..] Applying high-efficiency bundle optimization (stripping debug files, unused locales, bloat)...")
        optimize_bundle(DIST_DIR / "STDP")
        post_size_mb = sum(f.stat().st_size for f in (DIST_DIR / "STDP").rglob("*") if f.is_file()) / (1024 * 1024)
        saved_mb = pre_size_mb - post_size_mb

        print(f"\n[OK] PyInstaller build & optimization successful!")
        print(f"    Output Directory: {DIST_DIR / 'STDP'}")
        print(f"    Executable: {exe_path}")
        print(f"    Optimized Bundle Size: {post_size_mb:.1f} MB (Reduced by {saved_mb:.1f} MB / %{(saved_mb/pre_size_mb)*100:.1f})")
    else:
        print(f"\n[FAIL] Build may have failed — {exe_path} not found.")
        sys.exit(1)


def optimize_bundle(bundle_dir: Path) -> None:
    """Trim debug packages, unused locales, unused DLLs and stubs from the output bundle."""
    # 1. Remove debug paks and bins in resources
    res_dir = bundle_dir / "_internal" / "PyQt6" / "Qt6" / "resources"
    if res_dir.exists():
        for f in res_dir.glob("*.debug.*"):
            try:
                f.unlink()
            except Exception:
                pass

    # 2. Trim translations (keep only tr and en)
    trans_dir = bundle_dir / "_internal" / "PyQt6" / "Qt6" / "translations"
    if trans_dir.exists():
        for f in list(trans_dir.glob("*.qm")):
            stem = f.stem.lower()
            if not (stem.endswith("_tr") or stem.endswith("_en") or stem in ["qt_tr", "qt_en", "qtbase_tr", "qtbase_en"]):
                try:
                    f.unlink()
                except Exception:
                    pass

        # 3. Trim Chromium WebEngine locale paks (keep tr, en-US, en-GB, ru)
        locales_dir = trans_dir / "qtwebengine_locales"
        if locales_dir.exists():
            allowed_locales = {"tr.pak", "en-US.pak", "en-GB.pak", "ru.pak", "en_US.pak", "en_GB.pak"}
            for pak in list(locales_dir.glob("*.pak")):
                if pak.name not in allowed_locales:
                    try:
                        pak.unlink()
                    except Exception:
                        pass

    # 4. Remove unused QML, bindings, and heavy software fallback DLLs
    for path_rel in [
        bundle_dir / "_internal" / "PyQt6" / "Qt6" / "qml",
        bundle_dir / "_internal" / "PyQt6" / "bindings",
        bundle_dir / "_internal" / "PyQt6" / "Qt6" / "qsci",
        bundle_dir / "_internal" / "PyQt6" / "Qt6" / "bin" / "opengl32sw.dll",
    ]:
        if path_rel.exists():
            if path_rel.is_dir():
                shutil.rmtree(path_rel, ignore_errors=True)
            else:
                try:
                    path_rel.unlink()
                except Exception:
                    pass

    # 5. Remove unused DLLs
    bin_dir = bundle_dir / "_internal" / "PyQt6" / "Qt6" / "bin"
    if bin_dir.exists():
        unused_prefixes = [
            "avcodec", "avformat", "avutil", "swscale", "swresample",
            "Qt6Multimedia", "Qt6Bluetooth", "Qt6RemoteObjects", "Qt6SpatialAudio",
            "Qt6Help", "Qt6Sensors", "Qt6Nfc", "Qt6Sql", "Qt6StateMachine",
            "Qt6SerialPort", "Qt6TextToSpeech", "Qt6Pdf", "Qt6QuickControls2",
            "Qt6QuickDialogs2", "Qt6Labs", "Qt6Quick3D", "Qt6Designer", "Qt6ShaderTools",
        ]
        for f in bin_dir.glob("*.dll"):
            for pref in unused_prefixes:
                if f.name.startswith(pref):
                    try:
                        f.unlink()
                    except Exception:
                        pass
                    break

    # 6. Remove unused plugins
    plugins_dir = bundle_dir / "_internal" / "PyQt6" / "Qt6" / "plugins"
    if plugins_dir.exists():
        for d in ["audio", "sensorgestures", "sensors", "sqldrivers", "multimedia", "designer", "position", "scenegraph", "qmltooling", "sceneparsers"]:
            p = plugins_dir / d
            if p.exists():
                shutil.rmtree(p, ignore_errors=True)

    # 7. Remove unused .pyd files & .pyi stubs in _internal/PyQt6
    pyqt_dir = bundle_dir / "_internal" / "PyQt6"
    if pyqt_dir.exists():
        for f in pyqt_dir.glob("*.pyi"):
            try:
                f.unlink()
            except Exception:
                pass
        for pyd in pyqt_dir.glob("Qt*.pyd"):
            base = pyd.stem.split(".")[0]
            if base not in ["QtCore", "QtGui", "QtWidgets", "QtWebEngineCore", "QtWebEngineWidgets", "QtWebChannel", "QtNetwork", "sip"]:
                try:
                    pyd.unlink()
                except Exception:
                    pass


if __name__ == "__main__":
    build()
