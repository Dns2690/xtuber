# Xtuber — Descargador de YouTube

Aplicación de escritorio para descargar videos de YouTube en MP4 o audio en MP3. **No requiere instalar nada**: Python, yt-dlp, ffmpeg y deno van incluidos dentro del ejecutable.

## Descargar

Ve a [**Releases**](../../releases) y descarga el archivo de tu equipo:

| Plataforma | Archivo |
|---|---|
| 🍎 Mac con Apple Silicon (M1/M2/M3/M4) | `Xtuber-mac-arm64.dmg` |
| 🍎 Mac con Intel | `Xtuber-mac-x86_64.dmg` |
| 🪟 Windows | `Xtuber-windows.exe` |

**Mac:** abre el `.dmg` y arrastra `Xtuber.app` a Aplicaciones. Como la app no está notarizada por Apple, la primera vez macOS la bloquea: ve a *Ajustes del Sistema → Privacidad y seguridad* y pulsa **"Abrir igualmente"**.

**Windows:** ejecuta el `.exe`. Si SmartScreen avisa, pulsa *Más información → Ejecutar de todas formas*.

## Funciones

- Lista las resoluciones reales del video (hasta 4K/8K) y audio MP3.
- Prefiere H.264 + AAC, así el MP4 se reproduce en QuickTime, Windows y móviles.
- Barra de progreso con velocidad y tiempo restante; botón para cancelar.
- Carpeta de destino configurable y botón "Mostrar archivo".
- **yt-dlp se actualiza solo**: al iniciar busca la última versión oficial, la verifica (SHA-256) y la usa en el siguiente arranque. Así la app sigue funcionando cuando YouTube cambia.
- Aviso de nuevas versiones de Xtuber.

## Desarrollo

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python xtuber.py
```

En modo desarrollo usa el `ffmpeg` del sistema y `deno`, `node` o `bun` si están instalados (`brew install ffmpeg deno`). Sin un runtime JavaScript, YouTube entrega muy pocos formatos.

### Build local

```bash
bash build.sh            # Mac → dist/Xtuber.app y dist/Xtuber-mac-<arch>.dmg
```
```bat
build_windows.bat        :: Windows → dist\Xtuber.exe
```

Los scripts descargan ffmpeg, ffprobe y deno nativos para la arquitectura del equipo y empaquetan el yt-dlp más reciente.

### Publicar una versión

```bash
# 1. Cambiar VERSION en xtuber.py (ej: "1.2.0") — el spec la toma de ahí
git commit -am "release: v1.2.0"
git tag v1.2.0
git push origin main --tags
```

GitHub Actions compila Mac (Apple Silicon e Intel) y Windows y publica el Release.
