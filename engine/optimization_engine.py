"""FarmOptimizer - robust crop-mix optimisation (independent of the AgroCast hazard scores).

Per-acre outcome in simulated scenario s for crop j (FAO-33 water-production function):
    ETa  = min(ETm, eff*R_n*m_s + I_plan)           I_plan = max(0, ETm - eff*R_n)  (irrigation planned for a NORMAL year)
    Y_ws = 1 - Ky*(1 - ETa/ETm)                      water-stress factor
    Y_wl = 1 - W_j*clip((m_s-1.3)/0.7, 0, 1)         waterlogging factor from excess rain
    profit_js = Ym*Y_ws*Y_wl*price - cost
LP (Rockafellar-Uryasev CVaR), x_j = acres of crop j:
    max (1-L)*mean_s(a_s.x) + L*CVaR_alpha(a_s.x)   s.t. sum x<=area, cost.x<=budget, water_plan.x<=water, lo<=x<=hi
    CVaR via z - 1/(alpha*S) * sum(u_s),  u_s >= z - a_s.x,  u_s >= 0.
L=0 -> max expected profit; L=1 -> pure downside protection. Everything is linear -> solved exactly by HiGHS (scipy)."""
import numpy as np
import pandas as pd
from scipy.optimize import linprog
from scipy.sparse import csr_matrix, hstack, identity

MM_TO_M3 = 4.0469
DEFAULT_ASSUMPTIONS = {"eff_rain": 0.75, "irrig_eff": 0.70, "cost_mult": 1.0, "price_mult": 1.0, "alpha": 0.10,
                       "normal_rain": {"kharif": 870.0, "rabi": 120.0}}   # kharif ~ all-India monsoon LPA 87 cm (IMD); rabi illustrative
PRIORITY_LAMBDA = {"profit": 0.0, "balanced": 0.5, "risk": 0.85}


def normal_rain_for(crop, assum):
    nr = assum["normal_rain"]
    return nr["kharif"] + nr["rabi"] if crop["season"] == "annual" else nr[crop["season"]]


def crop_outcomes(crop, mult, assum):
    """Per-acre arrays over scenarios: dict(profit, yield_q, water_m3) + scalars (plan_water_m3, cost)."""
    mult = np.asarray(mult, float)
    etm, rn = crop["etm_mm"], normal_rain_for(crop, assum)
    eff_n = assum["eff_rain"] * rn
    i_plan = max(0.0, etm - eff_n)
    eff_s = assum["eff_rain"] * rn * mult
    applied = np.minimum(i_plan, np.maximum(0.0, etm - eff_s))
    eta = np.minimum(etm, eff_s + applied)
    ws = np.clip(1 - crop["ky"] * (1 - eta / etm), 0, 1)
    wl = 1 - crop["waterlog_sens"] * np.clip((mult - 1.3) / 0.7, 0, 1)
    y = crop["yield_q_acre"] * ws * wl
    cost = crop["cost_per_acre"] * assum["cost_mult"]
    return {"yield_q": y, "profit": y * crop["price_per_q"] * assum["price_mult"] - cost,
            "water_m3": applied / assum["irrig_eff"] * MM_TO_M3,
            "plan_water_m3": i_plan / assum["irrig_eff"] * MM_TO_M3, "cost": cost, "i_plan_mm": i_plan}


def validate_inputs(crops, area, budget, water, min_frac, max_frac):
    if crops is None or len(crops) == 0:
        raise ValueError("select at least one crop")
    if not (area > 0) or budget < 0 or water < 0:
        raise ValueError("area must be > 0; budget and water must be >= 0")
    for k, (lo, hi) in enumerate(zip(min_frac, max_frac)):
        if lo < 0 or hi > 1 or lo > hi:
            raise ValueError("min/max allocation fractions must satisfy 0 <= min <= max <= 1")
    if sum(min_frac) > 1 + 1e-9:
        raise ValueError("minimum allocations add up to more than 100% of the land")


def build_matrices(crops_df, sim, assum):
    outs = [crop_outcomes(r, sim["rain_mult"].values, assum) for _, r in crops_df.iterrows()]
    return {"A": np.column_stack([o["profit"] for o in outs]), "Y": np.column_stack([o["yield_q"] for o in outs]),
            "W": np.column_stack([o["water_m3"] for o in outs]), "plan_w": np.array([o["plan_water_m3"] for o in outs]),
            "cost": np.array([o["cost"] for o in outs])}


def _solve(M, area, budget, water, lo, hi, lam, alpha, water_obj=False, profit_floor=None):
    A, S, n = M["A"], M["A"].shape[0], M["A"].shape[1]
    if water_obj:                                     # minimise expected water subject to profit floor
        c = np.concatenate([M["W"].mean(0), [0.0], np.zeros(S)])
    else:
        c = np.concatenate([-(1 - lam) * A.mean(0), [-lam], np.full(S, lam / (alpha * S))])
    rows = [csr_matrix(hstack([-csr_matrix(A), csr_matrix(np.ones((S, 1))), -identity(S)]))]
    rhs = [np.zeros(S)]
    def add(vec, b):
        rows.append(csr_matrix(np.concatenate([vec, np.zeros(1 + S)])[None, :])); rhs.append([b])
    add(np.ones(n), area); add(M["cost"], budget); add(M["plan_w"], water)
    if profit_floor is not None:
        add(-A.mean(0), -profit_floor)
    from scipy.sparse import vstack
    bounds = [(lo[j] * area, hi[j] * area) for j in range(n)] + [(None, None)] + [(0, None)] * S
    res = linprog(c, A_ub=vstack(rows).tocsr(), b_ub=np.concatenate([np.ravel(r) for r in rhs]), bounds=bounds, method="highs")
    return res


def evaluate_plan(x, M, available_water=None, alpha=0.10):
    """Metrics for allocation x (acres per crop) over all simulated scenarios."""
    x = np.asarray(x, float)
    profit = M["A"] @ x
    thr = np.quantile(profit, alpha)
    tail = profit[profit <= thr]
    pot = M["Y"].max(0)  # observed best-case yield per crop in the simulation
    idx = (M["Y"] @ x) / max(float(pot @ x), 1e-9)
    water = M["W"] @ x
    mean = float(profit.mean())
    cvar = float(tail.mean()) if len(tail) else float(profit.min())
    p_loss = float((profit < 0).mean())
    # Climate Resilience Score (0-100): 35% no-loss probability, 30% downside retention (CVaR/mean),
    # 20% yield stability (1-CV of yield index), 15% water safety (1 - expected use / available water)
    ret = np.clip(cvar / mean, 0, 1) if mean > 0 else 0.0
    cv = float(idx.std() / idx.mean()) if idx.mean() > 0 else 1.0
    ws = 1 - min(float(water.mean()) / available_water, 1.0) if available_water and available_water > 0 else 0.0
    score = 100 * (0.35 * (1 - p_loss) + 0.30 * ret + 0.20 * (1 - min(cv, 1)) + 0.15 * ws) if x.sum() > 0 else 0.0
    return {"expected_profit": mean, "profit_std": float(profit.std()), "p5_profit": float(np.quantile(profit, 0.05)),
            "worst_profit": float(profit.min()), "cvar": cvar, "p_loss": p_loss, "expected_water_m3": float(water.mean()),
            "yield_cv": cv, "investment": float(M["cost"] @ x), "resilience": round(score, 1), "acres_used": float(x.sum())}


def optimize(crops_df, area, budget, water, sim, assum=None, priority="balanced", min_frac=None, max_frac=None,
             water_floor_share=0.7):
    """Return dict(ok, message, allocation(acres per crop), metrics, matrices). Never raises for infeasible problems."""
    assum = {**DEFAULT_ASSUMPTIONS, **(assum or {})}
    n = len(crops_df)
    min_frac = [0.0] * n if min_frac is None else list(min_frac)
    max_frac = [1.0] * n if max_frac is None else list(max_frac)
    validate_inputs(crops_df, area, budget, water, min_frac, max_frac)
    if priority not in list(PRIORITY_LAMBDA) + ["water"]:
        raise ValueError("priority must be profit, balanced, risk or water")
    M = build_matrices(crops_df, sim, assum)
    alpha = assum["alpha"]
    if priority == "water":
        base = _solve(M, area, budget, water, min_frac, max_frac, 0.0, alpha)
        if base.status != 0:
            return {"ok": False, "message": "No feasible plan: " + base.message, "matrices": M}
        p_star = float((M["A"].mean(0) * base.x[:n]).sum())
        floor = water_floor_share * p_star if p_star > 0 else p_star
        res = _solve(M, area, budget, water, min_frac, max_frac, 0.0, alpha, water_obj=True, profit_floor=floor)
    else:
        res = _solve(M, area, budget, water, min_frac, max_frac, PRIORITY_LAMBDA[priority], alpha)
    if res.status != 0:
        return {"ok": False, "message": "No feasible plan under these constraints (check budget, water, minimum allocations).", "matrices": M}
    x = np.clip(res.x[:n], 0, None)
    x[x < 1e-6] = 0.0
    alloc = dict(zip(crops_df["crop"], x))
    return {"ok": True, "message": "optimal", "priority": priority, "allocation": alloc,
            "metrics": evaluate_plan(x, M, water, alpha), "matrices": M, "crops": list(crops_df["crop"])}


def compare_strategies(crops_df, area, budget, water, sim, assum=None, min_frac=None, max_frac=None):
    """Table of optimised priorities + naive baselines (even split, each single crop) evaluated on the same scenarios."""
    assum = {**DEFAULT_ASSUMPTIONS, **(assum or {})}
    rows, plans = [], {}
    for pr in ["profit", "balanced", "risk", "water"]:
        r = optimize(crops_df, area, budget, water, sim, assum, pr, min_frac, max_frac)
        if r["ok"]:
            plans[f"Optimised: {pr}"] = r
    M = build_matrices(crops_df, sim, assum)
    n = len(crops_df)
    def cap(j):  # largest feasible single-crop area
        lim = [area, budget / M["cost"][j] if M["cost"][j] > 0 else area, water / M["plan_w"][j] if M["plan_w"][j] > 0 else area]
        return max(min(lim), 0.0)
    even = np.full(n, 1.0 / n) * area
    scale = min(1.0, budget / max(M["cost"] @ even, 1e-9), water / max(M["plan_w"] @ even, 1e-9) if M["plan_w"] @ even > 0 else 1.0)
    base = {"Baseline: even split": even * scale}
    for j, name in enumerate(crops_df["crop"]):
        x = np.zeros(n); x[j] = cap(j); base[f"Baseline: only {name}"] = x
    for k, x in base.items():
        plans[k] = {"ok": True, "allocation": dict(zip(crops_df["crop"], x)), "metrics": evaluate_plan(x, M, water, assum["alpha"]), "matrices": M}
    for k, p in plans.items():
        rows.append({"strategy": k, **p["metrics"], **{f"acres_{c}": a for c, a in p["allocation"].items()}})
    return pd.DataFrame(rows), plans


def scenario_breakdown(plan, sim):
    """Mean profit per scenario label for a plan (shows who wins in drought vs excess)."""
    x = np.array([plan["allocation"][c] for c in plan["crops"]]) if "crops" in plan else np.array(list(plan["allocation"].values()))
    p = plan["matrices"]["A"] @ x
    return pd.DataFrame({"scenario": sim["scenario"].values, "profit": p}).groupby("scenario").profit.agg(["mean", "min", "count"])


def crop_economics_table(crops_df, assum=None, mults=(("Drought", 0.7), ("Normal", 1.0), ("Excess", 1.35))):
    """Per-acre transparent economics by crop: cost, break-even yield, profit under 3 fixed rainfall multipliers."""
    assum = {**DEFAULT_ASSUMPTIONS, **(assum or {})}
    rows = []
    for _, c in crops_df.iterrows():
        o = crop_outcomes(c, [m for _, m in mults], assum)
        row = {"crop": c["crop"], "cost/acre": o["cost"], "break-even yield (q/acre)": o["cost"] / (c["price_per_q"] * assum["price_mult"]),
               "irrigation planned (m3/acre)": o["plan_water_m3"]}
        for (nme, _), pr, y in zip(mults, o["profit"], o["yield_q"]):
            row[f"profit {nme}"], row[f"yield {nme}"] = pr, y
        rows.append(row)
    return pd.DataFrame(rows)
