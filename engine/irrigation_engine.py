"""AgroCast - root-zone water balance + irrigation advisor (FAO-56 style bucket model).
AW(t+1) = clip(AW(t) + 0.8*rain - ET0*Kc, 0, TAW);  stress when AW < (1-p)*TAW.
Soil moisture is MEASURED only if the farmer supplies it; otherwise it is ESTIMATED by spinning
the bucket up from an assumed 60% of capacity at the start of the weather window."""
from datetime import date
import numpy as np
import pandas as pd
from .crop_database import SOILS, ROOT_FACTOR, IRRIGATION_EFF, kc_for_stage

EFF_RAIN = 0.8        # fraction of rainfall assumed to enter the root zone (assumption)
MM_TO_M3_PER_ACRE = 4.0469   # 1 mm over 1 acre = 4.0469 m3
MAX_NET_DEPTH_MM = 60.0
SPINUP_FRAC = 0.6


def day_label(d, today=None) -> str:
    """'today', 'tomorrow' or 'Wed 4 Nov' - friendlier than an ISO date in advice text."""
    today = today or date.today()
    n = (d - today).days
    return "today" if n == 0 else "tomorrow" if n == 1 else f"{d:%a} {d.day} {d:%b}"


def taw_mm(crop, stage_idx, soil) -> float:
    awc, _ = SOILS[soil]
    return awc * crop["root_m"] * ROOT_FACTOR[max(stage_idx, 0)]


def project_moisture(wx, crop, stage_idx, soil, measured_pct=None):
    """Daily available-water projection. Returns (df, info). df has aw_mm, frac, etc_mm, stressed."""
    if len(wx) == 0:
        raise ValueError("no weather rows")
    taw = taw_mm(crop, stage_idx, soil)
    kc = kc_for_stage(crop, stage_idx)
    rows = wx[wx.kind == "forecast"] if measured_pct is not None else wx
    if measured_pct is not None and len(rows) == 0:
        rows = wx
    aw = taw * (measured_pct / 100.0 if measured_pct is not None else SPINUP_FRAC)
    out = []
    for _, r in rows.iterrows():
        etc = float(r.et0_mm) * kc
        aw = float(np.clip(aw + EFF_RAIN * float(r.rain_mm) - etc, 0, taw))
        out.append((r["date"], r["kind"], float(r.rain_mm), etc, aw, aw / taw if taw else 0.0))
    df = pd.DataFrame(out, columns=["date", "kind", "rain_mm", "etc_mm", "aw_mm", "frac"])
    df["stressed"] = df.frac < (1 - crop["p_depl"])
    return df, {"taw_mm": taw, "kc": kc, "estimated": measured_pct is None, "threshold_frac": 1 - crop["p_depl"]}


def advise(wx, crop, stage_idx, soil, area_acres, method, measured_pct=None):
    """Irrigation advice dict: decision, when, net/gross depth, volume, postpone flag, reasons, estimated flag."""
    if area_acres <= 0:
        raise ValueError("area must be positive")
    if method not in IRRIGATION_EFF:
        raise ValueError(f"unknown irrigation method {method}")
    res = {"needed": False, "postpone": False, "when": None, "net_mm": 0.0, "gross_mm": 0.0, "volume_m3": 0.0,
           "reasons": [], "estimated": measured_pct is None, "decision": ""}
    if stage_idx == -1:
        res["decision"] = "Crop not sown yet - no crop irrigation needed. Plan land preparation/pre-sowing moisture."
        return res
    proj, info = project_moisture(wx, crop, stage_idx, soil, measured_pct)
    res.update(taw_mm=info["taw_mm"], threshold_frac=info["threshold_frac"], projection=proj)
    fc = proj[proj.kind == "forecast"] if (proj.kind == "forecast").any() else proj
    eff = IRRIGATION_EFF[method]
    tag = "ESTIMATED" if res["estimated"] else "MEASURED"
    res["reasons"].append(f"Root-zone water is {tag}: capacity {info['taw_mm']:.0f} mm; stress below {info['threshold_frac']*100:.0f}% full.")
    now_frac = float(fc.iloc[0].frac)
    hit = fc[fc.stressed]
    rain48 = float(fc.head(2).rain_mm.sum())
    if hit.empty:
        res["decision"] = "No irrigation needed in the next 7 days (projected soil water stays above stress level)."
        res["reasons"].append(f"Lowest projected water level: {fc.frac.min()*100:.0f}% of capacity.")
        return res
    first = hit.iloc[0]
    res["needed"] = True
    net = min(float(info["taw_mm"] - first.aw_mm), MAX_NET_DEPTH_MM)
    res.update(net_mm=net, when=first["date"])
    if eff > 0:
        res["gross_mm"] = net / eff
        res["volume_m3"] = res["gross_mm"] * MM_TO_M3_PER_ACRE * area_acres
    if now_frac < info["threshold_frac"] and EFF_RAIN * rain48 >= 0.7 * net:
        res["postpone"] = True
        res["decision"] = f"Soil is dry but ~{rain48:.0f} mm rain is forecast within 48 hours - postpone irrigation and re-check after the rain."
        res["reasons"].append("Forecast rain is large enough to refill most of the deficit.")
        return res
    if eff == 0:
        res["decision"] = (f"Water stress expected from {day_label(first['date'])} but no irrigation source is available. "
                           "Consider mulching, weed control and moisture-conserving practices; seek protective irrigation if possible.")
        return res
    res["decision"] = (f"Irrigate {day_label(first['date'])} (early morning or evening): apply about {res['gross_mm']:.0f} mm "
                       f"(~{res['volume_m3']:,.0f} m³ for {area_acres:g} acres, {method.lower()}).")
    res["reasons"].append(f"Projected water falls below the stress level {day_label(first['date'])}; 7-day forecast rain: {fc.rain_mm.sum():.0f} mm.")
    return res
