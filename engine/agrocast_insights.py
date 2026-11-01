"""AgroCast presentation logic: weather summary, day-by-day trend, prioritised what/why/do/when recommendations, growth-stage
progress and data-quality notes. Pure functions over the existing engine outputs - nothing here changes a risk score.
All recommendations are built from computed values; risk scores are heuristic exposure indicators, NOT probabilities
(the fungal score in particular is a weather-condition heuristic, not a disease probability)."""
from datetime import datetime
import pandas as pd
from .crop_database import STAGES, STAGE_BOUNDS, STAGE_SENS
from .climate_risk import assess_risks
from .irrigation_engine import day_label

HAZARDS = ("drought", "heat", "cold", "rain", "flood", "fungal")
PRIORITY = {"Severe": (1, "Act now", "critical"), "High": (2, "Plan within 1-3 days", "warning"), "Moderate": (3, "Monitor", "info")}


def forecast_days(wx, n=7):
    f = wx[wx.kind == "forecast"].head(n)
    return f if len(f) else wx.tail(n)


def weather_summary(wx, crop):
    """Headline + small facts for the coming week."""
    f = forecast_days(wx)
    wet, hot = f.loc[f.rain_mm.idxmax()], f.loc[f.tmax.idxmax()]
    hot_days = int((f.tmax > crop["heat_c"]).sum())
    cold_n = int((f.tmin < crop["cold_c"]).sum())
    rain = float(f.rain_mm.sum())
    bits = [f"{rain:.0f} mm rain over {len(f)} days" + (f", heaviest on {day_label(wet.date)} ({wet.rain_mm:.0f} mm)" if wet.rain_mm >= 1 else ", essentially dry"),
            f"highs {f.tmax.min():.0f}-{f.tmax.max():.0f}°C, lows {f.tmin.min():.0f}-{f.tmin.max():.0f}°C"]
    if hot_days:
        bits.append(f"{hot_days} day(s) above the {crop['heat_c']}°C heat threshold")
    if cold_n:
        bits.append(f"{cold_n} night(s) below {crop['cold_c']}°C")
    return {"headline": "This week: " + "; ".join(bits) + ".", "rain_total": rain, "tmax": float(f.tmax.max()), "tmin": float(f.tmin.min()),
            "et0_mean": float(f.et0_mm.mean()) if "et0_mm" in f else None, "hot_days": hot_days, "cold_nights": cold_n,
            "wettest": (wet.date, float(wet.rain_mm)), "hottest": (hot.date, float(hot.tmax))}


def daily_table(wx, crop, irr):
    """Per-day indicators against crop thresholds (not scores): heat margin, cold margin, rain, projected soil water."""
    f = forecast_days(wx).copy()
    f["heat_margin"] = f.tmax - crop["heat_c"]
    f["cold_margin"] = f.tmin - crop["cold_c"]
    proj = irr.get("projection")
    if proj is not None:
        pf = proj[proj.kind == "forecast"].set_index("date").frac
        f["soil_pct"] = [float(pf.get(d, float("nan"))) * 100 for d in f.date]
    else:
        f["soil_pct"] = float("nan")
    return f.reset_index(drop=True)


def risk_trend(wx, crop, stage_idx, soil, measured_pct=None):
    """Cumulative exposure as the week unfolds: re-runs the SAME assess_risks on the observed days plus the first k forecast days.
    Row k answers 'what would the score be if the window ended on forecast day k?' - a heuristic trend, not a forecast of risk."""
    obs, fc = wx[wx.kind == "observed"], wx[wx.kind == "forecast"].head(7)
    rows = []
    for k in range(1, len(fc) + 1):
        r = assess_risks(pd.concat([obs, fc.head(k)], ignore_index=True), crop, stage_idx, soil, measured_pct)
        rows.append({"date": fc.iloc[k - 1].date, "day": k, **{h: r[h]["score"] for h in HAZARDS}})
    return pd.DataFrame(rows)


def stage_progress(crop, stage_idx, das):
    """Growth-stage facts for the indicator card (generic stage split of the crop duration; not a phenology model)."""
    dur = int(crop["duration_days"])
    if stage_idx < 0:
        return {"sown": False, "days_to_sowing": -das, "stage": "Not sown yet", "pct": 0, "duration": dur, "idx": -1, "bounds_days": [round(b * dur) for b in STAGE_BOUNDS]}
    nxt = round(STAGE_BOUNDS[stage_idx + 1] * dur) - das if stage_idx < 4 else 0
    sens = sorted(((STAGE_SENS[h][stage_idx], h) for h in HAZARDS), reverse=True)[:2]
    names = {"heat": "heat", "cold": "cold", "drought": "dry spells", "rain": "heavy rain", "flood": "waterlogging", "fungal": "humid, disease-favourable weather"}
    return {"sown": True, "das": das, "stage": STAGES[stage_idx], "idx": stage_idx, "pct": min(100, round(100 * das / dur)), "duration": dur,
            "days_to_next": max(nxt, 0) if stage_idx < 4 else None, "days_to_harvest": max(dur - das, 0), "bounds_days": [round(b * dur) for b in STAGE_BOUNDS],
            "sensitive_to": [names[h] for _, h in sens]}


def _first_day(f, mask):
    d = f[mask]
    return day_label(d.iloc[0].date) if len(d) else None


def recommendations(wx, crop, risks, irr, stage_idx, source_label):
    """Prioritised actions. Every item answers WHAT happened, WHY it matters, WHAT to do and WHEN."""
    f = forecast_days(wx)
    out = []
    when = {
        "heat": _first_day(f, f.tmax > crop["heat_c"]),
        "cold": _first_day(f, f.tmin < crop["cold_c"]),
        "rain": day_label(f.loc[f.rain_mm.idxmax()].date) if f.rain_mm.max() >= 1 else None,
        "flood": day_label(f.loc[f.rain_mm.idxmax()].date) if f.rain_mm.max() >= 1 else None,
        "drought": day_label(irr["when"]) if irr.get("when") is not None else None,
        "fungal": _first_day(f, (f.rh_mean >= 85) | (f.rain_mm >= 1)) if "rh_mean" in f else None}
    timing = {"Severe": "Today", "High": "Within 1-3 days", "Moderate": "Check again in 2-3 days"}
    for h in HAZARDS:
        r = risks[h]
        if r["score"] < 25:
            continue
        p, plabel, level = PRIORITY[r["category"]]
        w = timing[r["category"]] + (f" - the risk builds from {when[h]}" if when[h] and r["category"] != "Severe" else (f" (risk peaks {when[h]})" if when[h] else ""))
        if h == "drought" and irr.get("needed") and irr.get("when") is not None:
            w = ("Postpone and re-check after the rain" if irr.get("postpone") else f"Irrigate {day_label(irr['when'])}, early morning or evening")
        out.append({"priority": p, "label": plabel, "level": level, "key": h, "title": r["name"], "category": r["category"], "score": r["score"],
                    "what": f"{r['name']} is {r['category'].lower()} ({r['score']:.0f}/100): " + (r["factors"][0][0] if r["factors"] else "no contributing factors") + ".",
                    "why": r["what"], "do": (irr["decision"] if h == "drought" and irr.get("decision") else r["action"]), "when": w,
                    "basis": f"Weather source: {source_label} · heuristic exposure score, not a probability"})
    out.sort(key=lambda x: (x["priority"], -x["score"]))
    if not out:
        out.append({"priority": 4, "label": "Routine", "level": "ok", "key": "none", "title": "No significant weather hazard", "category": "Low", "score": 0,
                    "what": "No hazard reached the Moderate level for the next 7 days.", "why": "Crop stress from weather is unlikely this week.",
                    "do": "Continue normal field work and routine scouting.", "when": "Re-check in 2-3 days, or sooner if the forecast changes.", "basis": f"Weather source: {source_label}"})
    return out


def data_quality(meta, wx):
    """Source, freshness and gap information with an overall plain-language rating."""
    q, live = meta["quality"], meta["source"] == "open-meteo"
    obs, fc = int((wx.kind == "observed").sum()), int((wx.kind == "forecast").sum())
    pct = 100 * q["imputed_rows"] / max(q["rows"], 1)
    notes, score = [], 0
    if not live:
        notes.append("Sample (synthetic) weather is in use - for demonstration, not for real farm decisions."); score += 3
    if not meta.get("location_exact", False) and live:
        notes.append("Location is approximate (state reference point); weather may differ from your field."); score += 1
    if pct > 0:
        notes.append(f"{q['imputed_rows']} of {q['rows']} days ({pct:.0f}%) contain filled-in values."); score += 1 if pct < 15 else 2
    if not q["rh_available"]:
        notes.append("Humidity data missing - rain is used as a stand-in for the fungal-weather indicator."); score += 1
    if fc < 7:
        notes.append(f"Only {fc} forecast day(s) available."); score += 1
    try:
        ts = datetime.fromisoformat(meta["fetched_at"]); stamp = ts.strftime("%d %b %Y, %H:%M %Z").strip()
    except Exception:
        stamp = "unknown"
    rating = "Good" if score == 0 else "Fair" if score <= 2 else "Limited"
    if not notes:
        notes.append("Live data, exact location, no gaps, humidity available.")
    return {"rating": rating, "live": live, "source": "Open-Meteo (live)" if live else "SAMPLE (synthetic)", "fetched": stamp, "observed_days": obs,
            "forecast_days": fc, "imputed_pct": pct, "notes": notes, "location_exact": bool(meta.get("location_exact", False))}
