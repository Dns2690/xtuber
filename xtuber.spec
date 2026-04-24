# xtuber.spec
# Archivo de configuración para PyInstaller.
# Genera un ejecutable que incluye Python, todas las dependencias y ffmpeg.
#
# Uso:
#   pyinstaller xtuber.spec
#
# Requiere que los binarios de ffmpeg estén en la carpeta ./bin/
#   Mac:     bin/ffmpeg  (sin extensión, chmod +x)
#   Windows: bin/ffmpeg.exe

import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# ── Datos de CustomTkinter (fuentes, temas, imágenes) ────────────────────────
ctk_datas = collect_data_files("customtkinter", include_py_files=False)

# ── Datos de yt-dlp ──────────────────────────────────────────────────────────
ytdlp_datas = collect_data_files("yt_dlp")

# ── Binarios de ffmpeg (según plataforma) ────────────────────────────────────
if sys.platform == "win32":
    ffmpeg_binaries = [("bin/ffmpeg.exe", "bin")]
else:
    ffmpeg_binaries = [("bin/ffmpeg", "bin")]

# ── Análisis ─────────────────────────────────────────────────────────────────
a = Analysis(
    ["xtuber.py"],
    pathex=[],
    binaries=ffmpeg_binaries,
    datas=ctk_datas + ytdlp_datas,
    hiddenimports=[
        "customtkinter",
        "yt_dlp",
        "yt_dlp.extractor",
        "yt_dlp.postprocessor",
        *collect_submodules("yt_dlp"),
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["matplotlib", "numpy", "pandas", "scipy", "PIL", "tkinter.test"],
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure)

# ── Ejecutable ────────────────────────────────────────────────────────────────
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="Xtuber",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # Sin ventana de consola
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon="assets/icon.icns",   # ← Descomenta y pon tu icono aquí
)

# ── Bundle .app para Mac ─────────────────────────────────────────────────────
if sys.platform == "darwin":
    app = BUNDLE(
        exe,
        name="Xtuber.app",
        # icon="assets/icon.icns",   # ← Descomenta y pon tu icono aquí
        bundle_identifier="com.xtuber.app",
        info_plist={
            "CFBundleShortVersionString": "1.0.0",
            "CFBundleVersion":            "1.0.0",
            "NSHighResolutionCapable":    True,
            "LSMinimumSystemVersion":     "10.13.0",
        },
    )
