# PyInstaller build recipe. Run it with `pyinstaller gameoflife.spec`.
#
# The game has no data files of its own - the fonts come from the system, and
# everything else is code - so this is a plain one-file bundle of the launcher
# plus the `life` package. numpy is a genuine runtime dependency (life/sound.py
# vectorizes note synthesis with it) and must stay out of this list; the other
# heavy toolkits that get pulled in by accident are still excluded to keep the
# executable small.

excludes = [
    "tkinter",
    "unittest",
    "pydoc",
    "doctest",
    "email",
    "html",
    "http",
    "xml",
    "pygame.examples",
    "pygame.tests",
]

a = Analysis(
    ["gameoflife.py"],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
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
    name="gameoflife",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
