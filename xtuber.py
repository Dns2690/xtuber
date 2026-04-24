#!/usr/bin/env python3
"""
Xtuber.py — Descargador de YouTube con interfaz gráfica
https://github.com/TU_USUARIO/xtuber
"""

import os
import sys
import json
import threading
import urllib.request
import webbrowser
import customtkinter as ctk

# ── Versión ──────────────────────────────────────────────────────────────────
VERSION = "1.0.0"
GITHUB_REPO = "Dns2690/xtuber"

# ── Tema ─────────────────────────────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

# ── Colores ───────────────────────────────────────────────────────────────────
BG       = "#0f0f0f"
SURFACE  = "#1a1a1a"
SURFACE2 = "#242424"
BORDER   = "#2e2e2e"
ACCENT   = "#ff4444"
ACCENT2  = "#cc3333"
TEXT     = "#f0f0f0"
MUTED    = "#666666"
SUCCESS  = "#3ecf8e"
WARNING  = "#f0a500"
UPDATE   = "#7c6af7"   # Color para notificaciones de actualización


# ── Utilidades ────────────────────────────────────────────────────────────────

def get_ffmpeg_path():
    """
    Retorna la ruta al directorio que contiene el binario de ffmpeg.
    Prioridad: binario bundleado dentro del ejecutable → ffmpeg del sistema.
    """
    if getattr(sys, "frozen", False):
        # Corriendo como ejecutable PyInstaller
        base = sys._MEIPASS
        ffmpeg_name = "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"
        bundled = os.path.join(base, "bin", ffmpeg_name)
        if os.path.isfile(bundled):
            return os.path.dirname(bundled)
    # Fallback: ffmpeg del sistema (PATH)
    return None


def check_yt_dlp():
    try:
        import yt_dlp  # noqa: F401
        return True
    except ImportError:
        return False


def get_output_dir():
    home = os.path.expanduser("~")
    for name in ["Descargas", "Downloads", "Desktop"]:
        path = os.path.join(home, name)
        if os.path.isdir(path):
            return path
    return home


def check_for_updates(on_update_found):
    """
    Consulta la API de GitHub en background y llama on_update_found(tag, url)
    si hay una versión más nueva.
    """
    def _worker():
        try:
            api_url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
            req = urllib.request.Request(
                api_url, headers={"User-Agent": f"Xtuber/{VERSION}"}
            )
            with urllib.request.urlopen(req, timeout=6) as resp:
                data = json.loads(resp.read().decode())
            latest_tag = data.get("tag_name", "").lstrip("v")
            html_url   = data.get("html_url", "")
            if latest_tag and latest_tag > VERSION:
                on_update_found(latest_tag, html_url)
        except Exception:
            pass  # Sin internet o repo no configurado → silencioso

    threading.Thread(target=_worker, daemon=True).start()


# ── App ───────────────────────────────────────────────────────────────────────

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Xtuber")
        self.geometry("560x740")
        self.minsize(560, 700)
        self.resizable(True, True)
        self.configure(fg_color=BG)

        # Estado interno
        self.formats       = []
        self.selected_fmt  = ctk.StringVar(value="")
        self.is_loading    = False
        self._update_banner = None

        self._build_ui()

        if not check_yt_dlp():
            self._set_status(
                "yt-dlp no encontrado. Ejecuta: pip install yt-dlp",
                "error",
            )
            self.btn_fetch.configure(state="disabled")

        # Chequear actualizaciones en background al iniciar
        check_for_updates(self._on_update_found)

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        # ── Banner de actualización (oculto hasta que haya update) ───────────
        self._update_frame = ctk.CTkFrame(
            self, fg_color="#1c1a2e", corner_radius=0, height=0
        )
        self._update_frame.pack(fill="x")
        self._update_frame.pack_propagate(False)

        # ── Header ───────────────────────────────────────────────────────────
        header = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=0, height=64)
        header.pack(fill="x")
        header.pack_propagate(False)

        dot = ctk.CTkLabel(
            header, text="●", font=("Courier", 18), text_color=ACCENT
        )
        dot.pack(side="left", padx=(20, 8))

        ctk.CTkLabel(
            header,
            text="Xtuber",
            font=("Courier New", 20, "bold"),
            text_color=TEXT,
        ).pack(side="left")

        ctk.CTkLabel(
            header,
            text="descargador de youtube",
            font=("Courier New", 11),
            text_color=MUTED,
        ).pack(side="left", padx=(10, 0), pady=(6, 0))

        ctk.CTkLabel(
            header,
            text=f"v{VERSION}",
            font=("Courier New", 10),
            text_color=MUTED,
        ).pack(side="right", padx=16)

        # ── Contenido principal ───────────────────────────────────────────────
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=24, pady=20)

        # URL
        self._label(main, "URL del video")
        url_row = ctk.CTkFrame(main, fg_color="transparent")
        url_row.pack(fill="x", pady=(4, 0))

        self.entry_url = ctk.CTkEntry(
            url_row,
            placeholder_text="https://www.youtube.com/watch?v=...",
            font=("Courier New", 12),
            fg_color=SURFACE,
            border_color=BORDER,
            border_width=1,
            text_color=TEXT,
            placeholder_text_color=MUTED,
            corner_radius=6,
            height=40,
        )
        self.entry_url.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.btn_fetch = ctk.CTkButton(
            url_row,
            text="Analizar",
            font=("Courier New", 12, "bold"),
            fg_color=ACCENT,
            hover_color=ACCENT2,
            text_color="#ffffff",
            corner_radius=6,
            height=40,
            width=90,
            command=self._on_fetch,
        )
        self.btn_fetch.pack(side="left")

        # Info del video
        self.frame_info = ctk.CTkFrame(main, fg_color=SURFACE2, corner_radius=8)
        self.frame_info.pack(fill="x", pady=(16, 0))

        self.lbl_title = ctk.CTkLabel(
            self.frame_info,
            text="—",
            font=("Courier New", 12, "bold"),
            text_color=TEXT,
            anchor="w",
            wraplength=480,
        )
        self.lbl_title.pack(fill="x", padx=14, pady=(12, 2))

        self.lbl_duration = ctk.CTkLabel(
            self.frame_info,
            text="",
            font=("Courier New", 11),
            text_color=MUTED,
            anchor="w",
        )
        self.lbl_duration.pack(fill="x", padx=14, pady=(0, 12))

        # Calidades
        self._label(main, "Calidad", pady=(20, 4))

        self.frame_formats = ctk.CTkScrollableFrame(
            main,
            fg_color=SURFACE,
            corner_radius=8,
            border_width=1,
            border_color=BORDER,
            height=160,
            scrollbar_button_color=BORDER,
            scrollbar_button_hover_color=ACCENT,
        )
        self.frame_formats.pack(fill="x")

        self._placeholder_formats()

        # Barra de progreso
        self._label(main, "Progreso", pady=(20, 4))

        self.progress_bar = ctk.CTkProgressBar(
            main,
            fg_color=SURFACE2,
            progress_color=ACCENT,
            corner_radius=4,
            height=6,
        )
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x")

        self.lbl_progress = ctk.CTkLabel(
            main,
            text="En espera",
            font=("Courier New", 11),
            text_color=MUTED,
            anchor="w",
        )
        self.lbl_progress.pack(fill="x", pady=(4, 0))

        # Botón descargar
        self.btn_download = ctk.CTkButton(
            main,
            text="Descargar",
            font=("Courier New", 13, "bold"),
            fg_color=ACCENT,
            hover_color=ACCENT2,
            text_color="#ffffff",
            corner_radius=6,
            height=44,
            state="disabled",
            command=self._on_download,
        )
        self.btn_download.pack(fill="x", pady=(20, 0))

        # Status bar
        self.lbl_status = ctk.CTkLabel(
            self,
            text="",
            font=("Courier New", 11),
            text_color=MUTED,
            anchor="w",
        )
        self.lbl_status.pack(fill="x", padx=24, pady=(4, 12))

    def _label(self, parent, text, pady=(0, 0)):
        ctk.CTkLabel(
            parent,
            text=text.upper(),
            font=("Courier New", 10, "bold"),
            text_color=MUTED,
            anchor="w",
        ).pack(fill="x", pady=pady)

    def _placeholder_formats(self):
        for w in self.frame_formats.winfo_children():
            w.destroy()
        ctk.CTkLabel(
            self.frame_formats,
            text="Ingresa una URL y presiona Analizar",
            font=("Courier New", 12),
            text_color=MUTED,
        ).pack(pady=20)

    # ── Auto-update UI ────────────────────────────────────────────────────────

    def _on_update_found(self, latest_tag, download_url):
        """Llamado desde el thread de check_for_updates cuando hay update."""
        self.after(0, lambda: self._show_update_banner(latest_tag, download_url))

    def _show_update_banner(self, tag, url):
        """Muestra el banner de actualización en el hilo de la UI."""
        # Limpiar el frame y darle altura
        for w in self._update_frame.winfo_children():
            w.destroy()
        self._update_frame.configure(height=44)

        ctk.CTkLabel(
            self._update_frame,
            text=f"⬆  Nueva versión disponible: v{tag}",
            font=("Courier New", 11, "bold"),
            text_color="#a89ef7",
        ).pack(side="left", padx=16)

        ctk.CTkButton(
            self._update_frame,
            text="Descargar actualización",
            font=("Courier New", 11, "bold"),
            fg_color=UPDATE,
            hover_color="#5a4fd1",
            text_color="#ffffff",
            corner_radius=6,
            height=28,
            width=190,
            command=lambda: webbrowser.open(url),
        ).pack(side="right", padx=16, pady=8)

    # ── Lógica ────────────────────────────────────────────────────────────────

    def _on_fetch(self):
        url = self.entry_url.get().strip()
        if not url:
            self._set_status("Pega una URL primero.", "warning")
            return
        if self.is_loading:
            return

        self.is_loading = True
        self.btn_fetch.configure(state="disabled", text="...")
        self.btn_download.configure(state="disabled")
        self._set_status("Obteniendo información del video...", "info")
        self._placeholder_formats()
        self.lbl_title.configure(text="—")
        self.lbl_duration.configure(text="")

        threading.Thread(target=self._fetch_thread, args=(url,), daemon=True).start()

    def _fetch_thread(self, url):
        import yt_dlp

        try:
            with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True}) as ydl:
                info = ydl.extract_info(url, download=False)

            title    = info.get("title", "Sin título")
            duration = info.get("duration_string", "?")
            formats  = info.get("formats", [])

            available_heights = {f.get("height") for f in formats if f.get("height")}

            presets = [
                ("Mejor calidad  (video + audio)", "bestvideo+bestaudio/best"),
                ("1080p          (video + audio)", "bestvideo[height<=1080]+bestaudio/best[height<=1080]"),
                ("720p           (video + audio)", "bestvideo[height<=720]+bestaudio/best[height<=720]"),
                ("480p           (video + audio)", "bestvideo[height<=480]+bestaudio/best[height<=480]"),
                ("360p           (video + audio)", "bestvideo[height<=360]+bestaudio/best[height<=360]"),
                ("Solo audio     (MP3 ~192kbps)",  "bestaudio/best"),
            ]

            filtered = []
            for label, fmt in presets:
                if "mejor" in label.lower() or "audio" in label.lower():
                    filtered.append((label, fmt))
                else:
                    for h in [1080, 720, 480, 360]:
                        if str(h) in label:
                            if any(ah >= h for ah in available_heights):
                                filtered.append((label, fmt))
                            break

            self.formats = filtered
            self.after(0, lambda: self._update_ui_after_fetch(title, duration, filtered))

        except Exception as e:
            self.after(0, lambda: self._set_status(f"Error: {e}", "error"))
            self.after(0, lambda: self.btn_fetch.configure(state="normal", text="Analizar"))
            self.is_loading = False

    def _update_ui_after_fetch(self, title, duration, presets):
        self.lbl_title.configure(text=title)
        self.lbl_duration.configure(text=f"Duración: {duration}")

        for w in self.frame_formats.winfo_children():
            w.destroy()

        self.selected_fmt.set(presets[0][1] if presets else "")

        for label, fmt in presets:
            row = ctk.CTkFrame(self.frame_formats, fg_color="transparent")
            row.pack(fill="x", pady=2)
            ctk.CTkRadioButton(
                row,
                text=label,
                variable=self.selected_fmt,
                value=fmt,
                font=("Courier New", 12),
                text_color=TEXT,
                fg_color=ACCENT,
                hover_color=ACCENT2,
                border_color=BORDER,
            ).pack(side="left", padx=8, pady=4)

        self.btn_fetch.configure(state="normal", text="Analizar")
        self.btn_download.configure(state="normal")
        self._set_status("Listo. Elige una calidad y descarga.", "success")
        self.is_loading = False

    def _on_download(self):
        fmt = self.selected_fmt.get()
        if not fmt:
            self._set_status("Selecciona una calidad.", "warning")
            return

        url = self.entry_url.get().strip()
        self.btn_download.configure(state="disabled", text="Descargando...")
        self.btn_fetch.configure(state="disabled")
        self.progress_bar.set(0)
        self.lbl_progress.configure(text="Iniciando...", text_color=MUTED)
        self._set_status("Descargando...", "info")

        threading.Thread(
            target=self._download_thread, args=(url, fmt), daemon=True
        ).start()

    def _download_thread(self, url, fmt):
        import yt_dlp

        output_dir  = get_output_dir()
        ffmpeg_path = get_ffmpeg_path()   # None si no está bundleado

        def progress_hook(d):
            if d["status"] == "downloading":
                pct_str = d.get("_percent_str", "0%").strip().replace("%", "")
                speed   = d.get("_speed_str", "").strip()
                eta     = d.get("_eta_str", "").strip()
                try:
                    pct = float(pct_str) / 100
                except ValueError:
                    pct = 0
                label = f"{pct_str}%  |  {speed}  |  ETA {eta}"
                self.after(0, lambda p=pct, l=label: self._update_progress(p, l))
            elif d["status"] == "finished":
                self.after(0, lambda: self._update_progress(1.0, "Procesando archivo..."))

        ydl_opts = {
            "format":             fmt,
            "outtmpl":            os.path.join(output_dir, "%(title)s.%(ext)s"),
            "progress_hooks":     [progress_hook],
            "quiet":              True,
            "no_warnings":        True,
            "merge_output_format": "mp4",
            "postprocessors":     [],
        }

        # Indicar dónde está ffmpeg si lo tenemos bundleado
        if ffmpeg_path:
            ydl_opts["ffmpeg_location"] = ffmpeg_path

        if fmt == "bestaudio/best":
            ydl_opts["postprocessors"] = [{
                "key":              "FFmpegExtractAudio",
                "preferredcodec":   "mp3",
                "preferredquality": "192",
            }]

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            self.after(0, lambda: self._on_download_done(output_dir))
        except Exception as e:
            self.after(0, lambda: self._on_download_error(str(e)))

    def _update_progress(self, pct, label):
        self.progress_bar.set(pct)
        self.lbl_progress.configure(text=label, text_color=TEXT)

    def _on_download_done(self, output_dir):
        self.progress_bar.set(1.0)
        self.lbl_progress.configure(text=f"Guardado en: {output_dir}", text_color=SUCCESS)
        self._set_status("¡Descarga completada!", "success")
        self.btn_download.configure(state="normal", text="Descargar")
        self.btn_fetch.configure(state="normal")

    def _on_download_error(self, error):
        self.lbl_progress.configure(text="Error en la descarga", text_color=ACCENT)
        self._set_status(f"Error: {error}", "error")
        self.btn_download.configure(state="normal", text="Descargar")
        self.btn_fetch.configure(state="normal")

    def _set_status(self, msg, level="info"):
        colors = {"info": MUTED, "success": SUCCESS, "warning": WARNING, "error": ACCENT}
        self.lbl_status.configure(text=msg, text_color=colors.get(level, MUTED))


if __name__ == "__main__":
    app = App()
    app.mainloop()
