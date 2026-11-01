from datetime import date
from engine.crop_database import SOILS, IRRIGATION_EFF, load_crops
from engine.locations import DISTRICTS, is_valid

ACRES_PER_HA = 2.47105
CAT_COLOR = {"Low": "#5b8a5a", "Moderate": "#c79a2b", "High": "#cc7a2e", "Severe": "#a63d2f"}


def to_acres(value, unit):
    return float(value) * (ACRES_PER_HA if unit.lower().startswith("h") else 1.0)


def inr(x):
    """Indian digit grouping: 1234567 -> Rs 12,34,567"""
    s = f"{abs(round(x)):d}"
    head, tail = s[:-3], s[-3:]
    if head:
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:]); head = head[:-2]
        if head: parts.insert(0, head)
        s = ",".join(parts) + "," + tail
    return ("-" if x < 0 else "") + "Rs " + s


def validate_farm(cfg, crops_df=None):
    """Return list of error strings (empty = valid)."""
    errs = []
    crops_df = load_crops() if crops_df is None else crops_df
    if cfg.get("state") in DISTRICTS and not is_valid(cfg["state"], cfg.get("district")): errs.append("Choose a district from the list for the selected state.")
    if cfg.get("crop") not in set(crops_df["crop"]): errs.append("Unknown crop.")
    if not isinstance(cfg.get("area_acres"), (int, float)) or cfg["area_acres"] <= 0: errs.append("Farm area must be greater than 0.")
    elif cfg["area_acres"] > 5000: errs.append("Farm area looks unrealistic for a small farm (>5000 acres).")
    if cfg.get("soil") not in SOILS: errs.append("Choose a valid soil type.")
    if cfg.get("irrigation") not in IRRIGATION_EFF: errs.append("Choose a valid irrigation method.")
    if cfg.get("budget", 0) < 0: errs.append("Budget cannot be negative.")
    if cfg.get("water_m3", 0) < 0: errs.append("Available water cannot be negative.")
    sd = cfg.get("sowing_date")
    if not isinstance(sd, date): errs.append("Enter a valid sowing date.")
    elif abs((sd - date.today()).days) > 400: errs.append("Sowing date is more than a year away from today.")
    mp = cfg.get("measured_pct")
    if mp is not None and not (0 <= mp <= 100): errs.append("Measured soil moisture must be between 0 and 100%.")
    return errs
