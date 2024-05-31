# schedule_windowed.spec
# This spec file is for creating a windowed (non-console) executable from main.pyw

# Define the Analysis object
a = Analysis(
    ['main.pyw'],
    pathex=['.'],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    noarchive=False,
)

# Define the PYZ object (Python compiled code)
pyz = PYZ(a.pure, a.zipped_data)

# Define the EXE object (the executable to be created)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='schedule',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Set to False for a windowed application
    disable_windowed_traceback=False,
)

# Define the COLLECT object (collects all necessary files)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='schedule'
)
