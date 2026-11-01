import numpy as np
import pandas as pd
import streamlit as st
from engine.crop_database import load_crops
from engine.scenario_generator import generate_scenarios
from engine.optimization_engine import DEFAULT_ASSUMPTIONS, compare_strategies, scenario_breakdown
from engine.recommendation_engine import explain_plan
from engine.unified_intelligence import scenario_adjustment, interpret, compare_plans, explain_comparison, ASSUMPTION_TEXT
from utils import charts, ui
from utils.helpers import inr

LABEL = {"profit": "Highest profit", "water": "Least water", "risk": "Lowest risk", "balanced": "Balanced"}


def render(ctx):
    ui.banner("farmopt", "FarmOptimizer", "Which crop mix holds up across good and bad seasons? The seasons are simulated, not forecasts, and are separate from the AgroCast scores.")
    crops = st.session_state.get("crops_df", load_crops())
    f = ctx["farm"]
    a, b = st.columns([3, 2], gap="large")
    pick = a.multiselect("Crops to compare", list(crops.crop), key="opt_pick", default=[x for x in ["Maize", "Soybean", "Groundnut", "Rice"] if x in set(crops.crop)])
    priority = a.radio("What matters most?", list(LABEL), format_func=LABEL.get, horizontal=True, index=3)
    c1, c2, c3 = b.columns(3)
    area = c1.number_input("Land (acres)", 0.1, 5000.0, float(f["area_acres"]), 0.5)
    budget = c2.number_input("Budget (Rs)", 0.0, 1e8, float(f["budget"]), 1000.0)
    water_pct = c3.slider("Water (% of entered)", 0, 150, 100)
    water = f["water_m3"] * water_pct / 100
    with st.expander("What-ifs and scenario settings"):
        a, b, c = st.columns(3)
        rain_chg = a.slider("What-if: rainfall change (%)", -50, 50, 0)
        cost_chg = b.slider("What-if: cultivation cost change (%)", -20, 50, 0)
        sev = c.slider("Scenario severity", 0.5, 1.5, 1.0, 0.1)
        a, b, c = st.columns(3)
        pn, pd_, pe = a.slider("P(normal) %", 0, 100, 60), b.slider("P(drought) %", 0, 100, 20), c.slider("P(excess rain) %", 0, 100, 20)
        a, b, c = st.columns(3)
        kh, rb = a.number_input("Normal kharif rainfall (mm)", 0.0, 4000.0, 870.0), b.number_input("Normal rabi rainfall (mm)", 0.0, 2000.0, 120.0)
        n = c.select_slider("Simulations", [200, 500, 1000, 2000, 5000], 1000)
        seed = a.number_input("Random seed", 0, 10**6, 42)
        lim = st.checkbox("Set min/max share of land per crop")
        mn, mx = [0.0] * len(pick), [1.0] * len(pick)
        if lim:
            for i, cname in enumerate(pick):
                mn[i], mx[i] = [v / 100 for v in st.slider(f"{cname} share of land (%)", 0, 100, (0, 100), key=f"lim_{cname}")]
    if not pick: ui.empty_state("Select at least one crop", "Pick the crops you want FarmOptimizer to compare in the box above.", "🌱"); return
    if pn + pd_ + pe == 0: ui.callout("error", "Scenario probabilities cannot all be zero", "", "Raise at least one of P(normal), P(drought) or P(excess rain) under What-ifs and scenario settings."); return
    assum = {**DEFAULT_ASSUMPTIONS, "cost_mult": 1 + cost_chg / 100, "normal_rain": {"kharif": kh, "rabi": rb}}
    st.session_state["assum"] = assum
    sel = crops[crops.crop.isin(pick)].reset_index(drop=True)
    try:
        sim = generate_scenarios(n, {"Normal": pn, "Drought": pd_, "Excess": pe}, sev, rain_chg / 100, int(seed))
        table, plans = compare_strategies(sel, area, budget, water, sim, assum, mn, mx)
    except ValueError as e:
        ui.callout("error", "Could not run the simulation", str(e), "Adjust the scenario settings and try again."); return
    key = f"Optimised: {priority}"
    plan = plans.get(key)
    if plan is None:
        ui.callout("error", "No feasible plan under these constraints", "The land, budget, water and share limits cannot all be met together.", "Increase budget or water, or relax the minimum crop shares."); return
    plan["priority"] = priority
    st.session_state["optim"], st.session_state["compare"] = plan, table
    t1, t2, t3, t4, t5, t6 = st.tabs(["Recommended strategy", "Strategy comparison", "Simulation", "Math & assumptions", "AgroCast-informed plan", "Farm layout"])
    m = plan["metrics"]
    with t1:
        base = table[table.strategy.str.startswith("Baseline")].cvar.max()
        st.markdown(ui.note("info", explain_plan({**plan, "ok": True}, base, priority)), unsafe_allow_html=True)
        plan["crops"] = list(plan["allocation"])
        _dashboard(plan, plans, sim, f, area, budget, water, pick, assum, {"Normal": pn, "Drought": pd_, "Excess": pe}, sev, n)
    with t2:
        show = table[["strategy", "expected_profit", "cvar", "p5_profit", "p_loss", "expected_water_m3", "yield_cv", "investment", "resilience"]].round(2)
        ui.table(show)
        ui.chart(charts.strategy_scatter(table))
    with t3:
        st.caption(sim.attrs.get("data_type", "SIMULATED"))
        ui.chart(charts.profit_hist(plan, {k: v for k, v in plans.items() if k.startswith("Optimised")}))
        ui.table(sim.groupby("scenario").rain_mult.describe().round(2).reset_index())
    with t4:
        st.markdown(r"""
**Yield (FAO-33):** ETa = min(ETm, η·Rₙ·m + I_plan);  Y = Ym·[1 − Ky(1 − ETa/ETm)]·[1 − W·clip((m−1.3)/0.7, 0, 1)]  
**Profit:** Y·price − cost.  **LP:** maximise (1−λ)·E[π] + λ·CVaR₁₀%(π) s.t. land, budget, planned-irrigation-water and min/max-share constraints (Rockafellar-Uryasev form, solved by HiGHS).  
λ = 0 (profit), 0.5 (balanced), 0.85 (risk). *Water* priority: minimise expected irrigation subject to ≥70% of max expected profit.  
**Resilience score** = 100·(0.35·(1−P(loss)) + 0.30·CVaR/mean + 0.20·(1−CV of yield index) + 0.15·water safety).  
Effective rain fraction 0.75, irrigation efficiency 0.70, crop values: illustrative - edit on *Crop Comparison*. Scenario means/SDs: Normal 1.00±0.12, Drought 0.70±0.12, Excess 1.35±0.15 (illustrative, editable in `engine/scenario_generator.py`).  
**Not modelled:** price volatility, sowing-date shifts, pests, labour. Results are simulations, not guarantees.""")
    with t5:
        _informed_tab(ctx, sel, area, budget, water, {"Normal": pn, "Drought": pd_, "Excess": pe}, sev, rain_chg / 100, int(seed), n, assum, priority, mn, mx)
    with t6:
        _layout_tab(plan, area, ctx)
    ui.footer()


def _layout_tab(plan, area, ctx):
    from utils import farm_layout
    ui.callout("info", "Illustrative layout, not a map", "Plot sizes are proportional to the acres in the recommended plan. Positions are arbitrary: no satellite imagery, GPS boundaries or real field shapes are used.")
    mode = st.radio("Colour plots by", ["Crop", "Irrigation zone", "Simulated crop risk"], horizontal=True, key="layout_mode")
    o = ctx["risks"]["overall"]
    ac = {"crop": ctx["farm"]["crop"], "category": o["category"]}
    ui.chart(farm_layout.farm_figure(plan, area, mode, ac))
    st.caption({"Crop": "Each colour is one crop.", "Irrigation zone": "Zones rank crops by planned irrigation per acre relative to the thirstiest crop in this plan; 'Rain-fed' means no irrigation is planned in a normal year.",
                "Simulated crop risk": "Based on the share of simulated seasons with a loss for that crop (Low <10%, Moderate <25%, High <50%, Severe otherwise). These are simulations, not forecasts. AgroCast's live weather risk is shown in the hover for the crop selected in the sidebar."}[mode])
    ui.chart(farm_layout.resource_shares(plan, area))
    ui.footer()


def _delta(a, b, higher_better=True, fmt=lambda v: f"{v:,.0f}", unit=""):
    d = b - a
    if abs(d) < 1e-9:
        return "no change"
    good = (d > 0) == higher_better
    return f"{'▲' if d > 0 else '▼'} {fmt(abs(d))}{unit} ({'better' if good else 'worse'})"


def _dashboard(plan, plans, sim, f, area, budget, water, pick, assum, probs, sev, n):
    """Premium farm-planning dashboard: farm summary, KPIs, allocation, baseline-vs-optimized comparison and visible assumptions.
    Uses only numbers already produced by the existing optimiser; nothing is re-computed or re-optimised here."""
    m, M = plan["metrics"], plan["matrices"]
    x = np.array(list(plan["allocation"].values()))
    used = [c for c, a in plan["allocation"].items() if a > 0.01]
    planned_water = float(M["plan_w"] @ x)
    base = plans.get("Baseline: even split")
    ui.section("Your farm plan at a glance")
    ui.html(ui.chips([("Farm area", f"{area:.1f} acres"), ("Crops considered", str(len(pick))), ("Crops in plan", ", ".join(used) or "none"),
                      ("Land planted", f"{m['acres_used'] / area * 100:.0f}%"), ("Budget", inr(budget)), ("Irrigation water cap", f"{water:,.0f} m³")]))
    col_loss = "#b04030" if m["p_loss"] > .25 else "#c79a2b" if m["p_loss"] > .1 else "#2f6b40"
    col_res = "#2f6b40" if m["resilience"] >= 70 else "#c79a2b" if m["resilience"] >= 50 else "#b04030"
    k = st.columns(4)
    k[0].markdown(ui.kpi("Expected profit", inr(m["expected_profit"]), f"Average over {len(sim):,} simulated seasons"), unsafe_allow_html=True)
    k[1].markdown(ui.kpi("Worst-case simulated profit", inr(m["worst_profit"]), f"Single worst run · worst-10% average {inr(m['cvar'])}"), unsafe_allow_html=True)
    k[2].markdown(ui.kpi("Probability of simulated loss", f"{m['p_loss'] * 100:.0f}%", "Share of simulated seasons with profit below zero", col_loss), unsafe_allow_html=True)
    k[3].markdown(ui.kpi("Resilience score", f"{m['resilience']:.0f}/100", "Blend of loss chance, downside, yield stability, water", col_res), unsafe_allow_html=True)
    k = st.columns(4)
    k[0].markdown(ui.kpi("Estimated investment", inr(m["investment"]), f"{m['investment'] / budget * 100:.0f}% of budget" if budget > 0 else "No budget entered"), unsafe_allow_html=True)
    k[1].markdown(ui.kpi("Water requirement", f"{planned_water:,.0f} m³", f"Planned irrigation · {planned_water / water * 100:.0f}% of cap · expected extra {m['expected_water_m3']:,.0f} m³" if water > 0 else "No irrigation water entered"), unsafe_allow_html=True)
    k[2].markdown(ui.kpi("Yield variability (CV)", f"{m['yield_cv']:.2f}", "Spread of the yield index across seasons; lower is steadier"), unsafe_allow_html=True)
    k[3].markdown(ui.kpi("Land planted", f"{m['acres_used']:.1f} ac", f"of {area:.1f} acres entered"), unsafe_allow_html=True)

    ui.section("Where the land goes")
    a, b = st.columns(2)
    with a:
        ui.chart(charts.allocation_donut(plan, area))
    with b:
        rows = []
        for j, (c, ac) in enumerate(plan["allocation"].items()):
            if ac > 0.01:
                rows.append({"Crop": c, "Acres": round(ac, 2), "Share of farm": f"{ac / area * 100:.0f}%", "Investment": inr(M["cost"][j] * ac), "Planned irrigation (m³)": round(float(M["plan_w"][j] * ac)),
                             "Expected profit": inr(float(M["A"][:, j].mean() * ac)), "Yield CV": round(float(M["Y"][:, j].std() / M["Y"][:, j].mean()), 2) if M["Y"][:, j].mean() > 0 else 0.0})
        ui.table(pd.DataFrame(rows))
        st.caption("Per-crop figures come from the same simulated seasons as the totals above. Expected profit per crop does not include diversification effects.")
    a, b = st.columns(2)
    with a:
        ui.chart(charts.crop_water_variability(plan))
    with b:
        ui.chart(charts.scenario_bars(scenario_breakdown(plan, sim)))

    ui.section("Baseline vs optimized")
    if base is None:
        ui.callout("info", "No baseline available", "The even-split baseline could not be evaluated for these inputs.")
    else:
        bm = base["metrics"]
        st.caption("Baseline = the same land split evenly across the selected crops (scaled down only if budget or water would otherwise be exceeded). Both plans are scored on the same simulated seasons.")
        spec = [("Expected profit", "expected_profit", True, inr, lambda v: inr(v)), ("Worst-10% average (CVaR)", "cvar", True, inr, lambda v: inr(v)),
                ("Worst simulated season", "worst_profit", True, inr, lambda v: inr(v)), ("Probability of loss", "p_loss", False, lambda v: f"{v * 100:.0f}%", lambda v: f"{v * 100:.0f}"),
                ("Resilience score", "resilience", True, lambda v: f"{v:.0f}/100", lambda v: f"{v:.0f}"), ("Expected extra irrigation (m³)", "expected_water_m3", False, lambda v: f"{v:,.0f}", lambda v: f"{v:,.0f}"),
                ("Yield variability (CV)", "yield_cv", False, lambda v: f"{v:.2f}", lambda v: f"{v:.2f}"), ("Investment", "investment", False, inr, lambda v: inr(v))]
        units = {"p_loss": " pts"}
        ui.table(pd.DataFrame({"Metric": [r[0] for r in spec], "Baseline (even split)": [r[3](bm[r[1]]) for r in spec], "Optimized": [r[3](m[r[1]]) for r in spec],
                               "Change": [_delta(bm[r[1]], m[r[1]], r[2], r[4], units.get(r[1], "")) for r in spec]}))
        a, b = st.columns([3, 2])
        with a:
            ui.chart(charts.baseline_vs_optimized(bm, m))
        with b:
            ui.chart(charts.profit_hist(plan, {"Baseline: even split": base, "Optimized plan": plan}))
        if m["cvar"] < bm["cvar"] and m["expected_profit"] < bm["expected_profit"]:
            ui.callout("warn", "Optimized plan does not beat the baseline here", "Your min/max shares or budget and water limits may be forcing the mix.", "Relax the share limits or raise the budget or water to give the optimizer room.")

    ui.section("Assumptions behind these numbers")
    ui.html(ui.chips([("Seasons", f"{n:,} simulated"), ("Mix", f"Normal {probs['Normal']}% · Drought {probs['Drought']}% · Excess {probs['Excess']}%"), ("Severity", f"x{sev:.1f}"),
                      ("Effective rain", f"{assum['eff_rain'] * 100:.0f}%"), ("Irrigation efficiency", f"{assum['irrig_eff'] * 100:.0f}%"), ("Downside tail", f"worst {assum['alpha'] * 100:.0f}%"),
                      ("Cost multiplier", f"x{assum['cost_mult']:.2f}"), ("Normal rain", f"{assum['normal_rain']['kharif']:.0f} mm kharif · {assum['normal_rain']['rabi']:.0f} mm rabi")]))
    with st.expander("What these results are, and are not", expanded=False):
        st.markdown("- **Simulated, not forecast.** Seasons are random draws around illustrative rainfall multipliers (Normal 1.00, Drought 0.70, Excess 1.35); they are not predictions for this year.\n"
                    "- **Crop yields, prices and costs are starting assumptions** from `data/crops.csv`; edit them on *Crop Comparison* and check them locally.\n"
                    "- **Optimisation is exact, not heuristic:** a CVaR linear programme solved by SciPy/HiGHS. The resilience score is a transparent weighted formula, not a trained model.\n"
                    "- **Not modelled:** price volatility, pests, labour, sowing-date shifts. Profit figures are not guarantees. See the *Math & assumptions* tab for the equations.")


def _informed_tab(ctx, sel, area, budget, water, probs, sev, rain_chg, seed, n, assum, priority, mn, mx):
    """Optional: run the SAME CVaR optimiser on a scenario set adjusted for this week's AgroCast risk, and compare with the plan above."""
    risks, irr = ctx["risks"], ctx["irr"]
    st.markdown("**Weather risk from AgroCast → planning scenario.** The heuristic risk scores are not probabilities; High/Severe categories switch on the stated, editable-in-code assumptions below.")
    adj = scenario_adjustment(risks)
    items = interpret(risks, irr, adj)
    ui.html(ui.insights(items))
    what_if = False
    if not adj["applied"]:
        ui.callout("info", "No High or Severe drought / excess-rain risk right now", "So no AgroCast-based planning scenario is triggered.", "You can still preview how a drought would change the plan.")
        what_if = st.checkbox("Preview a drought what-if (not from AgroCast)", key="whatif_drought")
        if what_if:
            sev_lvl = st.radio("What-if drought level", ["High", "Severe"], horizontal=True, key="whatif_level")
            adj = scenario_adjustment(risks, force_drought=sev_lvl)
    if not adj["applied"]:
        return
    for line in adj["rationale"]:
        st.caption(line)
    with st.expander("Assumptions behind the scenario"):
        st.markdown(ASSUMPTION_TEXT)
    res = compare_plans(sel, area, budget, water, probs, sev, rain_chg, seed, n, assum, priority, mn, mx, adj)
    if not res["ok"]:
        ui.callout("error", "No feasible risk-aware plan", res["message"], "Increase budget or water, or relax the minimum crop shares.")
        return
    st.session_state["unified"] = {**st.session_state.get("unified", {}), "comparison": {k: v for k, v in res.items() if k not in ("sim1",)}, "adjustment": adj}
    st.markdown(ui.note("info", explain_comparison(res), "Scenario: " + ("what-if preview" if adj["what_if"] else "derived from AgroCast category") + " · SIMULATED"), unsafe_allow_html=True)
    o, k, r = res["original"], res["original_under_risk"], res["risk_aware"]
    c = st.columns(4)
    c[0].metric("Expected profit", inr(r["expected_profit"]), inr(r["expected_profit"] - k["expected_profit"]) + " vs keeping old plan")
    c[1].metric("Worst-10% average", inr(r["cvar"]), inr(r["cvar"] - k["cvar"]) + " vs old plan")
    c[2].metric("Expected extra water", f"{r['expected_water_m3']:,.0f} m³", f"{r['expected_water_m3'] - k['expected_water_m3']:+,.0f} m³ vs old plan", delta_color="inverse")
    c[3].metric("Chance of loss", f"{r['p_loss'] * 100:.0f}%", f"{(r['p_loss'] - k['p_loss']) * 100:+.0f} pts vs old plan", delta_color="inverse")
    a, b = st.columns(2)
    with a:
        ui.chart(charts.plan_shift_bars(res))
    with b:
        ui.chart(charts.risk_outcome_bars(res))
    ui.table(pd.DataFrame({"": ["Original plan (normal assumptions)", "Original plan (risk scenario)", "Risk-aware plan (risk scenario)"],
                           "Expected profit": [inr(m["expected_profit"]) for m in (o, k, r)], "Worst-10% avg": [inr(m["cvar"]) for m in (o, k, r)],
                           "Chance of loss": [f"{m['p_loss'] * 100:.0f}%" for m in (o, k, r)], "Extra water m³": [f"{m['expected_water_m3']:,.0f}" for m in (o, k, r)],
                           "Investment": [inr(m["investment"]) for m in (o, k, r)], "Resilience": [f"{m['resilience']:.0f}/100" for m in (o, k, r)]}))
    st.caption(f"Water available: {res['water0']:,.0f} m³ normally, {res['water1']:,.0f} m³ in the risk scenario. Scenario mix (%): " +
               ", ".join(f"{k_} {v:.0f}" for k_, v in res["probs1"].items()) + " (was " + ", ".join(f"{k_} {v:.0f}" for k_, v in res["probs0"].items()) + ").")
