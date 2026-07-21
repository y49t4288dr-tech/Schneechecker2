"""Tests fuer die GUI-freien Kernmodule (geo + data).

Diese Tests laufen ohne tkinter, Pillow oder Netzwerkzugriff.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from schnee_checker import data
from schnee_checker.geo import lonlat_to_world, world_to_lonlat


class GeoTests(unittest.TestCase):
    def test_roundtrip(self):
        for lon, lat, zoom in [(10.5, 46.8, 7), (0.0, 0.0, 3), (-73.9, 40.7, 12)]:
            x, y = lonlat_to_world(lon, lat, zoom)
            lon2, lat2 = world_to_lonlat(x, y, zoom)
            self.assertAlmostEqual(lon, lon2, places=6)
            self.assertAlmostEqual(lat, lat2, places=6)

    def test_lon_increases_eastward(self):
        x_west, _ = lonlat_to_world(0.0, 46.0, 8)
        x_east, _ = lonlat_to_world(10.0, 46.0, 8)
        self.assertLess(x_west, x_east)

    def test_lat_increases_downward(self):
        # Weiter noerdlich => kleinerer Weltpixel-Y-Wert.
        _, y_north = lonlat_to_world(10.0, 47.0, 8)
        _, y_south = lonlat_to_world(10.0, 46.0, 8)
        self.assertLess(y_north, y_south)


class GridTests(unittest.TestCase):
    def test_grid_count_and_bounds(self):
        bbox = (46.0, 10.0, 47.0, 11.0)  # lat_min, lon_min, lat_max, lon_max
        cells = data.build_grid(bbox, 5)
        self.assertEqual(len(cells), 25)
        lat0, lon0, lat1, lon1 = cells[0]
        self.assertAlmostEqual(lat0, 46.0)
        self.assertAlmostEqual(lon0, 10.0)
        self.assertAlmostEqual(lat1, 46.2)
        self.assertAlmostEqual(lon1, 10.2)


class SampleAreaTests(unittest.TestCase):
    def setUp(self):
        self._orig = data._fetch_batch

    def tearDown(self):
        data._fetch_batch = self._orig

    def test_threshold_and_cache(self):
        calls = {"count": 0}

        def fake_fetch(mode, points):
            calls["count"] += 1
            # Wert = Breitengrad * 100 (deterministisch, ohne Netzwerk).
            return [lat * 100 for lat, _ in points]

        data._fetch_batch = fake_fetch
        bbox = (46.0, 10.0, 47.0, 11.0)
        cache = {}
        cells = data.sample_area(
            data.MODE_ELEVATION, bbox, 4, threshold=4650,
            cache=cache, pause=0,
        )
        self.assertEqual(len(cells), 16)
        # Nur Zellen mit Mittelpunkt-Breite >= 46.5 liegen ueber der Schwelle.
        for cell in cells:
            expected = cell.center[0] * 100 >= 4650
            self.assertEqual(cell.above, expected)

        # Zweiter Lauf: alles aus dem Cache -> kein weiterer Abruf.
        before = calls["count"]
        data.sample_area(data.MODE_ELEVATION, bbox, 4, threshold=4650,
                         cache=cache, pause=0)
        self.assertEqual(calls["count"], before)

    def test_cancel_returns_empty(self):
        def fake_fetch(mode, points):
            return [1000.0 for _ in points]

        data._fetch_batch = fake_fetch
        cells = data.sample_area(
            data.MODE_ELEVATION, (46.0, 10.0, 47.0, 11.0), 4, threshold=0,
            should_cancel=lambda: True, pause=0,
        )
        self.assertEqual(cells, [])


if __name__ == "__main__":
    unittest.main()
