"""Hauptfenster des Schnee-Checkers.

Links die grosse Kartenansicht, rechts die dunkle Steuerleiste mit Modus-
Umschalter, Schiebereglern, Aktualisieren-Button, Statuszeile, Fortschritts-
balken und Legende.
"""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from tkinter import ttk

from . import data
from .mapview import MAX_ZOOM, MIN_ZOOM, MapView

# Farbwelt der Steuerleiste (dunkel, ruhig).
PANEL_BG = "#1e1e24"
CARD_BG = "#26262e"
FG = "#e6e6ea"
MUTED = "#9a9aa5"
ACCENT = "#d63a2f"
ACCENT_ACTIVE = "#b8281f"
TROUGH = "#3a3a44"

# Voreinstellungen je Modus: (von, bis, standard, einheit).
MODE_RANGES = {
    data.MODE_ELEVATION: (0, 4000, 1500, "m"),
    data.MODE_SNOW: (0, 200, 30, "cm"),
}
MODE_LABELS = {
    data.MODE_ELEVATION: "Höhe",
    data.MODE_SNOW: "Schnee",
}


class SchneeCheckerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Schnee-Checker")
        self.geometry("1100x720")
        self.minsize(820, 540)
        self.configure(bg=PANEL_BG)

        self._cache = {}
        self._queue: "queue.Queue" = queue.Queue()
        self._worker = None
        self._generation = 0
        self._sync_zoom = False  # verhindert Rueckkopplung Slider <-> Karte
        self._threshold_by_mode = {
            data.MODE_ELEVATION: MODE_RANGES[data.MODE_ELEVATION][2],
            data.MODE_SNOW: MODE_RANGES[data.MODE_SNOW][2],
        }

        self.mode = tk.StringVar(value=data.MODE_ELEVATION)

        self._build_layout()
        self.after(120, self._poll_queue)

    # ------------------------------------------------------------------ #
    # Aufbau der Oberflaeche
    # ------------------------------------------------------------------ #
    def _build_layout(self):
        self.map = MapView(self, center=(46.8, 10.5), zoom=7, on_zoom_change=self._on_map_zoom)
        self.map.pack(side="left", fill="both", expand=True)

        panel = tk.Frame(self, bg=PANEL_BG, width=270)
        panel.pack(side="right", fill="y")
        panel.pack_propagate(False)

        tk.Label(panel, text="Schnee-Checker", bg=PANEL_BG, fg=FG,
                 font=("TkDefaultFont", 15, "bold")).pack(anchor="w", padx=18, pady=(18, 2))
        tk.Label(panel, text="Höhe und Schnee auf der Karte", bg=PANEL_BG, fg=MUTED,
                 font=("TkDefaultFont", 9)).pack(anchor="w", padx=18, pady=(0, 14))

        # --- Modus-Umschalter ---
        self._section(panel, "Modus")
        mode_row = tk.Frame(panel, bg=PANEL_BG)
        mode_row.pack(fill="x", padx=18, pady=(0, 12))
        for value in (data.MODE_ELEVATION, data.MODE_SNOW):
            tk.Radiobutton(
                mode_row, text=MODE_LABELS[value], value=value, variable=self.mode,
                command=self._on_mode_change, indicatoron=False, width=8,
                bg=CARD_BG, fg=FG, selectcolor=ACCENT, activebackground=CARD_BG,
                activeforeground=FG, bd=0, relief="flat", padx=8, pady=6,
                font=("TkDefaultFont", 10),
            ).pack(side="left", padx=(0, 8))

        # --- Schwelle ---
        von, bis, start, einheit = MODE_RANGES[data.MODE_ELEVATION]
        self.threshold_label = self._section(panel, f"Schwelle: {start} {einheit}")
        self.threshold = tk.Scale(
            panel, from_=von, to=bis, orient="horizontal", showvalue=False,
            command=self._on_threshold, **self._scale_style(),
        )
        self.threshold.set(start)
        self.threshold.pack(fill="x", padx=18, pady=(0, 14))

        # --- Aufloesung (Raster) ---
        self.resolution_label = self._section(panel, "Auflösung: 10 × 10")
        self.resolution = tk.Scale(
            panel, from_=4, to=20, orient="horizontal", showvalue=False,
            command=self._on_resolution, **self._scale_style(),
        )
        self.resolution.set(10)
        self.resolution.pack(fill="x", padx=18, pady=(0, 14))

        # --- Zoom ---
        self.zoom_label = self._section(panel, "Zoom: 7")
        self.zoom = tk.Scale(
            panel, from_=MIN_ZOOM, to=MAX_ZOOM, orient="horizontal", showvalue=False,
            command=self._on_zoom_slider, **self._scale_style(),
        )
        self.zoom.set(7)
        self.zoom.pack(fill="x", padx=18, pady=(0, 16))

        # --- Aktualisieren-Button ---
        self.refresh_btn = tk.Button(
            panel, text="Aktualisieren", command=self._on_refresh,
            bg=ACCENT, fg="#ffffff", activebackground=ACCENT_ACTIVE,
            activeforeground="#ffffff", bd=0, relief="flat", pady=10,
            font=("TkDefaultFont", 11, "bold"), cursor="hand2",
        )
        self.refresh_btn.pack(fill="x", padx=18, pady=(0, 12))

        # --- Status + Fortschritt ---
        self.status = tk.Label(panel, text="Bereit.", bg=PANEL_BG, fg=MUTED,
                               anchor="w", font=("TkDefaultFont", 9))
        self.status.pack(fill="x", padx=18, pady=(0, 4))

        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Schnee.Horizontal.TProgressbar", troughcolor=TROUGH,
                        background=ACCENT, bordercolor=PANEL_BG, lightcolor=ACCENT,
                        darkcolor=ACCENT)
        self.progress = ttk.Progressbar(panel, style="Schnee.Horizontal.TProgressbar",
                                        maximum=100)
        self.progress.pack(fill="x", padx=18, pady=(0, 18))

        # --- Legende ---
        self._section(panel, "Legende")
        self.legend = tk.Frame(panel, bg=PANEL_BG)
        self.legend.pack(fill="x", padx=18, pady=(0, 8))
        self._build_legend()

    def _scale_style(self):
        return dict(
            bg=PANEL_BG, fg=FG, troughcolor=TROUGH, highlightthickness=0,
            bd=0, sliderrelief="flat", activebackground=ACCENT, length=220,
        )

    def _section(self, parent, text):
        lbl = tk.Label(parent, text=text, bg=PANEL_BG, fg=FG, anchor="w",
                       font=("TkDefaultFont", 10, "bold"))
        lbl.pack(fill="x", padx=18, pady=(2, 4))
        return lbl

    def _build_legend(self):
        for child in self.legend.winfo_children():
            child.destroy()
        mode = self.mode.get()
        if mode == data.MODE_SNOW:
            color, text = "#2c6ed8", "Fläche mit Schnee über der Schwelle"
        else:
            color, text = "#d83c2c", "Fläche über der Höhenschwelle"
        row = tk.Frame(self.legend, bg=PANEL_BG)
        row.pack(fill="x")
        swatch = tk.Canvas(row, width=18, height=18, bg=PANEL_BG, highlightthickness=0)
        swatch.create_rectangle(2, 2, 16, 16, fill=color, outline=color)
        swatch.pack(side="left")
        tk.Label(row, text=text, bg=PANEL_BG, fg=MUTED, anchor="w",
                 justify="left", wraplength=200, font=("TkDefaultFont", 9)).pack(
            side="left", padx=(8, 0))

    # ------------------------------------------------------------------ #
    # Ereignisse der Bedienelemente
    # ------------------------------------------------------------------ #
    def _on_mode_change(self):
        mode = self.mode.get()
        von, bis, _default, einheit = MODE_RANGES[mode]
        value = self._threshold_by_mode[mode]
        self.threshold.config(from_=von, to=bis)
        self.threshold.set(value)
        self.threshold_label.config(text=f"Schwelle: {value} {einheit}")
        self._build_legend()

    def _on_threshold(self, raw):
        mode = self.mode.get()
        einheit = MODE_RANGES[mode][3]
        value = int(float(raw))
        self._threshold_by_mode[mode] = value
        self.threshold_label.config(text=f"Schwelle: {value} {einheit}")

    def _on_resolution(self, raw):
        value = int(float(raw))
        self.resolution_label.config(text=f"Auflösung: {value} × {value}")

    def _on_zoom_slider(self, raw):
        if self._sync_zoom:
            return
        value = int(float(raw))
        self.zoom_label.config(text=f"Zoom: {value}")
        self.map.set_zoom(value)

    def _on_map_zoom(self, zoom):
        # Karte hat gezoomt (Mausrad) -> Slider ohne Rueckkopplung nachziehen.
        self._sync_zoom = True
        self.zoom.set(zoom)
        self.zoom_label.config(text=f"Zoom: {zoom}")
        self._sync_zoom = False

    # ------------------------------------------------------------------ #
    # Datenabruf im Hintergrund
    # ------------------------------------------------------------------ #
    def _on_refresh(self):
        if self._worker and self._worker.is_alive():
            return  # laeuft bereits
        mode = self.mode.get()
        bbox = self.map.visible_bbox()
        resolution = int(self.resolution.get())
        threshold = int(self.threshold.get())

        self._generation += 1
        generation = self._generation
        self.refresh_btn.config(state="disabled", text="Lädt …")
        self.progress["value"] = 0
        self.status.config(text="Daten werden geladen …")

        def progress_cb(done, total):
            self._queue.put(("progress", generation, done, total))

        def should_cancel():
            return generation != self._generation

        def run():
            try:
                cells = data.sample_area(
                    mode, bbox, resolution, threshold,
                    cache=self._cache, progress=progress_cb,
                    should_cancel=should_cancel,
                )
                self._queue.put(("done", generation, mode, cells))
            except Exception as exc:  # noqa: BLE001 - an die GUI weiterreichen
                self._queue.put(("error", generation, str(exc)))

        self._worker = threading.Thread(target=run, daemon=True)
        self._worker.start()

    def _poll_queue(self):
        try:
            while True:
                message = self._queue.get_nowait()
                self._handle_message(message)
        except queue.Empty:
            pass
        self.after(120, self._poll_queue)

    def _handle_message(self, message):
        kind = message[0]
        generation = message[1]
        if generation != self._generation:
            return  # veraltete Nachricht eines abgebrochenen Laufs
        if kind == "progress":
            _, _, done, total = message
            pct = 0 if total == 0 else int(done / total * 100)
            self.progress["value"] = pct
            self.status.config(text=f"Daten werden geladen … {done}/{total}")
        elif kind == "done":
            _, _, mode, cells = message
            self.map.set_cells(cells, mode)
            above = sum(1 for c in cells if c.above)
            self.progress["value"] = 100
            self.status.config(text=f"Fertig – {above} von {len(cells)} Feldern markiert.")
            self.refresh_btn.config(state="normal", text="Aktualisieren")
        elif kind == "error":
            _, _, msg = message
            self.progress["value"] = 0
            self.status.config(text=f"Fehler: {msg}")
            self.refresh_btn.config(state="normal", text="Aktualisieren")


def main():
    app = SchneeCheckerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
