"""Geografische Hilfsfunktionen fuer die Web-Mercator-Projektion.

Diese Funktionen bilden die Grundlage fuer die "Slippy-Map"-Kacheln von
OpenStreetMap. Sie sind bewusst frei von tkinter/PIL, damit sie sich leicht
testen lassen.
"""

from __future__ import annotations

import math

TILE_SIZE = 256  # Kantenlaenge einer OSM-Kachel in Pixeln


def lonlat_to_world(lon: float, lat: float, zoom: int) -> tuple[float, float]:
    """Wandelt geografische Koordinaten in Weltpixel der gegebenen Zoomstufe um."""
    n = TILE_SIZE * (2 ** zoom)
    x = (lon + 180.0) / 360.0 * n
    lat = max(min(lat, 85.05112878), -85.05112878)  # gueltiger Mercator-Bereich
    lat_rad = math.radians(lat)
    y = (1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n
    return x, y


def world_to_lonlat(x: float, y: float, zoom: int) -> tuple[float, float]:
    """Umkehrung von :func:`lonlat_to_world`."""
    n = TILE_SIZE * (2 ** zoom)
    lon = x / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1.0 - 2.0 * y / n)))
    return lon, math.degrees(lat_rad)


def clamp_lat(lat: float) -> float:
    return max(min(lat, 85.05112878), -85.05112878)
