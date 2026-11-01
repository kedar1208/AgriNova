import os, tempfile, unittest
from datetime import date
import numpy as np
from engine.crop_database import load_crops
from engine.scenario_generator import generate_scenarios
from engine.optimization_engine import optimize, compare_strategies, crop_outcomes, DEFAULT_ASSUMPTIONS, evaluate_plan
from database import database as db
from utils.helpers import validate_farm, inr, to_acres
from utils.pdf_generator import build_report
from engine.climate_risk import assess_risks
from engine.irrigation_engine import advise
from engine.recommendation_engine import generate_alerts
from engine.weather_engine import get_weather

CR = load_crops()
SEL = CR[CR.crop.isin(["Rice", "Maize", "Soybean", "Cotton", "Groundnut"])].reset_index(drop=True)
SIM = generate_scenarios(1000, seed=42)
A = DEFAULT_ASSUMPTIONS


class TestOptimizer(unittest.TestCase):
    def test_constraints_respected_all_priorities(self):
        for pr in ["profit", "balanced", "risk", "water"]:
            r = optimize(SEL, 10, 150000, 2000, SIM, priority=pr)
            self.assertTrue(r["ok"], pr)
            x = np.array(list(r["allocation"].values()))
            self.assertLessEqual(x.sum(), 10 + 1e-6)
            self.assertLessEqual(r["matrices"]["cost"] @ x, 150000 + 1e-3)
            self.assertLessEqual(r["matrices"]["plan_w"] @ x, 2000 + 1e-3)
            self.assertTrue((x >= -1e-9).all())

    def test_budget_limit_binding_and_monotone(self):
        small = optimize(SEL, 10, 20000, 5000, SIM, priority="profit")
        big = optimize(SEL, 10, 400000, 5000, SIM, priority="profit")
        self.assertLessEqual(small["metrics"]["investment"], 20000 + 1e-3)
        self.assertLess(small["metrics"]["expected_profit"], big["metrics"]["expected_profit"])

    def test_zero_budget_gives_empty_plan(self):
        r = optimize(SEL, 10, 0, 5000, SIM)
        self.assertTrue(r["ok"]); self.assertAlmostEqual(sum(r["allocation"].values()), 0, places=6)

    def test_water_limit_blocks_irrigated_crops(self):
        rabi = CR[CR.crop.isin(["Wheat", "Tomato"])].reset_index(drop=True)
        assum = {"normal_rain": {"kharif": 870, "rabi": 100}}
        r = optimize(rabi, 5, 500000, 0, SIM, assum, "profit")   # rabi rain cannot cover ETm -> irrigation needed
        self.assertAlmostEqual(sum(r["allocation"].values()), 0, places=6)
        r2 = optimize(rabi, 5, 500000, 10000, SIM, assum, "profit")
        self.assertGreater(sum(r2["allocation"].values()), 0)

    def test_infeasible_min_allocation_reported_not_crashed(self):
        r = optimize(SEL, 10, 1000, 1000, SIM, min_frac=[0.2] * 5)  # forced 20% each, budget far too small
        self.assertFalse(r["ok"]); self.assertIn("feasible", r["message"].lower())

    def test_min_max_allocation_honoured(self):
        r = optimize(SEL, 10, 400000, 9000, SIM, priority="profit", min_frac=[0.1, 0, 0, 0, 0], max_frac=[0.3, 1, 1, 1, 1])
        self.assertGreaterEqual(r["allocation"]["Rice"], 1.0 - 1e-6); self.assertLessEqual(r["allocation"]["Rice"], 3.0 + 1e-6)

    def test_optimum_beats_baselines_on_its_own_objective(self):
        df, plans = compare_strategies(SEL, 10, 250000, 3000, SIM)
        prof = df.set_index("strategy").expected_profit
        self.assertGreaterEqual(prof["Optimised: profit"], prof.drop("Optimised: profit").max() - 1e-3)
        risk_cvar = df.set_index("strategy").cvar
        self.assertGreaterEqual(risk_cvar["Optimised: risk"] * 1, risk_cvar["Baseline: even split"])

    def test_risk_priority_improves_downside(self):
        p, k = optimize(SEL, 10, 250000, 3000, SIM, priority="profit"), optimize(SEL, 10, 250000, 3000, SIM, priority="risk")
        self.assertGreaterEqual(k["metrics"]["cvar"], p["metrics"]["cvar"] - 1e-3)
        self.assertGreaterEqual(p["metrics"]["expected_profit"], k["metrics"]["expected_profit"] - 1e-3)

    def test_what_if_less_rain_hurts_profit_and_cost_increase_hurts(self):
        base = optimize(SEL, 10, 400000, 6000, SIM, priority="profit")["metrics"]["expected_profit"]
        dry = optimize(SEL, 10, 400000, 6000, generate_scenarios(1000, rain_change=-0.3), priority="profit")["metrics"]["expected_profit"]
        cost = optimize(SEL, 10, 400000, 6000, SIM, {"cost_mult": 1.15}, "profit")["metrics"]["expected_profit"]
        self.assertLess(dry, base); self.assertLess(cost, base)

    def test_yield_physics(self):
        c = SEL[SEL.crop == "Rice"].iloc[0]
        o = crop_outcomes(c, [1.0, 0.5, 1.9], A)
        self.assertLess(o["yield_q"][1], o["yield_q"][0])      # drought < normal
        self.assertLessEqual(o["yield_q"][2], o["yield_q"][0])  # severe excess cannot beat normal
        self.assertTrue((o["yield_q"] >= 0).all() and (o["yield_q"] <= c["yield_q_acre"] + 1e-9).all())

    def test_reproducible_result(self):
        a, b = optimize(SEL, 10, 250000, 3000, generate_scenarios(1000, seed=5)), optimize(SEL, 10, 250000, 3000, generate_scenarios(1000, seed=5))
        self.assertEqual(a["allocation"], b["allocation"])

    def test_invalid_inputs(self):
        for kw in ({"area": 0}, {"area": -3}, {"budget": -1}, {"water": -1}):
            args = {"area": 10, "budget": 1000, "water": 100, **kw}
            with self.assertRaises(ValueError): optimize(SEL, args["area"], args["budget"], args["water"], SIM)
        with self.assertRaises(ValueError): optimize(SEL.iloc[0:0], 10, 1000, 100, SIM)
        with self.assertRaises(ValueError): optimize(SEL, 10, 1000, 100, SIM, priority="magic")
        with self.assertRaises(ValueError): optimize(SEL, 10, 1000, 100, SIM, min_frac=[0.5] * 5)


class TestSupport(unittest.TestCase):
    def test_validate_farm(self):
        ok = dict(crop="Wheat", area_acres=3, soil="Loam", irrigation="Drip", budget=20000, water_m3=500, sowing_date=date.today())
        self.assertEqual(validate_farm(ok), [])
        self.assertTrue(validate_farm({**ok, "area_acres": -1})); self.assertTrue(validate_farm({**ok, "crop": "Kale"}))
        self.assertTrue(validate_farm({**ok, "budget": -5})); self.assertTrue(validate_farm({**ok, "measured_pct": 140}))
        self.assertTrue(validate_farm({**ok, "sowing_date": "yesterday"}))
        self.assertAlmostEqual(to_acres(1, "hectares"), 2.47105); self.assertEqual(inr(1234567), "Rs 12,34,567")

    def test_database_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "t.db")
            db.save_config("farm1", {"crop": "Wheat", "area": 3}, p); db.save_config("farm1", {"crop": "Rice", "area": 4}, p)
            self.assertEqual(db.list_configs(p), ["farm1"]); self.assertEqual(db.load_config("farm1", p)["crop"], "Rice")
            self.assertIsNone(db.load_config("nope", p))
            db.save_plan("farm1", "risk", {"x": 1}, p); self.assertEqual(db.list_plans(p)[0]["priority"], "risk")
            with self.assertRaises(ValueError): db.save_config("  ", {}, p)

    def test_pdf_report_is_valid_pdf(self):
        wx, meta = get_weather("Punjab", offline=True)
        c = CR[CR.crop == "Wheat"].iloc[0].to_dict()
        risks = assess_risks(wx, c, 2, "Loam"); irr = advise(wx, c, 2, "Loam", 3, "Drip")
        alerts = generate_alerts(wx, c, risks, irr, meta["source"])
        opt = optimize(SEL, 10, 250000, 3000, SIM); df, _ = compare_strategies(SEL, 10, 250000, 3000, SIM)
        pdf = build_report({"crop": "Wheat", "area_acres": 3}, meta, risks, irr, alerts, opt, df)
        self.assertTrue(pdf.startswith(b"%PDF")); self.assertGreater(len(pdf), 3000)
        self.assertTrue(build_report({"crop": "x"}, {"source": "n/a"}).startswith(b"%PDF"))  # partial report works

    def test_alerts_from_sample_data(self):
        wx, meta = get_weather("Maharashtra", offline=True)
        c = CR[CR.crop == "Wheat"].iloc[0].to_dict()
        risks = assess_risks(wx, c, 2, "Loam"); al = generate_alerts(wx, c, risks, advise(wx, c, 2, "Loam", 2, "Drip"), meta["source"])
        txt = " ".join(a["message"] for a in al)
        self.assertIn("High temperature", txt); self.assertIn("Heavy rainfall", txt); self.assertIn("SAMPLE", al[0]["basis"])


if __name__ == "__main__":
    unittest.main()
