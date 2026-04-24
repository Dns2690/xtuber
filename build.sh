#!/usr/bin/env bash
# ============================================================
#  build.sh — Build de Xtuber para macOS
#  Genera: dist/Xtuber.app  y  dist/Xtuber-mac.dmg
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║        Xtuber — Build para macOS             ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

# ── 1. Dependencias Python ───────────────────────────────────────────────────
echo "▶ Instalando dependencias Python..."
pip3 install -r requirements.txt --quiet

# ── 2. Descargar ffmpeg estático para Mac (arm64 + x86_64) ──────────────────
mkdir -p bin

if [ ! -f "bin/ffmpeg" ]; then
    echo "▶ Descargando ffmpeg para Mac..."
    # ffmpeg-builds provee binarios estáticos sin dependencias
    FFMPEG_URL="https://evermeet.cx/ffmpeg/getrelease/ffmpeg/zip"
    curl -L "$FFMPEG_URL" -o /tmp/ffmpeg_mac.zip
    unzip -o /tmp/ffmpeg_mac.zip -d /tmp/ffmpeg_mac
    mv /tmp/ffmpeg_mac/ffmpeg bin/ffmpeg
    chmod +x bin/ffmpeg
    rm -rf /tmp/ffmpeg_mac /tmp/ffmpeg_mac.zip
    echo "   ✓ ffmpeg descargado: $(bin/ffmpeg -version 2>&1 | head -1)"
else
    echo "   ✓ ffmpeg ya existe, omitiendo descarga."
fi

# ── 3. Limpiar builds anteriores ─────────────────────────────────────────────
echo "▶ Limpiando builds anteriores..."
rm -rf build dist __pycache__

# ── 4. PyInstaller ────────────────────────────────────────────────────────────
echo "▶ Empaquetando con PyInstaller..."
pyinstaller xtuber.spec --noconfirm

# ── 5. Crear DMG ──────────────────────────────────────────────────────────────
if [ -d "dist/Xtuber.app" ]; then
    echo "▶ Creando DMG..."
    hdiutil create \
        -volname "Xtuber" \
        -srcfolder "dist/Xtuber.app" \
        -ov \
        -format UDZO \
        "dist/Xtuber-mac.dmg"
    echo ""
    echo "╔══════════════════════════════════════════════╗"
    echo "║  ✅  Build completado                        ║"
    echo "║     dist/Xtuber.app                         ║"
    echo "║     dist/Xtuber-mac.dmg                     ║"
    echo "╚══════════════════════════════════════════════╝"
else
    echo "❌ Error: no se encontró Xtuber.app en dist/"
    exit 1
fi
