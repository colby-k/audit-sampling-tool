# launch_gui.spec — Final Build for Audit Sampling Launcher

block_cipher = None

a = Analysis(
    ['launch_gui.py'],
    pathex=['.'],
    binaries=[],
    datas=[('streamlit_app.py', '.')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Audit Sampling Launcher',  # ✅ App display name
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # ✅ Hide terminal window
    icon='audit.ico'  # ✅ Optional: drop your .ico file in same folder
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AuditLauncher'
)
