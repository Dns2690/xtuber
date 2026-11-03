#!/usr/bin/env bash
# ============================================================
#  build.sh — Build de Xtuber para macOS
#  Genera: dist/Xtuber.app  y  dist/Xtuber-mac-<arch>.dmg
#
#  Compila para la arquitectura de la Mac donde se ejecuta
#  (arm64 = Apple Silicon, x86_64 = Intel).
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

ARCH="$(uname -m)"
case "$ARCH" in
    arm64)  FF_ARCH="arm64"; DENO_ARCH="aarch64-apple-darwin" ;;
    x86_64) FF_ARCH="amd64"; DENO_ARCH="x86_64-apple-darwin" ;;
    *) echo "❌ Arquitectura no soportada: $ARCH"; exit 1 ;;
esac

VERSION="$(sed -nE 's/^VERSION = "([^"]+)"/\1/p' xtuber.py)"
DMG="dist/Xtuber-mac-${ARCH}.dmg"

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║        Xtuber — Build para macOS             ║"
echo "╚══════════════════════════════════════════════╝"
echo "   versión $VERSION · arquitectura $ARCH"
echo ""

# ── 1. Dependencias Python ───────────────────────────────────────────────────
echo "▶ Configurando entorno virtual Python..."
PYTHON="${PYTHON:-python3}"
if [ ! -d ".venv" ]; then
    "$PYTHON" -m venv .venv
fi
source .venv/bin/activate
python -c "import tkinter" 2>/dev/null || {
    echo "❌ Este Python no tiene Tk. Instala: brew install python-tk"; exit 1; }
pip install --quiet --upgrade pip
# -U: siempre empaquetar el yt-dlp más reciente
pip install --quiet --upgrade -r requirements.txt
echo "   ✓ yt-dlp $(python -c 'import yt_dlp; print(yt_dlp.version.__version__)')"

# ── 2. Binarios externos nativos para esta arquitectura ─────────────────────
mkdir -p bin
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# Verifica que el binario sea de la arquitectura correcta (sin ejecutarlo)
check_arch() {
    if ! lipo -archs "$1" 2>/dev/null | tr ' ' '\n' | grep -qx "$ARCH"; then
        echo "   ⚠ $1 no es $ARCH ($(lipo -archs "$1" 2>/dev/null)); se descargará de nuevo."
        rm -f "$1"
        return 1
    fi
}

fetch_zip() {  # fetch_zip <nombre> <url>
    local name="$1" url="$2"
    if [ -f "bin/$name" ] && check_arch "bin/$name"; then
        echo "   ✓ $name ya existe"
        return
    fi
    echo "▶ Descargando $name ($ARCH)..."
    curl -fL --progress-bar "$url" -o "$TMP/$name.zip"
    unzip -o -q "$TMP/$name.zip" -d "$TMP/$name"
    find "$TMP/$name" -type f -name "$name" -exec cp {} "bin/$name" \;
    chmod +x "bin/$name"
    xattr -c "bin/$name" 2>/dev/null || true
    check_arch "bin/$name" || { echo "❌ $name descargado no es $ARCH"; exit 1; }
    echo "   ✓ $name listo"
}

# ffmpeg/ffprobe estáticos (sin dependencias de Homebrew)
FF_BASE="https://ffmpeg.martin-riedl.de/redirect/latest/macos/${FF_ARCH}/release"
fetch_zip ffmpeg  "$FF_BASE/ffmpeg.zip"
fetch_zip ffprobe "$FF_BASE/ffprobe.zip"
# deno: runtime JavaScript que yt-dlp necesita para YouTube
fetch_zip deno "https://github.com/denoland/deno/releases/latest/download/deno-${DENO_ARCH}.zip"

# ── 3. Limpiar builds anteriores ─────────────────────────────────────────────
echo "▶ Limpiando builds anteriores..."
rm -rf build dist __pycache__

# ── 4. PyInstaller ────────────────────────────────────────────────────────────
echo "▶ Empaquetando con PyInstaller..."
pyinstaller xtuber.spec --noconfirm

# ── 5. Crear DMG (con acceso directo a Aplicaciones) ─────────────────────────
if [ ! -d "dist/Xtuber.app" ]; then
    echo "❌ Error: no se encontró Xtuber.app en dist/"
    exit 1
fi

echo "▶ Creando DMG..."
STAGE="$TMP/dmg"
mkdir -p "$STAGE"
cp -R "dist/Xtuber.app" "$STAGE/"
ln -s /Applications "$STAGE/Aplicaciones"
hdiutil create -volname "Xtuber" -srcfolder "$STAGE" -ov -format UDZO "$DMG" >/dev/null

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║  ✅  Build completado                        ║"
echo "╚══════════════════════════════════════════════╝"
echo "   dist/Xtuber.app"
echo "   $DMG ($(du -h "$DMG" | cut -f1))"
