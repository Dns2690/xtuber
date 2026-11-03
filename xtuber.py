#!/usr/bin/env python3
"""
Xtuber — Descargador de YouTube con interfaz gráfica
https://github.com/Dns2690/xtuber
"""

import glob
import hashlib
import json
import os
import queue
import re
import shutil
import ssl
import subprocess
import sys
import tempfile
import threading
import urllib.request
import webbrowser
import zipfile
from tkinter import filedialog

import customtkinter as ctk

# ── Versión ──────────────────────────────────────────────────────────────────
VERSION = "1.1.0"
GITHUB_REPO = "Dns2690/xtuber"
YTDLP_REPO = "yt-dlp/yt-dlp"

IS_MAC = sys.platform == "darwin"
IS_WIN = sys.platform == "win32"

# ── Tema ─────────────────────────────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

# ── Colores ──────────────────────────────────────────────────────────────────
BG       = "#0f0f0f"
SURFACE  = "#1a1a1a"
SURFACE2 = "#242424"
BORDER   = "#2e2e2e"
ACCENT   = "#ff4444"
ACCENT2  = "#cc3333"
TEXT     = "#f0f0f0"
MUTED    = "#8a8a8a"
SUCCESS  = "#3ecf8e"
WARNING  = "#f0a500"
UPDATE   = "#7c6af7"

FONT = "Courier New"


# ══════════════════════════════════════════════════════════════════════════════
#  Rutas y herramientas externas
# ══════════════════════════════════════════════════════════════════════════════

def resource_dir():
    """Carpeta con los recursos del ejecutable (o del script en desarrollo)."""
    if getattr(sys, "frozen", False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


def data_dir():
    """Carpeta de datos del usuario (ajustes y yt-dlp actualizado)."""
    if IS_MAC:
        base = os.path.expanduser("~/Library/Application Support")
    elif IS_WIN:
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
    else:
        base = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    path = os.path.join(base, "Xtuber")
    os.makedirs(path, exist_ok=True)
    return path


# Las apps abiertas desde Finder no heredan el PATH de la terminal.
_EXTRA_PATHS = ["/opt/homebrew/bin", "/usr/local/bin", os.path.expanduser("~/.deno/bin")]


def find_tool(name):
    """Busca un binario: primero el incluido en la app, luego el del sistema."""
    exe = name + ".exe" if IS_WIN else name
    bundled = os.path.join(resource_dir(), "bin", exe)
    if os.path.isfile(bundled):
        return bundled
    found = shutil.which(exe)
    if found:
        return found
    for d in _EXTRA_PATHS:
        candidate = os.path.join(d, exe)
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return None


def ffmpeg_dir():
    """Directorio con ffmpeg (y ffprobe), o None si no hay ffmpeg."""
    ffmpeg = find_tool("ffmpeg")
    return os.path.dirname(ffmpeg) if ffmpeg else None


def js_runtimes():
    """
    YouTube exige resolver un reto JavaScript para entregar los formatos.
    Devuelve la configuración de runtime para yt-dlp (deno preferido).
    """
    for name in ("deno", "node", "bun"):
        path = find_tool(name)
        if path:
            return name, {name: {"path": path}}
    return None, None


def default_output_dir():
    home = os.path.expanduser("~")
    for name in ("Downloads", "Descargas", "Desktop", "Escritorio"):
        path = os.path.join(home, name)
        if os.path.isdir(path):
            return path
    return home


def reveal_in_file_manager(path):
    try:
        if IS_MAC:
            subprocess.Popen(["open", "-R", path])
        elif IS_WIN:
            subprocess.Popen(["explorer", "/select,", os.path.normpath(path)])
        else:
            subprocess.Popen(["xdg-open", os.path.dirname(path)])
    except OSError:
        pass


# ══════════════════════════════════════════════════════════════════════════════
#  Ajustes persistentes
# ══════════════════════════════════════════════════════════════════════════════

def _settings_path():
    return os.path.join(data_dir(), "settings.json")


def load_settings():
    try:
        with open(_settings_path(), encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def save_settings(settings):
    try:
        with open(_settings_path(), "w", encoding="utf-8") as fh:
            json.dump(settings, fh, indent=2)
    except OSError:
        pass


# ══════════════════════════════════════════════════════════════════════════════
#  Red
# ══════════════════════════════════════════════════════════════════════════════

def _ssl_context():
    # Sin certifi, Python en macOS no confía en ninguna CA y todo HTTPS falla.
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def http_get(url, timeout=15):
    req = urllib.request.Request(url, headers={"User-Agent": f"Xtuber/{VERSION}"})
    with urllib.request.urlopen(req, timeout=timeout, context=_ssl_context()) as resp:
        return resp.read()


def parse_version(text):
    """'v1.10.0' → (1, 10, 0). Permite comparar versiones numéricamente."""
    return tuple(int(n) for n in re.findall(r"\d+", text or ""))


# ══════════════════════════════════════════════════════════════════════════════
#  yt-dlp: carga y auto-actualización
#
#  YouTube cambia con frecuencia y un yt-dlp viejo deja de funcionar. Como el
#  ejecutable no puede reinstalar paquetes, la app descarga la versión oficial
#  de yt-dlp (un .zip importable) a la carpeta de datos y la usa en el
#  siguiente arranque. Si esa versión falla al cargar, vuelve a la incluida.
# ══════════════════════════════════════════════════════════════════════════════

def _bundled_ytdlp_version():
    try:
        from importlib.metadata import version
        return version("yt-dlp")
    except Exception:
        return "0"


def _updated_ytdlp_zips():
    """Zips descargados, del más nuevo al más viejo."""
    zips = glob.glob(os.path.join(data_dir(), "yt-dlp-*.zip"))
    return sorted(zips, key=lambda p: parse_version(os.path.basename(p)), reverse=True)


def _purge_ytdlp_modules():
    for name in [m for m in sys.modules if m == "yt_dlp" or m.startswith("yt_dlp.")]:
        del sys.modules[name]


def load_yt_dlp():
    """Importa yt-dlp usando la versión más nueva disponible que funcione."""
    bundled = parse_version(_bundled_ytdlp_version())
    for path in _updated_ytdlp_zips():
        if parse_version(os.path.basename(path)) <= bundled:
            continue
        sys.path.insert(0, path)
        try:
            import yt_dlp
            import yt_dlp.extractor.youtube  # noqa: F401  valida la carga completa
            import yt_dlp.postprocessor      # noqa: F401
            # Un zip inválido se ignora en silencio y Python carga el incluido
            if not os.path.abspath(yt_dlp.__file__).startswith(os.path.abspath(path)):
                raise ImportError("el zip no contiene un yt-dlp válido")
            return yt_dlp
        except Exception:
            sys.path.remove(path)
            _purge_ytdlp_modules()
            try:
                os.remove(path)
            except OSError:
                pass
    import yt_dlp
    return yt_dlp


def fetch_ytdlp_update(current_version):
    """
    Descarga la última versión de yt-dlp si es más nueva que la actual.
    Verifica el SHA-256 publicado. Devuelve la versión descargada o None.
    """
    data = json.loads(http_get(f"https://api.github.com/repos/{YTDLP_REPO}/releases/latest"))
    tag = data.get("tag_name", "")
    if not tag or parse_version(tag) <= parse_version(current_version):
        return None

    target = os.path.join(data_dir(), f"yt-dlp-{tag}.zip")
    if os.path.isfile(target):
        return tag

    assets = {a["name"]: a["browser_download_url"] for a in data.get("assets", [])}
    if "yt-dlp" not in assets or "SHA2-256SUMS" not in assets:
        return None

    sums = http_get(assets["SHA2-256SUMS"]).decode()
    expected = next(
        (line.split()[0] for line in sums.splitlines()
         if len(line.split()) == 2 and line.split()[1] == "yt-dlp"),
        None,
    )
    payload = http_get(assets["yt-dlp"], timeout=120)
    if not expected or hashlib.sha256(payload).hexdigest() != expected:
        return None

    fd, tmp = tempfile.mkstemp(dir=data_dir(), suffix=".tmp")
    with os.fdopen(fd, "wb") as fh:
        fh.write(payload)
    try:
        with zipfile.ZipFile(tmp) as zf:
            if "yt_dlp/__init__.py" not in zf.namelist():
                raise zipfile.BadZipFile("no contiene yt_dlp")
    except zipfile.BadZipFile:
        os.remove(tmp)
        return None
    os.replace(tmp, target)

    # Conservar solo la versión recién descargada
    for old in _updated_ytdlp_zips():
        if old != target:
            try:
                os.remove(old)
            except OSError:
                pass
    return tag


# ══════════════════════════════════════════════════════════════════════════════
#  Formatos
# ══════════════════════════════════════════════════════════════════════════════

AUDIO_FMT = "bestaudio/best"

# Ante igual resolución, preferir H.264 + AAC: el MP4 resultante se reproduce
# en QuickTime, Windows y móviles sin códecs extra.
FORMAT_SORT = ["res", "fps", "vcodec:h264", "acodec:aac"]


def build_presets(info):
    """Lista de (etiqueta, formato) según las resoluciones reales del video."""
    heights = sorted(
        {
            f["height"]
            for f in info.get("formats") or []
            if f.get("height") and f.get("vcodec") not in (None, "none")
        },
        reverse=True,
    )
    names = {4320: "8K", 2160: "4K", 1440: "2K", 1080: "Full HD", 720: "HD"}

    presets = []
    if heights:
        presets.append((f"Mejor calidad   ({heights[0]}p)", "bv*+ba/b"))
        for h in heights[1:]:
            if h < 240:
                continue
            tag = names.get(h, "")
            presets.append((f"{h}p {tag:<10}  (MP4)", f"bv*[height<={h}]+ba/b[height<={h}]"))
    else:
        presets.append(("Mejor calidad", "bv*+ba/b"))
    presets.append(("Solo audio      (MP3 192 kbps)", AUDIO_FMT))
    return presets


def human_size(num):
    if not num:
        return "?"
    for unit in ("B", "KB", "MB", "GB"):
        if num < 1024:
            return f"{num:.1f} {unit}"
        num /= 1024
    return f"{num:.1f} TB"


def human_eta(seconds):
    if seconds is None:
        return "--:--"
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


_ANSI = re.compile(r"\x1b\[[0-9;]*m")


def friendly_error(err):
    """Convierte errores de yt-dlp en mensajes comprensibles."""
    msg = _ANSI.sub("", str(err)).strip()
    msg = re.sub(r"^ERROR:\s*", "", msg)
    msg = re.sub(r"^\[[\w:]+\]\s*[\w-]+:\s*", "", msg)
    low = msg.lower()
    if "sign in to confirm" in low or "not a bot" in low:
        return "YouTube pide verificación anti-bots. Espera unos minutos o prueba otra red."
    if "private video" in low:
        return "El video es privado."
    if "unavailable" in low or "not available" in low:
        return "El video no está disponible (eliminado, privado o bloqueado en tu país)."
    if "age" in low and ("restricted" in low or "confirm your age" in low):
        return "El video tiene restricción de edad y requiere iniciar sesión."
    if "is not a valid url" in low or "unsupported url" in low:
        return "La URL no es válida o el sitio no está soportado."
    if "ffmpeg" in low and "not" in low:
        return "No se encontró ffmpeg; es necesario para unir video y audio."
    if "urlopen error" in low or "getaddrinfo" in low or "timed out" in low:
        return "Sin conexión a internet o el servidor no responde."
    return msg[:300]


class _YdlLogger:
    """
    Logger silencioso para yt-dlp. Evita que escriba en stdout, que no existe
    en el ejecutable de Windows sin consola (y haría fallar la descarga).
    """

    def __init__(self):
        self.warnings = []

    def debug(self, msg):
        pass

    def info(self, msg):
        pass

    def warning(self, msg):
        self.warnings.append(msg)

    def error(self, msg):
        pass


class DownloadCancelled(Exception):
    pass


# ══════════════════════════════════════════════════════════════════════════════
#  App
# ══════════════════════════════════════════════════════════════════════════════

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Xtuber")
        self.geometry("580x800")
        self.minsize(560, 760)
        self.configure(fg_color=BG)

        self.settings      = load_settings()
        self.output_dir    = self.settings.get("output_dir") or default_output_dir()
        if not os.path.isdir(self.output_dir):
            self.output_dir = default_output_dir()

        self.yt_dlp        = None
        self.selected_fmt  = ctk.StringVar(value="")
        self.busy          = False
        self.analyzed_url  = None
        self.last_file     = None
        self._cancel       = threading.Event()
        self._ui_queue     = queue.Queue()

        self._build_ui()
        self.after(50, self._drain_ui_queue)
        self.after(100, self._startup)

    # ── Comunicación segura entre hilos ──────────────────────────────────────

    def _ui(self, fn, *args):
        """Programa fn(*args) en el hilo de la interfaz (seguro desde cualquier hilo)."""
        self._ui_queue.put((fn, args))

    def _drain_ui_queue(self):
        try:
            while True:
                fn, args = self._ui_queue.get_nowait()
                fn(*args)
        except queue.Empty:
            pass
        self.after(50, self._drain_ui_queue)

    # ── Arranque ─────────────────────────────────────────────────────────────

    def _startup(self):
        try:
            self.yt_dlp = load_yt_dlp()
        except ImportError:
            self._set_status("yt-dlp no encontrado. Ejecuta: pip install 'yt-dlp[default]'", "error")
            self.btn_fetch.configure(state="disabled")
            return

        self._refresh_footer()
        if not ffmpeg_dir():
            self._set_status("ffmpeg no encontrado: solo habrá calidades limitadas.", "warning")

        threading.Thread(target=self._background_updates, daemon=True).start()

    def _background_updates(self):
        # 1. Nueva versión de Xtuber
        try:
            data = json.loads(http_get(
                f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest", timeout=8))
            latest = data.get("tag_name", "")
            if parse_version(latest) > parse_version(VERSION):
                self._ui(self._show_update_banner, latest.lstrip("v"), data.get("html_url", ""))
        except Exception:
            pass
        # 2. Nueva versión de yt-dlp (se aplica en el próximo arranque)
        try:
            tag = fetch_ytdlp_update(self.yt_dlp.version.__version__)
            if tag:
                self._ui(self._refresh_footer, tag)
        except Exception:
            pass

    # ── UI ───────────────────────────────────────────────────────────────────

    def _build_ui(self):
        # Banner de actualización (oculto hasta que haya update)
        self._update_frame = ctk.CTkFrame(self, fg_color="#1c1a2e", corner_radius=0, height=0)
        self._update_frame.pack(fill="x")
        self._update_frame.pack_propagate(False)

        # Header
        header = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=0, height=64)
        header.pack(fill="x")
        header.pack_propagate(False)
        ctk.CTkLabel(header, text="●", font=(FONT, 18), text_color=ACCENT).pack(side="left", padx=(20, 8))
        ctk.CTkLabel(header, text="Xtuber", font=(FONT, 20, "bold"), text_color=TEXT).pack(side="left")
        ctk.CTkLabel(header, text="descargador de youtube", font=(FONT, 11),
                     text_color=MUTED).pack(side="left", padx=(10, 0), pady=(6, 0))
        ctk.CTkLabel(header, text=f"v{VERSION}", font=(FONT, 10),
                     text_color=MUTED).pack(side="right", padx=16)

        # Footer (se empaqueta antes del contenido para que siempre quede visible)
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(side="bottom", fill="x", padx=24, pady=(0, 10))
        self.lbl_status = ctk.CTkLabel(footer, text="", font=(FONT, 11), text_color=MUTED,
                                       anchor="w", justify="left", wraplength=520)
        self.lbl_status.pack(fill="x")
        self.lbl_engine = ctk.CTkLabel(footer, text="", font=(FONT, 9), text_color="#555555", anchor="w")
        self.lbl_engine.pack(fill="x")

        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=24, pady=(18, 8))

        # URL
        self._label(main, "URL del video")
        url_row = ctk.CTkFrame(main, fg_color="transparent")
        url_row.pack(fill="x", pady=(4, 0))
        self.entry_url = ctk.CTkEntry(
            url_row, placeholder_text="https://www.youtube.com/watch?v=...",
            font=(FONT, 12), fg_color=SURFACE, border_color=BORDER, border_width=1,
            text_color=TEXT, placeholder_text_color=MUTED, corner_radius=6, height=40,
        )
        self.entry_url.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.entry_url.bind("<Return>", lambda _e: self._on_fetch())
        self.btn_fetch = ctk.CTkButton(
            url_row, text="Analizar", font=(FONT, 12, "bold"), fg_color=ACCENT,
            hover_color=ACCENT2, text_color="#ffffff", corner_radius=6, height=40, width=90,
            command=self._on_fetch,
        )
        self.btn_fetch.pack(side="left")

        # Info del video
        frame_info = ctk.CTkFrame(main, fg_color=SURFACE2, corner_radius=8)
        frame_info.pack(fill="x", pady=(14, 0))
        self.lbl_title = ctk.CTkLabel(frame_info, text="—", font=(FONT, 12, "bold"), text_color=TEXT,
                                      anchor="w", justify="left", wraplength=500)
        self.lbl_title.pack(fill="x", padx=14, pady=(12, 2))
        self.lbl_meta = ctk.CTkLabel(frame_info, text="", font=(FONT, 11), text_color=MUTED, anchor="w")
        self.lbl_meta.pack(fill="x", padx=14, pady=(0, 12))

        # Calidades
        self._label(main, "Calidad", pady=(18, 4))
        self.frame_formats = ctk.CTkScrollableFrame(
            main, fg_color=SURFACE, corner_radius=8, border_width=1, border_color=BORDER,
            height=170, scrollbar_button_color=BORDER, scrollbar_button_hover_color=ACCENT,
        )
        self.frame_formats.pack(fill="x")
        self._placeholder_formats()

        # Carpeta de destino
        self._label(main, "Guardar en", pady=(18, 4))
        dir_row = ctk.CTkFrame(main, fg_color=SURFACE, corner_radius=6, border_width=1, border_color=BORDER)
        dir_row.pack(fill="x")
        self.lbl_dir = ctk.CTkLabel(dir_row, text="", font=(FONT, 11), text_color=TEXT, anchor="w")
        self.lbl_dir.pack(side="left", fill="x", expand=True, padx=12, pady=6)
        self.btn_dir = ctk.CTkButton(
            dir_row, text="Cambiar", font=(FONT, 11, "bold"), fg_color=SURFACE2, hover_color=BORDER,
            text_color=TEXT, corner_radius=6, height=28, width=80, command=self._choose_dir,
        )
        self.btn_dir.pack(side="right", padx=6, pady=6)
        self._refresh_dir_label()

        # Progreso
        self._label(main, "Progreso", pady=(18, 4))
        self.progress_bar = ctk.CTkProgressBar(main, fg_color=SURFACE2, progress_color=ACCENT,
                                               corner_radius=4, height=6)
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x")
        self.lbl_progress = ctk.CTkLabel(main, text="En espera", font=(FONT, 11),
                                         text_color=MUTED, anchor="w")
        self.lbl_progress.pack(fill="x", pady=(4, 0))

        # Botones de acción
        actions = ctk.CTkFrame(main, fg_color="transparent")
        actions.pack(fill="x", pady=(16, 0))
        self.btn_download = ctk.CTkButton(
            actions, text="Descargar", font=(FONT, 13, "bold"), fg_color=ACCENT, hover_color=ACCENT2,
            text_color="#ffffff", corner_radius=6, height=44, state="disabled",
            command=self._on_download_or_cancel,
        )
        self.btn_download.pack(side="left", fill="x", expand=True)
        self.btn_open = ctk.CTkButton(
            actions, text="Mostrar archivo", font=(FONT, 12, "bold"), fg_color=SURFACE2,
            hover_color=BORDER, text_color=TEXT, corner_radius=6, height=44, width=150,
            command=lambda: self.last_file and reveal_in_file_manager(self.last_file),
        )
        # Se muestra solo después de una descarga exitosa

    def _label(self, parent, text, pady=(0, 0)):
        ctk.CTkLabel(parent, text=text.upper(), font=(FONT, 10, "bold"),
                     text_color=MUTED, anchor="w").pack(fill="x", pady=pady)

    def _placeholder_formats(self, text="Ingresa una URL y presiona Analizar"):
        for w in self.frame_formats.winfo_children():
            w.destroy()
        ctk.CTkLabel(self.frame_formats, text=text, font=(FONT, 12), text_color=MUTED).pack(pady=20)

    def _refresh_dir_label(self):
        path = self.output_dir
        home = os.path.expanduser("~")
        if path.startswith(home):
            path = "~" + path[len(home):]
        if len(path) > 52:
            path = "…" + path[-51:]
        self.lbl_dir.configure(text=path)

    def _refresh_footer(self, pending_update=None):
        if not self.yt_dlp:
            return
        parts = [f"yt-dlp {self.yt_dlp.version.__version__}"]
        parts.append("ffmpeg ✓" if ffmpeg_dir() else "ffmpeg ✗")
        runtime, _ = js_runtimes()
        parts.append(f"js {runtime} ✓" if runtime else "js ✗")
        if pending_update:
            parts.append(f"yt-dlp {pending_update} listo (se aplica al reiniciar)")
        self.lbl_engine.configure(text="  ·  ".join(parts))

    def _choose_dir(self):
        chosen = filedialog.askdirectory(initialdir=self.output_dir, title="Carpeta de descargas")
        if chosen:
            self.output_dir = chosen
            self.settings["output_dir"] = chosen
            save_settings(self.settings)
            self._refresh_dir_label()

    # ── Auto-update de la app ────────────────────────────────────────────────

    def _show_update_banner(self, tag, url):
        for w in self._update_frame.winfo_children():
            w.destroy()
        self._update_frame.configure(height=44)
        ctk.CTkLabel(self._update_frame, text=f"⬆  Nueva versión disponible: v{tag}",
                     font=(FONT, 11, "bold"), text_color="#a89ef7").pack(side="left", padx=16)
        ctk.CTkButton(
            self._update_frame, text="Descargar actualización", font=(FONT, 11, "bold"),
            fg_color=UPDATE, hover_color="#5a4fd1", text_color="#ffffff", corner_radius=6,
            height=28, width=190, command=lambda: webbrowser.open(url),
        ).pack(side="right", padx=16, pady=8)

    # ── Opciones comunes de yt-dlp ───────────────────────────────────────────

    def _base_opts(self, logger):
        opts = {
            "logger":            logger,
            "quiet":             True,
            "no_warnings":       True,
            "noprogress":        True,
            "noplaylist":        True,   # una URL con &list= descarga solo ese video
            "remote_components": ["ejs:github"],
        }
        _, runtimes = js_runtimes()
        if runtimes:
            opts["js_runtimes"] = runtimes
        ff = ffmpeg_dir()
        if ff:
            opts["ffmpeg_location"] = ff
        return opts

    def _set_busy(self, busy):
        self.busy = busy
        state = "disabled" if busy else "normal"
        self.btn_fetch.configure(state=state)
        self.btn_dir.configure(state=state)
        self.entry_url.configure(state=state)

    # ── Analizar ─────────────────────────────────────────────────────────────

    def _on_fetch(self):
        if self.busy or not self.yt_dlp:
            return
        url = self.entry_url.get().strip()
        if not url:
            self._set_status("Pega una URL primero.", "warning")
            return

        self._set_busy(True)
        self.btn_fetch.configure(text="...")
        self.btn_download.configure(state="disabled")
        self.btn_open.pack_forget()
        self.analyzed_url = None
        self._set_status("Obteniendo información del video...", "info")
        self._placeholder_formats("Analizando...")
        self.lbl_title.configure(text="—")
        self.lbl_meta.configure(text="")
        self.progress_bar.set(0)
        self.lbl_progress.configure(text="En espera", text_color=MUTED)

        threading.Thread(target=self._fetch_thread, args=(url,), daemon=True).start()

    def _fetch_thread(self, url):
        try:
            with self.yt_dlp.YoutubeDL(self._base_opts(_YdlLogger())) as ydl:
                info = ydl.extract_info(url, download=False)
            if info.get("_type") == "playlist":
                raise ValueError("Es una lista de reproducción; pega el enlace de un video.")
            if info.get("is_live"):
                raise ValueError("Las transmisiones en vivo no se pueden descargar.")
            self._ui(self._after_fetch_ok, url, info)
        except Exception as e:  # noqa: BLE001
            self._ui(self._after_fetch_error, friendly_error(e))

    def _after_fetch_ok(self, url, info):
        self.analyzed_url = url
        title = info.get("title") or "Sin título"
        meta = [f"Duración: {info.get('duration_string') or '?'}"]
        if info.get("uploader"):
            meta.append(info["uploader"])
        self.lbl_title.configure(text=title)
        self.lbl_meta.configure(text="  ·  ".join(meta))

        presets = build_presets(info)
        for w in self.frame_formats.winfo_children():
            w.destroy()
        self.selected_fmt.set(presets[0][1])
        for label, fmt in presets:
            ctk.CTkRadioButton(
                self.frame_formats, text=label, variable=self.selected_fmt, value=fmt,
                font=(FONT, 12), text_color=TEXT, fg_color=ACCENT, hover_color=ACCENT2,
                border_color=BORDER,
            ).pack(anchor="w", padx=8, pady=5)

        self._set_busy(False)
        self.btn_fetch.configure(text="Analizar")
        self.btn_download.configure(state="normal")
        self._set_status("Listo. Elige una calidad y descarga.", "success")

    def _after_fetch_error(self, msg):
        self._set_busy(False)
        self.btn_fetch.configure(text="Analizar")
        self._placeholder_formats()
        self._set_status(f"Error: {msg}", "error")

    # ── Descargar ────────────────────────────────────────────────────────────

    def _on_download_or_cancel(self):
        if self.busy:
            self._cancel.set()
            self.btn_download.configure(state="disabled", text="Cancelando...")
            return

        fmt = self.selected_fmt.get()
        url = self.entry_url.get().strip()
        if not fmt or not url:
            self._set_status("Analiza una URL y selecciona una calidad.", "warning")
            return
        if url != self.analyzed_url:
            self._set_status("La URL cambió: presiona Analizar de nuevo.", "warning")
            return
        if not os.path.isdir(self.output_dir) or not os.access(self.output_dir, os.W_OK):
            self._set_status("No se puede escribir en la carpeta de destino. Elige otra.", "error")
            return

        self._cancel.clear()
        self._set_busy(True)
        self.btn_open.pack_forget()
        self.btn_download.configure(text="Cancelar", fg_color=SURFACE2, hover_color=BORDER)
        self.progress_bar.set(0)
        self.lbl_progress.configure(text="Iniciando...", text_color=MUTED)
        self._set_status("Descargando...", "info")

        threading.Thread(target=self._download_thread, args=(url, fmt, self.output_dir),
                         daemon=True).start()

    def _download_thread(self, url, fmt, output_dir):
        partial_files = set()

        def progress_hook(d):
            if d.get("tmpfilename"):
                partial_files.add(d["tmpfilename"])
            if self._cancel.is_set():
                raise DownloadCancelled()
            if d["status"] == "downloading":
                done  = d.get("downloaded_bytes") or 0
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                pct   = min(done / total, 1.0) if total else 0.0
                kind  = "audio" if (d.get("info_dict") or {}).get("vcodec") == "none" else "video"
                speed = d.get("speed")
                label = (f"{kind}: {pct * 100:5.1f}%  ·  {human_size(done)} / {human_size(total)}"
                         f"  ·  {human_size(speed)}/s  ·  ETA {human_eta(d.get('eta'))}")
                self._ui(self._update_progress, pct, label)

        def pp_hook(d):
            if d["status"] != "started":
                return
            name = d.get("postprocessor", "")
            if name == "Merger":
                self._ui(self._update_progress, 1.0, "Uniendo video y audio...")
            elif name == "ExtractAudio":
                self._ui(self._update_progress, 1.0, "Convirtiendo a MP3...")

        logger = _YdlLogger()
        opts = self._base_opts(logger)
        opts.update({
            "format":              fmt,
            "format_sort":         FORMAT_SORT,
            # La resolución en el nombre evita que otra calidad del mismo
            # video se confunda con un archivo ya descargado.
            "outtmpl":             os.path.join(
                output_dir,
                "%(title).180B.%(ext)s" if fmt == AUDIO_FMT else "%(title).170B (%(height)sp).%(ext)s",
            ),
            "progress_hooks":      [progress_hook],
            "postprocessor_hooks": [pp_hook],
            "merge_output_format": "mp4",
            "overwrites":          False,
            "windowsfilenames":    True,
        })
        if fmt == AUDIO_FMT:
            opts["postprocessors"] = [{
                "key":              "FFmpegExtractAudio",
                "preferredcodec":   "mp3",
                "preferredquality": "192",
            }]

        try:
            with self.yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
            downloads = info.get("requested_downloads") or [{}]
            path = downloads[-1].get("filepath") or downloads[-1].get("_filename")
            self._ui(self._on_download_done, path)
        except Exception as e:  # noqa: BLE001
            if self._cancel.is_set() or isinstance(e, DownloadCancelled) or "DownloadCancelled" in repr(e):
                for tmp in partial_files:  # no dejar archivos .part a medias
                    for leftover in (tmp, tmp + ".ytdl"):
                        try:
                            os.remove(leftover)
                        except OSError:
                            pass
                self._ui(self._on_download_cancelled)
            else:
                self._ui(self._on_download_error, friendly_error(e))

    def _update_progress(self, pct, label):
        self.progress_bar.set(pct)
        self.lbl_progress.configure(text=label, text_color=TEXT)

    def _reset_download_button(self):
        self.btn_download.configure(state="normal", text="Descargar", fg_color=ACCENT, hover_color=ACCENT2)
        self._set_busy(False)

    def _on_download_done(self, path):
        self._reset_download_button()
        self.progress_bar.set(1.0)
        if path and os.path.isfile(path):
            self.last_file = path
            self.lbl_progress.configure(text=f"Guardado: {os.path.basename(path)}", text_color=SUCCESS)
            self.btn_open.pack(side="left", padx=(8, 0))
        else:
            self.lbl_progress.configure(text=f"Guardado en: {self.output_dir}", text_color=SUCCESS)
        self._set_status("¡Descarga completada!", "success")

    def _on_download_cancelled(self):
        self._reset_download_button()
        self.progress_bar.set(0)
        self.lbl_progress.configure(text="Descarga cancelada", text_color=WARNING)
        self._set_status("Descarga cancelada.", "warning")

    def _on_download_error(self, msg):
        self._reset_download_button()
        self.lbl_progress.configure(text="Error en la descarga", text_color=ACCENT)
        self._set_status(f"Error: {msg}", "error")

    def _set_status(self, msg, level="info"):
        colors = {"info": MUTED, "success": SUCCESS, "warning": WARNING, "error": ACCENT}
        self.lbl_status.configure(text=msg, text_color=colors.get(level, MUTED))


if __name__ == "__main__":
    App().mainloop()
