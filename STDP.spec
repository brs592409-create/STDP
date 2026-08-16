# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('D:/STDP/config.json', '.')]
binaries = []
hiddenimports = ['PyQt6.QtCore', 'PyQt6.QtGui', 'PyQt6.QtWidgets', 'PyQt6.QtWebEngineWidgets', 'PyQt6.QtWebEngineCore', 'PyQt6.QtWebChannel', 'PyQt6.QtNetwork', 'PyQt6.QtPositioning', 'PyQt6.QtPrintSupport', 'requests', 'bs4', 'psutil', 'vdf', 'pydantic', 'pydantic.deprecated.decorator', 'src', 'src.core', 'src.core.config', 'src.core.events', 'src.core.logger', 'src.core.models', 'src.depotbox', 'src.depotbox.client', 'src.depotbox.downloader', 'src.depotbox.extractor', 'src.onlinefix', 'src.onlinefix.installer', 'src.steam', 'src.steam.acf_builder', 'src.steam.depotcache_manager', 'src.steam.detector', 'src.steam.key_injector', 'src.steam.process_manager', 'src.steam.vdf_parser', 'src.ui', 'src.ui.main_window', 'src.ui.browser_view', 'src.ui.health_view', 'src.ui.onlinefix_view', 'src.ui.settings_view', 'src.ui.theme', 'src.ui.workers', 'src.ui.adblocker', 'src.ui.components', 'src.ui.components.disk_selector', 'src.ui.components.dropzone', 'src.ui.components.game_card', 'src.ui.components.log_console', 'src.unlockers', 'src.unlockers.base', 'src.unlockers.factory', 'src.unlockers.greenluma_adapter', 'src.unlockers.steamtools_adapter']
tmp_ret = collect_all('PyQt6')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('pydantic')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('requests')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('bs4')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['D:/STDP/main.py'],
    pathex=[],
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

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='STDP',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='NONE',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='STDP',
)
