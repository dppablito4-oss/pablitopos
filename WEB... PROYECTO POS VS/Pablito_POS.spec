# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('logo.png', '.'), ('logo.ico', '.')]
binaries = []
hiddenimports = ['ttkbootstrap', 'ttkbootstrap.constants', 'reportlab', 'reportlab.pdfgen', 'reportlab.lib', 'PIL', 'PIL.Image', 'app_ui.security', 'app_ui.profiles', 'app_ui.messages', 'app_ui.effects', 'app_ui.hotkeys', 'app_ui.backups', 'app_core.email_templates', 'app_core.logging_setup', 'app_core.ui_helpers', 'pyzipper']
tmp_ret = collect_all('app_ui')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('app_core')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['app_boletas.py'],
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
    a.binaries,
    a.datas,
    [],
    name='Pablito_POS',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['logo.ico'],
)
