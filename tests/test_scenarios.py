import unittest
import numpy as np, pandas as pd
from engine.scenario_generator import generate_scenarios, import_scenarios


class TestScenarios(unittest.TestCase):
    def test_reproducible_with_seed(self):
        a, b = generate_scenarios(1000, seed=7), generate_scenarios(1000, seed=7)
        pd.testing.assert_frame_equal(a, b)
        self.assertFalse(a.equals(generate_scenarios(1000, seed=8)))

    def test_count_labels_and_bounds(self):
        s = generate_scenarios(1000)
        self.assertEqual(len(s), 1000); self.assertEqual(set(s.scenario), {"Normal", "Drought", "Excess"})
        self.assertTrue((s.rain_mult > 0).all()); self.assertIn("SIMULATED", s.attrs["data_type"])

    def test_probabilities_respected(self):
        s = generate_scenarios(5000, probs={"Normal": 0.2, "Drought": 0.7, "Excess": 0.1}, seed=1)
        self.assertAlmostEqual((s.scenario == "Drought").mean(), 0.7, delta=0.03)

    def test_scenario_means_ordered(self):
        m = generate_scenarios(3000).groupby("scenario").rain_mult.mean()
        self.assertLess(m["Drought"], m["Normal"]); self.assertLess(m["Normal"], m["Excess"])

    def test_rain_change_and_severity(self):
        base = generate_scenarios(2000, seed=3).rain_mult.mean()
        self.assertAlmostEqual(generate_scenarios(2000, seed=3, rain_change=-0.3).rain_mult.mean(), base * 0.7, places=6)
        d0 = generate_scenarios(2000, seed=3, severity=1.0).query("scenario=='Drought'").rain_mult.mean()
        d2 = generate_scenarios(2000, seed=3, severity=1.5).query("scenario=='Drought'").rain_mult.mean()
        self.assertLess(d2, d0)

    def test_invalid_inputs(self):
        for kw in ({"n": 0}, {"n": -5}, {"probs": {"Normal": 0, "Drought": 0, "Excess": 0}},
                   {"probs": {"Normal": -1, "Drought": 1, "Excess": 1}}, {"rain_change": -1.0}, {"severity": -1}):
            with self.assertRaises(ValueError): generate_scenarios(**{"n": 100, **kw})

    def test_import(self):
        s = import_scenarios(pd.DataFrame({"rain_mult": [0.6, 1.0, 1.5]}))
        self.assertEqual(list(s.scenario), ["Drought", "Normal", "Excess"])
        with self.assertRaises(ValueError): import_scenarios(pd.DataFrame({"x": [1]}))
        with self.assertRaises(ValueError): import_scenarios(pd.DataFrame({"rain_mult": [1.0, -2.0]}))
