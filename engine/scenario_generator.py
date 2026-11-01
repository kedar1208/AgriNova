"""FarmOptimizer - SIMULATED seasonal rainfall scenarios (NOT forecasts).
Seasonal rainfall multiplier m = actual / normal.  m ~ Normal(mu_k, sd_k) clipped to [0.2, 2.5], where scenario k
is drawn from a categorical mix.  Defaults are illustrative planning values: editable in the UI or replaceable by
imported scenarios (e.g. from district rainfall history)."""
import numpy as np
import pandas as pd

DEFAULT_PARAMS = {"Normal": (1.00, 0.12), "Drought": (0.70, 0.12), "Excess": (1.35, 0.15)}
DEFAULT_PROBS = {"Normal": 0.60, "Drought": 0.20, "Excess": 0.20}


def generate_scenarios(n=1000, probs=None, severity=1.0, rain_change=0.0, seed=42, params=None) -> pd.DataFrame:
    """severity scales deviation of Drought/Excess means from 1.0; rain_change is a global shift (-0.3 = 30% less rain)."""
    if not isinstance(n, (int, np.integer)) or n < 1:
        raise ValueError("n must be a positive integer")
    probs = dict(DEFAULT_PROBS if probs is None else probs)
    params = dict(DEFAULT_PARAMS if params is None else params)
    if severity < 0 or rain_change <= -1:
        raise ValueError("severity must be >=0 and rain_change > -1")
    names = list(params)
    p = np.array([probs.get(k, 0.0) for k in names], float)
    if (p < 0).any() or p.sum() <= 0:
        raise ValueError("scenario probabilities must be non-negative with positive sum")
    p = p / p.sum()
    rng = np.random.default_rng(seed)
    idx = rng.choice(len(names), size=n, p=p)
    mu = np.array([1 + (params[k][0] - 1) * severity for k in names])
    sd = np.array([params[k][1] for k in names])
    m = np.clip(rng.normal(mu[idx], sd[idx]), 0.2, 2.5) * (1 + rain_change)
    df = pd.DataFrame({"scenario": np.array(names)[idx], "rain_mult": m})
    df.attrs["data_type"] = "SIMULATED (not a weather forecast)"
    return df


def import_scenarios(df: pd.DataFrame) -> pd.DataFrame:
    """Use your own scenarios: needs 'rain_mult' (>0); optional 'scenario' label."""
    if "rain_mult" not in df or len(df) == 0 or (pd.to_numeric(df["rain_mult"], errors="coerce") <= 0).any() or df["rain_mult"].isna().any():
        raise ValueError("imported scenarios need a positive 'rain_mult' column")
    out = df.copy()
    if "scenario" not in out:
        out["scenario"] = np.where(out.rain_mult < 0.9, "Drought", np.where(out.rain_mult > 1.2, "Excess", "Normal"))
    out.attrs["data_type"] = "IMPORTED scenarios"
    return out[["scenario", "rain_mult"]]
