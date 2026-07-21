"""Datenbeschaffung fuer den Schnee-Checker.

Die Werte (Hoehe bzw. Schneehoehe) stammen live aus der frei zugaenglichen
Open-Meteo-Schnittstelle. Ueber das sichtbare Gebiet wird ein Raster gelegt,
fuer jeden Rasterpunkt ein Wert abgefragt und die Punkte anschliessend zu
farbigen Zellen zusammengefasst.

Um die Zahl der Anfragen klein zu halten, werden die Punkte paketweise
abgefragt, kurze Pausen eingelegt und bereits geladene Werte zwischengespeichert.

Dieses Modul kommt bewusst ohne GUI-Abhaengigkeiten aus und laesst sich daher
einzeln testen.
"""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass

MODE_ELEVATION = "hoehe"
MODE_SNOW = "schnee"

ELEVATION_URL = "https://api.open-meteo.com/v1/elevation"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

_USER_AGENT = "SchneeChecker/1.0 (Informatik-Projekt)"


@dataclass
class Cell:
    """Eine Rasterzelle mit ihren geografischen Grenzen und ihrem Messwert."""

    lat_min: float
    lon_min: float
    lat_max: float
    lon_max: float
    value: float | None
    above: bool

    @property
    def center(self) -> tuple[float, float]:
        return (
            (self.lat_min + self.lat_max) / 2.0,
            (self.lon_min + self.lon_max) / 2.0,
        )


class DataError(RuntimeError):
    """Fehler beim Abruf der Daten."""


def build_grid(bbox, resolution):
    """Zerlegt eine Bounding-Box in ``resolution`` x ``resolution`` Zellen.

    ``bbox`` ist ein Tupel ``(lat_min, lon_min, lat_max, lon_max)``.
    Zurueckgegeben wird eine Liste von Zellgrenzen ``(lat0, lon0, lat1, lon1)``.
    """
    lat_min, lon_min, lat_max, lon_max = bbox
    resolution = max(1, int(resolution))
    lat_step = (lat_max - lat_min) / resolution
    lon_step = (lon_max - lon_min) / resolution
    cells = []
    for row in range(resolution):
        lat0 = lat_min + row * lat_step
        lat1 = lat0 + lat_step
        for col in range(resolution):
            lon0 = lon_min + col * lon_step
            lon1 = lon0 + lon_step
            cells.append((lat0, lon0, lat1, lon1))
    return cells


def _http_get_json(url: str, params: dict, timeout: float = 20.0):
    query = urllib.parse.urlencode(params)
    request = urllib.request.Request(
        f"{url}?{query}", headers={"User-Agent": _USER_AGENT}
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _fetch_elevation(points):
    """Fragt Hoehenwerte (in Metern) fuer eine Liste von ``(lat, lon)`` ab."""
    lats = ",".join(f"{lat:.5f}" for lat, _ in points)
    lons = ",".join(f"{lon:.5f}" for _, lon in points)
    data = _http_get_json(ELEVATION_URL, {"latitude": lats, "longitude": lons})
    elevations = data.get("elevation")
    if elevations is None:
        raise DataError("Antwort ohne Hoehenwerte erhalten.")
    return list(elevations)


def _fetch_snow(points):
    """Fragt Schneehoehen (in Zentimetern) fuer eine Liste von ``(lat, lon)`` ab."""
    lats = ",".join(f"{lat:.5f}" for lat, _ in points)
    lons = ",".join(f"{lon:.5f}" for _, lon in points)
    data = _http_get_json(
        FORECAST_URL,
        {"latitude": lats, "longitude": lons, "current": "snow_depth"},
    )
    # Bei mehreren Orten liefert Open-Meteo eine Liste, bei einem Ort ein Objekt.
    entries = data if isinstance(data, list) else [data]
    values = []
    for entry in entries:
        current = entry.get("current") or {}
        depth_m = current.get("snow_depth")
        # snow_depth kommt in Metern -> in Zentimeter umrechnen.
        values.append(None if depth_m is None else depth_m * 100.0)
    return values


def _fetch_batch(mode, points):
    if mode == MODE_ELEVATION:
        return _fetch_elevation(points)
    if mode == MODE_SNOW:
        return _fetch_snow(points)
    raise ValueError(f"Unbekannter Modus: {mode!r}")


def sample_area(
    mode,
    bbox,
    resolution,
    threshold,
    cache=None,
    progress=None,
    should_cancel=None,
    batch_size=50,
    pause=0.25,
):
    """Tastet das Gebiet ab und liefert eine Liste von :class:`Cell`.

    ``cache`` ist ein optionales ``dict`` zum Zwischenspeichern bereits
    abgerufener Werte. ``progress`` ist ein optionaler Callback
    ``progress(done, total)``. ``should_cancel`` ist ein optionaler Callback,
    der ``True`` zurueckgibt, wenn der Vorgang abgebrochen werden soll.
    """
    if cache is None:
        cache = {}
    grid = build_grid(bbox, resolution)
    total = len(grid)

    # Fuer jede Zelle den Mittelpunkt bestimmen und schauen, was noch fehlt.
    centers = []
    for (lat0, lon0, lat1, lon1) in grid:
        centers.append(((lat0 + lat1) / 2.0, (lon0 + lon1) / 2.0))

    def cache_key(lat, lon):
        return (mode, round(lat, 4), round(lon, 4))

    missing = [
        (idx, center)
        for idx, center in enumerate(centers)
        if cache_key(*center) not in cache
    ]

    done = total - len(missing)
    if progress:
        progress(done, total)

    # Fehlende Punkte paketweise abfragen.
    for start in range(0, len(missing), batch_size):
        if should_cancel and should_cancel():
            return []
        chunk = missing[start : start + batch_size]
        points = [center for _, center in chunk]
        try:
            values = _fetch_batch(mode, points)
        except Exception as exc:  # Netzwerk/Serverfehler -> Werte als unbekannt
            raise DataError(str(exc)) from exc
        for (_, center), value in zip(chunk, values):
            cache[cache_key(*center)] = value
        done += len(chunk)
        if progress:
            progress(done, total)
        if start + batch_size < len(missing):
            time.sleep(pause)  # kurze Pause, um die Schnittstelle zu schonen

    # Ergebniszellen aufbauen.
    cells = []
    for (lat0, lon0, lat1, lon1), center in zip(grid, centers):
        value = cache.get(cache_key(*center))
        above = value is not None and value >= threshold
        cells.append(Cell(lat0, lon0, lat1, lon1, value, above))
    return cells
