"""Plain-language outputs: alerts (AgroCast) and strategy explanations (FarmOptimizer). Text is built only from computed values."""
import numpy as np


def generate_alerts(wx, crop, risks, irrigation, source_label):
    """Alerts derived from actual input data. source_label is shown with each alert (e.g. 'Open-Meteo' or 'SAMPLE (synthetic)')."""
    f = wx[wx.kind == "forecast"].head(7)
    al = []
    hot = f[f.tmax > crop["heat_c"]]
    if len(hot) >= 1:
        al.append(("warning" if len(hot) < 3 else "critical",
                   f"High temperature expected on {len(hot)} of the next {len(f)} days (up to {f.tmax.max():.0f}°C, {crop['crop']} threshold {crop['heat_c']}°C). Monitor soil moisture and consider irrigation in cool hours."))
    heavy = f[f.rain_mm >= crop["heavy_rain_mm"]]
    if len(heavy):
        al.append(("critical", f"Heavy rainfall forecast ({f.rain_mm.max():.0f} mm in one day). Avoid unnecessary irrigation and check field drainage."))
    elif f.rain_mm.sum() >= 50:
        al.append(("warning", f"{f.rain_mm.sum():.0f} mm rain forecast this week. Skip irrigation if soil is moist and keep drains clear."))
    if (f.tmin < crop["cold_c"]).any():
        al.append(("warning", f"Cold night(s) forecast (minimum {f.tmin.min():.0f}°C, crop threshold {crop['cold_c']}°C)."))
    if irrigation.get("needed") and not irrigation.get("postpone"):
        al.append(("warning", irrigation["decision"]))
    if irrigation.get("postpone"):
        al.append(("info", irrigation["decision"]))
    if risks["fungal"]["score"] >= 50:
        al.append(("warning", "Weather is favourable for leaf diseases. Scout the field; consult your agriculture officer before spraying."))
    if not al:
        al.append(("ok", "No significant weather hazards detected for the next 7 days."))
    return [{"level": l, "message": m, "basis": f"Weather source: {source_label}"} for l, m in al]


def risk_explanation(r):
    """what / why / which factors / next step - for any risk dict from climate_risk."""
    fac = "; ".join(f"{d} (+{p:g} pts)" for d, p in r["factors"]) or "no contributing factors above zero"
    return {"predicted": f"{r['name']}: {r['category']} ({r['score']:.0f}/100).", "why": r["what"], "factors": fac, "next": r["action"]}


def explain_plan(plan, table_row_baseline=None, priority="balanced"):
    """Short farmer-friendly explanation of an optimised plan."""
    if not plan["ok"]:
        return plan["message"]
    m, alloc = plan["metrics"], {k: v for k, v in plan["allocation"].items() if v > 0.01}
    mix = ", ".join(f"{a:.1f} acres {c}" for c, a in alloc.items()) or "no crop (not profitable under these limits)"
    goal = {"profit": "highest average profit", "balanced": "a balance of profit and protection against bad years",
            "risk": "protection against bad years", "water": "low water use while keeping about 70% of the best average profit"}[priority]
    t = (f"Suggested mix: {mix}. It is chosen for {goal}. Across the simulated seasons the average profit is Rs {m['expected_profit']:,.0f}; "
         f"in the worst 10% of seasons it averages Rs {m['cvar']:,.0f}; chance of losing money is {m['p_loss']*100:.0f}%; "
         f"expected extra irrigation is {m['expected_water_m3']:,.0f} m3. Resilience score {m['resilience']:.0f}/100.")
    if table_row_baseline is not None:
        t += f" Compared with the best single-crop baseline, the worst-10% profit is Rs {m['cvar'] - table_row_baseline:+,.0f} different."
    return t + " These are simulated estimates, not guarantees."
