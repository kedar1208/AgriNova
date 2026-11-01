"""Unified agricultural intelligence: connects AgroCast (weather-risk) results to FarmOptimizer (season planning).

Design rules (kept deliberately honest):
* AgroCast scores are HEURISTIC exposure indicators, not probabilities. They are never copied into the optimiser as a
  probability. Instead a High/Severe category switches on a clearly-labelled PLANNING SCENARIO whose size comes from the
  explicit ASSUMPTION tables below (editable, shown to the user).
* Only hazards the optimiser can represent are translated: drought (less rain, less water, higher drought share) and
  excess rain/waterlogging (more excess-rain share). Heat, cold and fungal conditions are explained but NOT modelled there.
* The CVaR linear programme in engine/optimization_engine.py is reused unchanged - it is simply run on a second scenario set."""
import numpy as np
from .scenario_generator import generate_scenarios
from .optimization_engine import optimize, build_matrices, evaluate_plan, DEFAULT_ASSUMPTIONS

# ---- explicit, editable assumptions (illustrative planning values, not calibrated to yield-loss data) ------------------
DROUGHT_STEPS = {"High": dict(rain=-0.10, p=10, water=0.90), "Severe": dict(rain=-0.20, p=20, water=0.80)}   # rain: seasonal rainfall change; p: extra P(drought) in % points; water: share of irrigation water still available
EXCESS_STEPS = {"High": dict(rain=0.05, p=10), "Severe": dict(rain=0.10, p=20)}
ASSUMPTION_TEXT = ("Planning scenario sizes are illustrative assumptions, not measured effects: a High drought category lowers seasonal rainfall by 10%, adds 10 percentage points to the "
                   "simulated drought share and leaves 90% of the irrigation water; Severe uses 20% / 20 points / 80%. High excess-rain uses +5% rain and +10 points of excess-rain seasons; Severe +10% / +20 points. "
                   "Moderate scores only raise a 'watch' note.")
LEVEL = {"Moderate": "info", "High": "warning", "Severe": "critical"}
NOT_MODELLED = "Explained for the farmer but not modelled in FarmOptimizer (it simulates rainfall and water only)."


def _excess_risk(risks):
    return max(risks["rain"], risks["flood"], key=lambda r: r["score"])


def scenario_adjustment(risks, force_drought=None):
    """Translate AgroCast categories into a planning-scenario adjustment. force_drought ('High'/'Severe') builds a what-if instead."""
    d_cat = force_drought or risks["drought"]["category"]
    e = _excess_risk(risks)
    e_cat = "Low" if force_drought else e["category"]
    d, x = DROUGHT_STEPS.get(d_cat), EXCESS_STEPS.get(e_cat)
    adj = {"applied": bool(d or x), "what_if": bool(force_drought), "rain_change": 0.0, "p_shift": {"Drought": 0, "Excess": 0}, "water_mult": 1.0, "rationale": []}
    if d:
        adj["rain_change"] += d["rain"]; adj["p_shift"]["Drought"] += d["p"]; adj["water_mult"] *= d["water"]
        src = "What-if" if force_drought else f"AgroCast drought risk is {d_cat} ({risks['drought']['score']:.0f}/100)"
        adj["rationale"].append(f"{src}: rainfall {d['rain']:+.0%}, drought share +{d['p']} points, irrigation water x{d['water']:.2f}.")
    if x:
        adj["rain_change"] += x["rain"]; adj["p_shift"]["Excess"] += x["p"]
        adj["rationale"].append(f"AgroCast {e['name'].lower()} risk is {e_cat} ({e['score']:.0f}/100): rainfall {x['rain']:+.0%}, excess-rain share +{x['p']} points.")
    return adj


def interpret(risks, irr, adj=None):
    """List of insight dicts (Moderate and above) explaining indicators, the irrigation advice and how the planner treats each."""
    adj = adj or scenario_adjustment(risks)
    out = []
    for key in ("drought", "heat", "rain", "flood", "cold", "fungal"):
        r = risks[key]
        if r["score"] < 25:
            continue
        if key == "drought":
            irrigation = irr.get("decision", "")
            planning = (f"Planning scenario: {adj['rationale'][0]}" if adj["applied"] and adj["p_shift"]["Drought"] else
                        "Watch only - below the High level needed to switch on a drought planning scenario.")
        elif key in ("rain", "flood"):
            irrigation = "Hold irrigation while soil is wet and keep drains clear." if not irr.get("needed") or irr.get("postpone") else irr.get("decision", "")
            planning = (f"Planning scenario: {adj['rationale'][-1]}" if adj["applied"] and adj["p_shift"]["Excess"] and r is _excess_risk(risks) else
                        "Watch only - below the High level needed to switch on an excess-rain planning scenario." if r is _excess_risk(risks) else
                        "Covered by the excess-rain indicator.")
        else:
            irrigation = irr.get("decision", "") if key == "heat" else ""
            planning = NOT_MODELLED
        out.append({"key": key, "title": r["name"], "category": r["category"], "score": r["score"], "level": LEVEL[r["category"]],
                    "indicators": [d for d, _ in r["factors"][:3]], "what": r["what"], "action": r["action"], "irrigation": irrigation, "planning": planning,
                    "affects_optimizer": key in ("drought", "rain", "flood") and planning.startswith("Planning scenario")})
    return out


def shifted_probs(base_pct, shift):
    """Move probability mass (in % points) from Normal to Drought/Excess, then renormalise. base_pct: {'Normal','Drought','Excess'}."""
    p = {k: float(v) for k, v in base_pct.items()}
    p["Drought"] += shift.get("Drought", 0); p["Excess"] += shift.get("Excess", 0)
    p["Normal"] = max(0.0, p["Normal"] - shift.get("Drought", 0) - shift.get("Excess", 0))
    s = sum(p.values())
    return {k: v / s * 100 for k, v in p.items()} if s > 0 else base_pct


def compare_plans(crops_df, area, budget, water, probs_pct, severity, rain_change, seed, n, assum, priority, min_frac, max_frac, adj):
    """Original plan vs risk-aware plan. Both use the SAME CVaR optimiser; only the scenario set and water availability differ.
    Also scores the ORIGINAL allocation on the risk scenarios, i.e. 'what if we keep the old plan and the risk happens'."""
    assum = {**DEFAULT_ASSUMPTIONS, **(assum or {})}
    sim0 = generate_scenarios(n, probs_pct, severity, rain_change, seed)
    probs1 = shifted_probs(probs_pct, adj["p_shift"])
    sim1 = generate_scenarios(n, probs1, severity, (1 + rain_change) * (1 + adj["rain_change"]) - 1, seed)
    water1 = water * adj["water_mult"]
    p0 = optimize(crops_df, area, budget, water, sim0, assum, priority, min_frac, max_frac)
    p1 = optimize(crops_df, area, budget, water1, sim1, assum, priority, min_frac, max_frac)
    if not p0["ok"] or not p1["ok"]:
        return {"ok": False, "message": (p1 if not p1["ok"] else p0)["message"]}
    M1 = build_matrices(crops_df, sim1, assum)
    x0 = np.array([p0["allocation"][c] for c in crops_df["crop"]])
    keep = evaluate_plan(x0, M1, water1, assum["alpha"])
    return {"ok": True, "crops": list(crops_df["crop"]), "adj": adj, "water0": water, "water1": water1, "probs0": probs_pct, "probs1": probs1,
            "original": p0["metrics"], "original_under_risk": keep, "risk_aware": p1["metrics"],
            "alloc0": p0["allocation"], "alloc1": p1["allocation"], "sim1": sim1, "priority": priority,
            "original_needs_more_water": bool(M1["plan_w"] @ x0 > water1 + 1e-6)}


def explain_comparison(res):
    """Plain-language summary built only from the computed comparison."""
    if not res["ok"]:
        return res["message"]
    o, k, r = res["original"], res["original_under_risk"], res["risk_aware"]
    moved = [(c, res["alloc1"][c] - res["alloc0"][c]) for c in res["crops"] if abs(res["alloc1"][c] - res["alloc0"][c]) >= 0.05]
    mv = "; ".join(f"{c} {d:+.1f} acres" for c, d in sorted(moved, key=lambda t: -abs(t[1]))) or "no change in the crop mix"
    t = (f"Re-planning for this risk scenario shifts the mix: {mv}. If the original plan is kept and the risk scenario happens, average profit is Rs {k['expected_profit']:,.0f} "
         f"(worst-10% Rs {k['cvar']:,.0f}); the risk-aware plan gives Rs {r['expected_profit']:,.0f} (worst-10% Rs {r['cvar']:,.0f}), "
         f"a difference of Rs {r['expected_profit'] - k['expected_profit']:+,.0f} on average and Rs {r['cvar'] - k['cvar']:+,.0f} in bad seasons. "
         f"Expected extra irrigation moves from {k['expected_water_m3']:,.0f} to {r['expected_water_m3']:,.0f} m3 and investment from Rs {k['investment']:,.0f} to Rs {r['investment']:,.0f}.")
    if res["original_needs_more_water"]:
        t += " The original plan needs more planned irrigation water than the reduced supply allows."
    return t + " Scenario sizes are stated assumptions and the results are simulations, not forecasts or guarantees."
