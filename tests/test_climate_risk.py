import unittest
from datetime import date, timedelta
import numpy as np
from engine.crop_database import get_crop, stage_for
from engine.climate_risk import assess_risks, categorize
from engine.irrigation_engine import advise
from engine.weather_engine import clean_weather, get_weather, hargreaves_et0
from tests.helpers_for_tests import make_wx

W = get_crop("Wheat")


class TestRisk(unittest.TestCase):
    def test_heat_monotonic_and_bounded(self):
        cool = assess_risks(make_wx(tmax=28), W, 2, "Loam")["heat"]["score"]
        hot = assess_risks(make_wx(tmax=38), W, 2, "Loam")["heat"]["score"]
        self.assertEqual(cool, 0)
        self.assertGreater(hot, 50)
        self.assertLessEqual(hot, 100)

    def test_stage_sensitivity(self):  # heat matters more at flowering than germination
        wx = make_wx(tmax=38)
        self.assertGreater(assess_risks(wx, W, 2, "Loam")["heat"]["score"], assess_risks(wx, W, 0, "Loam")["heat"]["score"])

    def test_cold(self):
        self.assertGreater(assess_risks(make_wx(tmin=0), W, 2, "Loam")["cold"]["score"], 40)

    def test_flood_and_rain(self):
        wx = make_wx(rain={5: 90, 6: 80, "default": 0})
        r = assess_risks(wx, W, 2, "Clay")
        self.assertGreater(r["flood"]["score"], 25)
        dry = assess_risks(make_wx(rain=0), W, 2, "Clay")
        self.assertEqual(dry["flood"]["score"], 0)
        # poorly drained soil scores higher than sandy for same rain
        self.assertGreater(r["flood"]["score"], assess_risks(wx, W, 2, "Sandy")["flood"]["score"])

    def test_drought_depends_on_rain_and_measured_moisture(self):
        dry = assess_risks(make_wx(rain=0, et0=6), W, 2, "Sandy", measured_pct=40)["drought"]["score"]
        wet = assess_risks(make_wx(rain=15, et0=3), W, 2, "Loam", measured_pct=90)["drought"]["score"]
        self.assertGreater(dry, wet)

    def test_fungal_uses_rain_proxy_when_rh_missing(self):
        wx = make_wx(rain=5, rh=np.nan, tmax=26, tmin=18)
        r = assess_risks(wx, get_crop("Rice"), 1, "Clay")["fungal"]
        self.assertGreaterEqual(r["score"], 0)

    def test_explanation_fields_and_categories(self):
        r = assess_risks(make_wx(tmax=38), W, 2, "Loam")["heat"]
        for k in ("score", "category", "factors", "action", "what"):
            self.assertIn(k, r)
        self.assertEqual([categorize(x) for x in (0, 30, 60, 90)], ["Low", "Moderate", "High", "Severe"])

    def test_empty_weather_and_bad_soil_raise(self):
        with self.assertRaises(ValueError):
            assess_risks(make_wx().iloc[0:0], W, 2, "Loam")
        with self.assertRaises(ValueError):
            assess_risks(make_wx(), W, 2, "Moonrock")


class TestMissingData(unittest.TestCase):
    def test_imputation_and_flags(self):
        wx = make_wx()
        wx.loc[3, "tmax"] = np.nan
        wx.loc[5, "et0_mm"] = np.nan
        wx.loc[8, "rh_mean"] = np.nan
        c, q = clean_weather(wx, lat=20)
        self.assertEqual(c.isna().sum().sum(), 0)
        self.assertEqual(q["imputed_rows"], 3)
        self.assertTrue(c.imputed.sum() == 3)

    def test_unusable_inputs(self):
        with self.assertRaises(ValueError):
            clean_weather(make_wx().iloc[0:0])
        bad = make_wx(); bad["tmax"] = np.nan
        with self.assertRaises(ValueError):
            clean_weather(bad)

    def test_implausible_values_removed(self):
        wx = make_wx(); wx.loc[2, "tmax"] = 99; wx.loc[4, "rain_mm"] = -5
        c, _ = clean_weather(wx)
        self.assertLess(c.tmax.max(), 56); self.assertGreaterEqual(c.rain_mm.min(), 0)

    def test_offline_fallback_is_labelled(self):
        c, meta = get_weather("Maharashtra", offline=True)
        self.assertIn("SAMPLE", meta["source"]); self.assertGreater(len(c), 10)

    def test_hargreaves_reasonable(self):
        self.assertTrue(2 < hargreaves_et0(34, 22, 18.5, 120) < 9)


class TestIrrigation(unittest.TestCase):
    def test_dry_spell_needs_irrigation(self):
        a = advise(make_wx(rain=0, et0=6), W, 2, "Sandy", 2, "Drip", measured_pct=45)
        self.assertTrue(a["needed"]); self.assertGreater(a["volume_m3"], 0); self.assertFalse(a["estimated"])

    def test_postpone_when_big_rain_coming(self):
        a = advise(make_wx(rain={0: 0, 1: 60, 2: 40, "default": 0}, et0=5), W, 2, "Sandy", 2, "Drip", measured_pct=25)
        self.assertTrue(a["postpone"])

    def test_wet_conditions_no_irrigation(self):
        a = advise(make_wx(rain=12, et0=3), W, 2, "Loam", 2, "Drip", measured_pct=90)
        self.assertFalse(a["needed"])

    def test_rainfed_has_no_volume_and_estimated_flag(self):
        a = advise(make_wx(rain=0, et0=6), W, 2, "Sandy", 2, "Rainfed (none)")
        self.assertEqual(a["volume_m3"], 0); self.assertTrue(a["estimated"])

    def test_not_sown_and_bad_inputs(self):
        self.assertFalse(advise(make_wx(), W, -1, "Loam", 2, "Drip")["needed"])
        with self.assertRaises(ValueError): advise(make_wx(), W, 2, "Loam", 0, "Drip")
        with self.assertRaises(ValueError): advise(make_wx(), W, 2, "Loam", 2, "Laser")

    def test_stage_calc(self):
        t = date.today()
        self.assertEqual(stage_for(t + timedelta(days=3), 100, t)[0], -1)
        self.assertEqual(stage_for(t - timedelta(days=50), 100, t)[0], 2)
        self.assertEqual(stage_for(t - timedelta(days=500), 100, t)[0], 4)


if __name__ == "__main__":
    unittest.main()
