"""AgroCast - transparent, crop- and stage-specific hazard scoring (0-100).
Each score = 100 x stage_sensitivity x sum(weight_i x factor_i); factors are 0-1 normalised weather features.
Heuristic and unvalidated against yield-loss data: scores rank EXPOSURE, they are not probabilities of loss.
Fungal score is a generic leaf-wetness/temperature heuristic, NOT a validated disease-forecast model."""
import numpy as np
from .crop_database import STAGE_SENS, SOILS
from .irrigation_engine import project_moisture

CATEGORIES = [(25, "Low"), (50, "Moderate"), (75, "High"), (101, "Severe")]


def categorize(score: float) -> str:
    return next(n for t, n in CATEGORIES if score < t)


def _result(key, name, parts, what, actions, extra=None):
    """parts: list of (description, points). Score = sum(points), clipped 0-100."""
    score = float(np.clip(sum(p for _, p in parts), 0, 100))
    r = {"key": key, "name": name, "score": round(score, 1), "category": categorize(score), "what": what,
         "factors": sorted([(d, round(p, 1)) for d, p in parts if p > 0.05], key=lambda x: -x[1]),
         "action": actions[categorize(score)]}
    r.update(extra or {})
    return r


def _fc(wx, n=7):
    f = wx[wx.kind == "forecast"].head(n)
    return f if len(f) else wx.tail(n)


def assess_risks(wx, crop, stage_idx, soil, measured_pct=None):
    """Return dict of six hazard results + 'overall' + 'features'. Raises ValueError for unusable input."""
    if wx is None or len(wx) == 0:
        raise ValueError("no weather data")
    if soil not in SOILS:
        raise ValueError(f"unknown soil {soil}")
    si = max(stage_idx, 0)
    S = {k: STAGE_SENS[k][si] for k in STAGE_SENS}
    f, obs = _fc(wx), wx[wx.kind == "observed"].tail(14)
    drain = SOILS[soil][1]
    wl = max(float(crop["waterlog_sens"]), 0.15)
    out, n = {}, len(f)

    # 1 Heat stress: share of days above crop heat threshold + average exceedance
    over = np.maximum(f.tmax - crop["heat_c"], 0)
    a, b = float((f.tmax > crop["heat_c"]).mean()), float(np.clip(over.mean() / 5, 0, 1))
    k = 100 * S["heat"]
    out["heat"] = _result("heat", "Heat stress", [
        (f"{int((f.tmax > crop['heat_c']).sum())} of {n} forecast days above {crop['heat_c']}°C (max {f.tmax.max():.1f}°C)", k * .5 * a),
        (f"Average exceedance {over.mean():.1f}°C above threshold", k * .5 * b)],
        "Hot days can reduce flowering/grain or fruit set.",
        {"Low": "No action needed.", "Moderate": "Monitor field; irrigate in morning/evening.",
         "High": "Light irrigation in cool hours, avoid fertiliser/spray at midday, mulch if possible.",
         "Severe": "Protect flowering crop: frequent light irrigation, mulching, shade/antitranspirant advice from local KVK."})

    # 2 Cold stress
    short = np.maximum(crop["cold_c"] - f.tmin, 0)
    a, b = float((f.tmin < crop["cold_c"]).mean()), float(np.clip(short.mean() / 4, 0, 1))
    k = 100 * S["cold"]
    out["cold"] = _result("cold", "Cold stress", [
        (f"{int((f.tmin < crop['cold_c']).sum())} of {n} forecast nights below {crop['cold_c']}°C (min {f.tmin.min():.1f}°C)", k * .5 * a),
        (f"Average shortfall {short.mean():.1f}°C", k * .5 * b)],
        "Cold nights slow growth and can damage flowers.",
        {"Low": "No action needed.", "Moderate": "Watch night temperatures.",
         "High": "Light evening irrigation and smoke/cover for sensitive plots.", "Severe": "Cover nursery/young plants; irrigate before cold night."})

    # 3 Drought: from the bucket model (see irrigation_engine)
    proj, info = project_moisture(wx, crop, stage_idx, soil, measured_pct)
    pf = proj[proj.kind == "forecast"] if (proj.kind == "forecast").any() else proj
    buf = min((1 - crop["p_depl"]) + 0.1, 1.0)
    dry = float(np.clip((buf - pf.frac.min()) / buf, 0, 1))
    days_str = int(pf.stressed.sum())
    out["drought"] = _result("drought", "Drought / moisture stress", [
        (f"Lowest projected root-zone water {pf.frac.min()*100:.0f}% of capacity (stress below {info['threshold_frac']*100:.0f}%)", 100 * S["drought"] * .8 * dry),
        (f"{days_str} projected stress day(s) in forecast window", 100 * S["drought"] * .2 * min(days_str / 5, 1))],
        "Soil may not hold enough water for the crop (unmitigated - before any irrigation).",
        {"Low": "Moisture adequate.", "Moderate": "Check soil by hand; prepare to irrigate.",
         "High": "Irrigate within 1-3 days if source available (see Irrigation Advisor).", "Severe": "Irrigate immediately if possible; protect flowering stage."},
        {"estimated_moisture": info["estimated"]})

    # 4 Excess rainfall (cumulative) and 5 Flooding/waterlogging indicator (daily extreme + wet run)
    r7, r14 = float(f.rain_mm.sum()), float(obs.rain_mm.sum())
    mult = 0.7 + 0.6 * drain
    k = 100 * S["rain"] * wl * mult
    out["rain"] = _result("rain", "Excess rainfall", [
        (f"{r7:.0f} mm forecast in next {n} days", k * .65 * min(r7 / 150, 1)),
        (f"{r14:.0f} mm already fell in last 14 days (wet soil)", k * .35 * min(r14 / 300, 1))],
        "Too much rain can waterlog roots and wash away nutrients.",
        {"Low": "No action needed.", "Moderate": "Skip irrigation; check drains.",
         "High": "Clear drainage channels, delay fertiliser/spray, avoid irrigation.", "Severe": "Open drains now, delay all field operations, plan for replanting/support."})
    mx = float(f.rain_mm.max())
    run = best = 0
    for v in f.rain_mm:
        run = run + 1 if v >= 10 else 0
        best = max(best, run)
    k = 100 * S["flood"] * wl * mult
    out["flood"] = _result("flood", "Flooding / waterlogging indicator", [
        (f"Heaviest day {mx:.0f} mm (heavy-rain level {crop['heavy_rain_mm']} mm)", k * .55 * min(mx / crop["heavy_rain_mm"], 1)),
        (f"{best} consecutive wet day(s) (>=10 mm)", k * .25 * min(best / 4, 1))],
        "Indicator of standing-water risk (soil drainage factor %.1f)." % drain,
        {"Low": "No action needed.", "Moderate": "Keep drains clear.", "High": "Prepare drainage; avoid low-lying sowing/transplanting.",
         "Severe": "Drain field before the rain event; move inputs/produce to higher ground."})

    # 6 Fungal-favourable conditions (heuristic)
    w = wx[(wx.kind == "forecast")].head(7)
    w = w if len(w) else wx.tail(7)
    tmean = (w.tmax + w.tmin) / 2
    humid = (w.rh_mean >= 85) if w.rh_mean.notna().any() else (w.rain_mm >= 1)
    proxy = not w.rh_mean.notna().any()
    cond = (humid & (tmean >= crop["fungal_tmin"]) & (tmean <= crop["fungal_tmax"])).to_numpy()
    run = best = 0
    for c in cond:
        run = run + 1 if c else 0
        best = max(best, run)
    k = 100 * S["fungal"]
    out["fungal"] = _result("fungal", "Fungal-disease-favourable weather", [
        (f"{int(cond.sum())} of {len(w)} days humid{' (rain used as proxy)' if proxy else ' (RH>=85%)'} and {crop['fungal_tmin']}-{crop['fungal_tmax']}°C", k * .6 * cond.mean()),
        (f"Longest favourable run: {best} day(s)", k * .4 * min(best / 5, 1))],
        "Warm, humid, wet spells favour many leaf diseases. This is a weather-condition heuristic, not a validated disease forecast.",
        {"Low": "No action needed.", "Moderate": "Scout fields for leaf spots.", "High": "Scout daily; consult KVK/agri officer before any spray.",
         "Severe": "Scout immediately; follow local expert advice on preventive protection."})
    top = max(out.values(), key=lambda r: r["score"])
    out["overall"] = {"score": top["score"], "category": top["category"], "driver": top["name"]}
    out["features"] = {"rain7": r7, "rain14_obs": r14, "tmax7": float(f.tmax.max()), "tmin7": float(f.tmin.min()), "imputed_rows": int(wx.imputed.sum()) if "imputed" in wx else 0}
    return out
