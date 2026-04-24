# Xtuber — Descargador de YouTube

Aplicación de escritorio para descargar videos de YouTube. **No requiere instalar nada** — Python, yt-dlp y ffmpeg están incluidos dentro del ejecutable.

---

## Descargar

Ve a la sección [**Releases**](../../releases) y descarga el archivo de tu plataforma:

| Plataforma | Archivo | Instalación |
|---|---|---|
| 🍎 **macOS** | `Xtuber-mac.dmg` | Abre el DMG y arrastra a Aplicaciones |
| 🪟 **Windows** | `Xtuber-windows.exe` | Doble clic y listo |

---

## Actualizaciones automáticas

Xtuber verifica al iniciar si hay una versión nueva disponible y muestra una notificación con el enlace de descarga.

---

## Desarrollo

### Requisitos
```bash
pip install -r requirements.txt
```

### Correr en modo desarrollo
```bash
python3 xtuber.py
```

### Build local (Mac)
```bash
bash build.sh
# Genera: dist/Xtuber.app  y  dist/Xtuber-mac.dmg
```

### Build local (Windows)
```bat
build_windows.bat
:: Genera: dist\Xtuber.exe
```

### Publicar una nueva versión (GitHub Actions)

Los builds se generan **automáticamente** en Mac y Windows al hacer push de un tag:

```bash
# 1. Editar VERSION en xtuber.py (ej: "1.1.0")
# 2. Commit y tag
git add .
git commit -m "release: v1.1.0"
git tag v1.1.0
git push origin main --tags
```

GitHub Actions compilará ambas plataformas y publicará el Release automáticamente.

---

## Configuración del auto-updater

Edita las siguientes líneas en `xtuber.py` para apuntar a tu repositorio:

```python
VERSION     = "1.0.0"        # ← Versión actual
GITHUB_REPO = "TU_USUARIO/xtuber"  # ← Tu usuario y repo de GitHub
```
