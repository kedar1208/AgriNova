import unittest
from datetime import date
from unittest.mock import patch, MagicMock
from engine import locations, weather_engine as we
from utils.helpers import validate_farm


class TestLocations(unittest.TestCase):
    def test_every_state_has_coords_default_and_unique_districts(self):
        self.assertEqual(set(locations.DISTRICTS), set(we.STATE_COORDS))
        for st, ds in locations.DISTRICTS.items():
            self.assertEqual(len(ds), len(set(ds)), st)
            self.assertIn(locations.DEFAULT_DISTRICT[st], ds)

    def test_random_text_is_not_a_district(self):
        self.assertFalse(locations.is_valid("Karnataka", "seedhe maut"))
        self.assertFalse(locations.is_valid("Karnataka", "Pune"))      # real district, wrong state
        self.assertTrue(locations.is_valid("Maharashtra", "Pune"))

    def test_validate_farm_rejects_bad_district(self):
        cfg = dict(state="Karnataka", district="seedhe maut", crop="Wheat", area_acres=3, soil="Loam", irrigation="Drip",
                   budget=1, water_m3=1, sowing_date=date.today())
        self.assertTrue(any("district" in e.lower() for e in validate_farm(cfg)))
        cfg["district"] = "Mysuru"
        self.assertEqual(validate_farm(cfg), [])


def _resp(results):
    r = MagicMock(); r.json.return_value = {"results": results}; r.raise_for_status = lambda: None
    return r


class TestGeocode(unittest.TestCase):
    def test_only_hits_inside_the_state_count(self):
        hits = [{"name": "Pune", "admin1": "Karnataka", "latitude": 1, "longitude": 1}]
        with patch("requests.get", return_value=_resp(hits)):
            self.assertIsNone(we.geocode("Pune", "Maharashtra"))

    def test_alias_is_tried(self):
        def fake(url, params=None, timeout=0):
            return _resp([{"name": "Mysore", "admin1": "Karnataka", "latitude": 12.3, "longitude": 76.6}] if params["name"] == "Mysore" else [])
        with patch("requests.get", side_effect=fake):
            self.assertEqual(we.geocode("Mysuru", "Karnataka"), (12.3, 76.6))

    def test_locate_flags_approximate_when_not_found(self):
        with patch.object(we, "geocode", return_value=None):
            loc = we.locate("Karnataka", "Mysuru")
        self.assertFalse(loc["exact"]); self.assertIn("reference point", loc["note"])

    def test_offline_never_touches_network(self):
        with patch("requests.get", side_effect=AssertionError("network used")):
            wx, meta = we.get_weather("Maharashtra", "Pune", offline=True)
        self.assertEqual(meta["source"], "SAMPLE (synthetic)"); self.assertEqual(meta["location"], "Pune, Maharashtra")

    def test_live_failure_falls_back_with_message(self):
        with patch("requests.get", side_effect=OSError("down")):
            wx, meta = we.get_weather("Maharashtra", "Pune")
        self.assertEqual(meta["source"], "SAMPLE (synthetic)"); self.assertIn("unavailable", meta["error"])

    def test_live_weather_raises_so_it_is_never_cached(self):
        with patch("requests.get", side_effect=OSError("down")):
            with self.assertRaises(OSError):
                we.get_live_weather("Maharashtra", "Pune")


if __name__ == "__main__":
    unittest.main()
