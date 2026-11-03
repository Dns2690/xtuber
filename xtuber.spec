# xtuber.spec
# Configuración de PyInstaller: genera un ejecutable con Python, todas las
# dependencias y los binarios externos (ffmpeg, ffprobe y deno).
#
# Uso:
#   pyinstaller xtuber.spec --noconfirm
#
# Los binarios deben estar en ./bin/ (build.sh / build_windows.bat los descargan):
#   Mac:     bin/ffmpeg  bin/ffprobe  bin/deno
#   Windows: bin/ffmpeg.exe  bin/ffprobe.exe  bin/deno.exe

import os
import re
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata

# ── Versión (fuente única: VERSION en xtuber.py) ─────────────────────────────
with open("xtuber.py", encoding="utf-8") as fh:
    VERSION = re.search(r'^VERSION\s*=\s*"([^"]+)"', fh.read(), re.M).group(1)

# ── Binarios externos ────────────────────────────────────────────────────────
ext = ".exe" if sys.platform == "win32" else ""
binaries = []
for tool in ("ffmpeg", "ffprobe", "deno"):
    path = os.path.join("bin", tool + ext)
    if not os.path.isfile(path):
        raise SystemExit(f"Falta {path}. Ejecuta el script de build para descargarlo.")
    binaries.append((path, "bin"))

# ── Datos ────────────────────────────────────────────────────────────────────
datas = (
    collect_data_files("customtkinter", include_py_files=False)
    + collect_data_files("yt_dlp")
    + collect_data_files("yt_dlp_ejs")   # scripts JS para el reto de YouTube
    + collect_data_files("certifi")      # certificados raíz para HTTPS
    + copy_metadata("yt-dlp")            # permite leer la versión incluida
)

hiddenimports = (
    collect_submodules("yt_dlp")
    + collect_submodules("yt_dlp_ejs")
    + ["customtkinter", "certifi", "brotli", "mutagen", "Cryptodome",
       "websockets", "requests", "urllib3"]
)

a = Analysis(
    ["xtuber.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["matplotlib", "numpy", "pandas", "scipy", "PIL", "tkinter.test"],
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure)

# ── macOS: onedir + BUNDLE (.app nativo) ─────────────────────────────────────
if sys.platform == "darwin":
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name="Xtuber",
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
    )

    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=False,
        upx_exclude=[],
        name="Xtuber",
    )

    app = BUNDLE(
        coll,
        name="Xtuber.app",
        bundle_identifier="com.xtuber.app",
        info_plist={
            "CFBundleName":               "Xtuber",
            "CFBundleDisplayName":        "Xtuber",
            "CFBundleShortVersionString": VERSION,
            "CFBundleVersion":            VERSION,
            "NSHighResolutionCapable":    True,
            "LSMinimumSystemVersion":     "11.0",
        },
    )

# ── Windows: onefile ─────────────────────────────────────────────────────────
else:
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
        upx=False,   # UPX corrompe deno/ffmpeg y dispara falsos positivos de antivirus
        upx_exclude=[],
        runtime_tmpdir=None,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
    )
