"""Interaktive Kartenansicht auf Basis von OpenStreetMap-Kacheln.

Das Widget laedt echte OSM-Kacheln, laesst sich per Maus verschieben und
zoomen, zeigt ein Fadenkreuz sowie eine Info-Einblendung und kann ein
halbtransparentes Ergebnis-Overlay ueber die Karte legen.

Kacheln werden im Hintergrund geladen (Thread + Warteschlange), damit die
Oberflaeche beim Nachladen nicht einfriert. Bereits geladene Kacheln landen im
Arbeitsspeicher und zusaetzlich in einem Ordner auf der Festplatte.
"""

from __future__ import annotations

import math
import os
import queue
import tempfile
import threading
import tkinter as tk
import urllib.request

from PIL import Image, ImageDraw, ImageTk

from .geo import TILE_SIZE, clamp_lat, lonlat_to_world, world_to_lonlat

TILE_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
_USER_AGENT = "SchneeChecker/1.0 (Informatik-Projekt)"

MIN_ZOOM = 3
MAX_ZOOM = 17

# Farben der Ergebnis-Overlays je Modus (R, G, B).
COLOR_ELEVATION = (216, 60, 44)   # warmes Rot fuer Hoehe
COLOR_SNOW = (44, 110, 216)       # kuehles Blau fuer Schnee
OVERLAY_ALPHA = 120

_PLACEHOLDER = "#e8e4dc"          # Fuellfarbe fuer noch nicht geladene Kacheln


class MapView(tk.Frame):
    def __init__(self, master, center=(46.8, 10.5), zoom=7, on_zoom_change=None):
        super().__init__(master, bg="#000000")
        self.center_lat, self.center_lon = center
        self.zoom = zoom
        self.on_zoom_change = on_zoom_change

        self.canvas = tk.Canvas(self, highlightthickness=0, bg=_PLACEHOLDER, cursor="fleur")
        self.canvas.pack(fill="both", expand=True)

        # Kachel-Zwischenspeicher.
        self._tiles: dict[tuple[int, int, int], ImageTk.PhotoImage] = {}
        self._pending: set[tuple[int, int, int]] = set()
        self._requests: "queue.Queue" = queue.Queue()
        self._ready: "queue.Queue" = queue.Queue()
        self._cache_dir = os.path.join(tempfile.gettempdir(), "schnee_checker_tiles")
        os.makedirs(self._cache_dir, exist_ok=True)

        # Ergebnis-Overlay.
        self._cells = []
        self._overlay_mode = None
        self._overlay_img = None

        # Drag-Zustand.
        self._drag_start = None
        self._drag_last = None

        # Hintergrund-Thread fuer Kacheln.
        self._stop = threading.Event()
        self._worker = threading.Thread(target=self._tile_worker, daemon=True)
        self._worker.start()

        self.canvas.bind("<Configure>", lambda e: self.redraw())
        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        # Mausrad: Windows/Mac <MouseWheel>, Linux <Button-4>/<Button-5>.
        self.canvas.bind("<MouseWheel>", self._on_wheel_windows)
        self.canvas.bind("<Button-4>", lambda e: self._zoom_at(e.x, e.y, +1))
        self.canvas.bind("<Button-5>", lambda e: self._zoom_at(e.x, e.y, -1))

        self.after(80, self._poll_ready)

    # ------------------------------------------------------------------ #
    # Groesse / Geometrie
    # ------------------------------------------------------------------ #
    def _size(self):
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        return max(w, 1), max(h, 1)

    def visible_bbox(self):
        """Liefert die sichtbare Bounding-Box ``(lat_min, lon_min, lat_max, lon_max)``."""
        w, h = self._size()
        cwx, cwy = lonlat_to_world(self.center_lon, self.center_lat, self.zoom)
        lon0, lat_top = world_to_lonlat(cwx - w / 2, cwy - h / 2, self.zoom)
        lon1, lat_bot = world_to_lonlat(cwx + w / 2, cwy + h / 2, self.zoom)
        return (lat_bot, lon0, lat_top, lon1)

    # ------------------------------------------------------------------ #
    # Kachel-Laden im Hintergrund
    # ------------------------------------------------------------------ #
    def _tile_path(self, z, x, y):
        return os.path.join(self._cache_dir, f"{z}_{x}_{y}.png")

    def _tile_worker(self):
        while not self._stop.is_set():
            try:
                key = self._requests.get(timeout=0.5)
            except queue.Empty:
                continue
            if key is None:
                break
            z, x, y = key
            path = self._tile_path(z, x, y)
            image = None
            try:
                if os.path.exists(path):
                    image = Image.open(path).convert("RGBA")
                else:
                    url = TILE_URL.format(z=z, x=x, y=y)
                    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
                    with urllib.request.urlopen(req, timeout=15) as resp:
                        raw = resp.read()
                    with open(path, "wb") as fh:
                        fh.write(raw)
                    from io import BytesIO

                    image = Image.open(BytesIO(raw)).convert("RGBA")
            except Exception:
                image = None
            self._ready.put((key, image))

    def _poll_ready(self):
        updated = False
        while True:
            try:
                key, image = self._ready.get_nowait()
            except queue.Empty:
                break
            self._pending.discard(key)
            if image is not None:
                try:
                    self._tiles[key] = ImageTk.PhotoImage(image)
                    updated = True
                except tk.TclError:
                    pass
        if updated:
            self.redraw()
        if not self._stop.is_set():
            self.after(80, self._poll_ready)

    def _get_tile(self, key):
        img = self._tiles.get(key)
        if img is not None:
            return img
        if key not in self._pending:
            self._pending.add(key)
            self._requests.put(key)
        return None

    # ------------------------------------------------------------------ #
    # Zeichnen
    # ------------------------------------------------------------------ #
    def redraw(self):
        if not self.winfo_exists():
            return
        w, h = self._size()
        self.canvas.delete("all")

        cwx, cwy = lonlat_to_world(self.center_lon, self.center_lat, self.zoom)
        n_tiles = 2 ** self.zoom

        x0 = math.floor((cwx - w / 2) / TILE_SIZE)
        x1 = math.floor((cwx + w / 2) / TILE_SIZE)
        y0 = math.floor((cwy - h / 2) / TILE_SIZE)
        y1 = math.floor((cwy + h / 2) / TILE_SIZE)

        for tx in range(x0, x1 + 1):
            for ty in range(y0, y1 + 1):
                if ty < 0 or ty >= n_tiles:
                    continue
                wrapped_x = tx % n_tiles
                px = tx * TILE_SIZE - cwx + w / 2
                py = ty * TILE_SIZE - cwy + h / 2
                img = self._get_tile((self.zoom, wrapped_x, ty))
                if img is not None:
                    self.canvas.create_image(px, py, anchor="nw", image=img, tags=("pan", "tile"))
                else:
                    self.canvas.create_rectangle(
                        px, py, px + TILE_SIZE, py + TILE_SIZE,
                        fill=_PLACEHOLDER, outline=_PLACEHOLDER, tags=("pan", "tile"),
                    )

        self._draw_overlay(w, h, cwx, cwy)
        self._draw_hud(w, h)

    def _draw_overlay(self, w, h, cwx, cwy):
        if not self._cells:
            return
        color = COLOR_SNOW if self._overlay_mode == "schnee" else COLOR_ELEVATION
        fill = color + (OVERLAY_ALPHA,)

        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        drawn = False
        for cell in self._cells:
            if not cell.above:
                continue
            # Nordwest-Ecke (lon_min, lat_max) und Suedost-Ecke (lon_max, lat_min).
            lx, ty = lonlat_to_world(cell.lon_min, cell.lat_max, self.zoom)
            rx, by = lonlat_to_world(cell.lon_max, cell.lat_min, self.zoom)
            x_left = lx - cwx + w / 2
            y_top = ty - cwy + h / 2
            x_right = rx - cwx + w / 2
            y_bottom = by - cwy + h / 2
            draw.rectangle([x_left, y_top, x_right, y_bottom], fill=fill)
            drawn = True

        if not drawn:
            self._overlay_img = None
            return
        self._overlay_img = ImageTk.PhotoImage(img)
        self.canvas.create_image(0, 0, anchor="nw", image=self._overlay_img, tags=("pan", "overlay"))

    def _draw_hud(self, w, h):
        # Fadenkreuz in der Mitte.
        cx, cy = w / 2, h / 2
        arm = 12
        self.canvas.create_line(cx - arm, cy, cx + arm, cy, fill="#333333", width=1, tags="hud")
        self.canvas.create_line(cx, cy - arm, cx, cy + arm, fill="#333333", width=1, tags="hud")
        self.canvas.create_oval(cx - 3, cy - 3, cx + 3, cy + 3, outline="#333333", tags="hud")

        # Info-Einblendung unten links.
        text = f"Zoom {self.zoom}   {self.center_lat:.4f}, {self.center_lon:.4f}"
        pad = 6
        tid = self.canvas.create_text(
            pad + 6, h - pad - 8, anchor="sw", text=text,
            fill="#ffffff", font=("TkDefaultFont", 9), tags="hud",
        )
        bbox = self.canvas.bbox(tid)
        if bbox:
            self.canvas.create_rectangle(
                bbox[0] - 5, bbox[1] - 3, bbox[2] + 5, bbox[3] + 3,
                fill="#000000", outline="", stipple="gray50", tags="hud",
            )
            self.canvas.tag_raise(tid)

    # ------------------------------------------------------------------ #
    # Interaktion
    # ------------------------------------------------------------------ #
    def _on_press(self, event):
        self._drag_start = (event.x, event.y)
        self._drag_last = (event.x, event.y)

    def _on_drag(self, event):
        if self._drag_last is None:
            return
        dx = event.x - self._drag_last[0]
        dy = event.y - self._drag_last[1]
        self.canvas.move("pan", dx, dy)
        self._drag_last = (event.x, event.y)

    def _on_release(self, event):
        if self._drag_start is None:
            return
        total_dx = event.x - self._drag_start[0]
        total_dy = event.y - self._drag_start[1]
        self._drag_start = None
        self._drag_last = None
        if total_dx == 0 and total_dy == 0:
            return
        cwx, cwy = lonlat_to_world(self.center_lon, self.center_lat, self.zoom)
        cwx -= total_dx
        cwy -= total_dy
        lon, lat = world_to_lonlat(cwx, cwy, self.zoom)
        self.center_lon = lon
        self.center_lat = clamp_lat(lat)
        self.redraw()

    def _on_wheel_windows(self, event):
        self._zoom_at(event.x, event.y, +1 if event.delta > 0 else -1)

    def _zoom_at(self, mx, my, delta):
        new_zoom = max(MIN_ZOOM, min(MAX_ZOOM, self.zoom + delta))
        if new_zoom == self.zoom:
            return
        w, h = self._size()
        cwx, cwy = lonlat_to_world(self.center_lon, self.center_lat, self.zoom)
        # Geografischer Punkt unter dem Mauszeiger vor dem Zoom.
        lon, lat = world_to_lonlat(cwx + (mx - w / 2), cwy + (my - h / 2), self.zoom)
        self.zoom = new_zoom
        # Center so verschieben, dass derselbe Punkt wieder unter dem Zeiger liegt.
        wx, wy = lonlat_to_world(lon, lat, new_zoom)
        cwx2 = wx - (mx - w / 2)
        cwy2 = wy - (my - h / 2)
        clon, clat = world_to_lonlat(cwx2, cwy2, new_zoom)
        self.center_lon = clon
        self.center_lat = clamp_lat(clat)
        self.redraw()
        if self.on_zoom_change:
            self.on_zoom_change(self.zoom)

    def set_zoom(self, zoom):
        """Setzt die Zoomstufe (z. B. vom Schieberegler) unter Beibehaltung des Zentrums."""
        zoom = max(MIN_ZOOM, min(MAX_ZOOM, int(zoom)))
        if zoom == self.zoom:
            return
        self.zoom = zoom
        self.redraw()
        if self.on_zoom_change:
            self.on_zoom_change(self.zoom)

    # ------------------------------------------------------------------ #
    # Overlay-Steuerung
    # ------------------------------------------------------------------ #
    def set_cells(self, cells, mode):
        self._cells = cells or []
        self._overlay_mode = mode
        self.redraw()

    def clear_cells(self):
        self._cells = []
        self._overlay_img = None
        self.redraw()

    def destroy(self):
        self._stop.set()
        self._requests.put(None)
        super().destroy()
