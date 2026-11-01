"""Modular crop database + shared agronomy constants (used by BOTH solutions).
Crop parameters live in data/crops.csv; add a row (or call add_crop) to add a crop.
All numbers in crops.csv are ILLUSTRATIVE planning defaults (FAO-56 Kc, FAO-33 Ky style values,
approximate recent MSP/FRP price levels) - verify against your state agriculture department."""
from pathlib import Path
from datetime import date
import pandas as pd

CSV_PATH = Path(__file__).resolve().parent.parent / "data" / "crops.csv"
REQUIRED = ["crop", "season", "duration_days", "kc_ini", "kc_mid", "kc_end", "ky", "etm_mm", "root_m",
            "p_depl", "yield_q_acre", "price_per_q", "cost_per_acre", "waterlog_sens", "heat_c",
            "cold_c", "heavy_rain_mm", "fungal_tmin", "fungal_tmax"]

STAGES = ["Germination/Establishment", "Vegetative", "Flowering/Reproductive", "Grain/Fruit filling", "Maturity/Harvest"]
STAGE_BOUNDS = [0.0, 0.15, 0.45, 0.65, 0.85, 1.0]          # fraction of crop duration (generic split)
ROOT_FACTOR = [0.3, 0.6, 1.0, 1.0, 1.0]                      # fraction of max root depth per stage
# Stage sensitivity multipliers (0-1) per hazard - expert-judgement heuristics, not fitted values.
STAGE_SENS = {"heat": [0.5, 0.6, 1.0, 0.9, 0.4], "cold": [0.7, 0.5, 1.0, 0.7, 0.3],
              "drought": [0.9, 0.7, 1.0, 0.8, 0.4], "rain": [0.7, 0.5, 0.8, 0.7, 0.9],
              "flood": [0.9, 0.7, 0.8, 0.6, 0.6], "fungal": [0.5, 0.8, 0.9, 0.8, 0.6]}
# soil: (available water capacity mm per metre of soil, drainage-problem factor 0=free draining, 1=poor)
SOILS = {"Sandy": (80, 0.2), "Sandy loam": (110, 0.3), "Red soil": (100, 0.35), "Loam": (160, 0.5),
         "Clay loam": (170, 0.8), "Clay": (150, 1.0), "Black cotton soil": (170, 0.9)}
IRRIGATION_EFF = {"Drip": 0.90, "Sprinkler": 0.75, "Furrow/Flood": 0.60, "Rainfed (none)": 0.0}


def load_crops(path=None) -> pd.DataFrame:
    df = pd.read_csv(path or CSV_PATH)
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise ValueError(f"crops file missing columns: {missing}")
    return df


def get_crop(name: str, df: pd.DataFrame = None) -> dict:
    df = load_crops() if df is None else df
    hit = df[df["crop"].str.lower() == str(name).lower()]
    if hit.empty:
        raise KeyError(f"Unknown crop '{name}'. Available: {', '.join(df['crop'])}")
    return hit.iloc[0].to_dict()


def add_crop(row: dict, path=None):
    """Append a new crop (all REQUIRED keys needed)."""
    miss = [c for c in REQUIRED if c not in row]
    if miss:
        raise ValueError(f"missing keys: {miss}")
    df = load_crops(path)
    if row["crop"].lower() in df["crop"].str.lower().values:
        raise ValueError("crop already exists")
    pd.concat([df, pd.DataFrame([row])]).to_csv(path or CSV_PATH, index=False)


def stage_for(sowing: date, duration_days: int, today: date):
    """Return (stage_index, label, days_after_sowing). -1 = not sown yet."""
    das = (today - sowing).days
    if das < 0:
        return -1, "Not sown yet", das
    frac = das / float(duration_days)
    if frac >= 1.0:
        return 4, "Maturity/Harvest (past expected duration)", das
    for i in range(5):
        if STAGE_BOUNDS[i] <= frac < STAGE_BOUNDS[i + 1]:
            return i, STAGES[i], das


def kc_for_stage(crop: dict, idx: int) -> float:
    i, m, e = crop["kc_ini"], crop["kc_mid"], crop["kc_end"]
    return [i, (i + m) / 2, m, m, e][max(idx, 0)]
