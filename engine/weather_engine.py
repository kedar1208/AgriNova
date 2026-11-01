"""Weather acquisition + cleaning (AgroCast input pipeline).
Order of preference: Open-Meteo (free, no key) -> bundled SYNTHETIC sample (clearly labelled).
Columns: date, tmax, tmin, rain_mm, rh_mean, et0_mm, kind(observed|forecast), imputed(bool)."""
from datetime import date, datetime, timedelta
from pathlib import Path
import math
import numpy as np
import pandas as pd

SAMPLE_CSV = Path(__file__).resolve().parent.parent / "data" / "sample_weather.csv"
# Approximate representative coordinates (fallback when geocoding is unavailable).
STATE_COORDS = {"Maharashtra": (18.52, 73.86), "Punjab": (30.90, 75.86), "Uttar Pradesh": (26.85, 80.95),
                "Karnataka": (12.97, 77.59), "Telangana": (17.39, 78.49), "Gujarat": (23.02, 72.57),
                "Madhya Pradesh": (23.26, 77.41), "Tamil Nadu": (13.08, 80.27), "West Bengal": (22.57, 88.36),
                "Rajasthan": (26.91, 75.79), "Haryana": (29.69, 76.99), "Bihar": (25.59, 85.14),
                "Andhra Pradesh": (16.31, 80.44), "Odisha": (20.30, 85.82), "Chhattisgarh": (21.25, 81.63)}
COLS = ["date", "tmax", "tmin", "rain_mm", "rh_mean", "et0_mm", "kind"]


def hargreaves_et0(tmax, tmin, lat_deg, doy):
    """FAO-56 Hargreaves ET0 (mm/day) with extraterrestrial radiation Ra from latitude + day of year."""
    phi = math.radians(lat_deg)
    dr = 1 + 0.033 * math.cos(2 * math.pi * doy / 365)
    delta = 0.409 * math.sin(2 * math.pi * doy / 365 - 1.39)
    ws = math.acos(max(-1, min(1, -math.tan(phi) * math.tan(delta))))
    ra = (24 * 60 / math.pi) * 0.0820 * dr * (ws * math.sin(phi) * math.sin(delta) + math.cos(phi) * math.cos(delta) * math.sin(ws))
    ra_mm = 0.408 * ra
    return max(0.0, 0.0023 * ((tmax + tmin) / 2 + 17.8) * math.sqrt(max(tmax - tmin, 0)) * ra_mm)


def clean_weather(df: pd.DataFrame, lat: float = 20.0):
    """Validate + impute. Returns (clean_df, quality_report). Raises ValueError if unusable.
    Strategy: linear interpolation for gaps <=2 days, then column median of available data,
    ET0 gaps filled with Hargreaves from tmax/tmin. Every imputed row is flagged."""
    need = ["date", "tmax", "tmin", "rain_mm", "kind"]
    if df is None or len(df) == 0 or any(c not in df.columns for c in need):
        raise ValueError("weather data empty or missing required columns")
    d = df.copy()
    for c in COLS[1:6]:
        if c not in d.columns:
            d[c] = np.nan
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d["date"] = pd.to_datetime(d["date"]).dt.date
    d = d.sort_values("date").reset_index(drop=True)
    if d[["tmax", "tmin"]].isna().all().any():
        raise ValueError("no usable temperature data")
    # physically implausible values -> NaN
    d.loc[(d.tmax < -10) | (d.tmax > 55), "tmax"] = np.nan
    d.loc[(d.tmin < -15) | (d.tmin > 45), "tmin"] = np.nan
    d.loc[d.rain_mm < 0, "rain_mm"] = np.nan
    d.loc[(d.rh_mean < 0) | (d.rh_mean > 100), "rh_mean"] = np.nan
    miss_before = d[COLS[1:6]].isna().sum().to_dict()
    flag = d[COLS[1:6]].isna().any(axis=1)
    for c in ["tmax", "tmin", "rain_mm", "rh_mean"]:
        d[c] = d[c].interpolate(limit=2, limit_direction="both")
        if d[c].isna().any() and d[c].notna().any():
            d[c] = d[c].fillna(d[c].median())
    swap = d.tmin > d.tmax
    d.loc[swap, ["tmin", "tmax"]] = d.loc[swap, ["tmax", "tmin"]].values
    for i in d.index[d.et0_mm.isna() & d.tmax.notna() & d.tmin.notna()]:
        d.at[i, "et0_mm"] = hargreaves_et0(d.at[i, "tmax"], d.at[i, "tmin"], lat, d.at[i, "date"].timetuple().tm_yday)
    d["imputed"] = flag.values
    d["rain_mm"] = d["rain_mm"].fillna(0.0)  # no rain data at all -> assume 0 (flagged via imputed)
    return d, {"missing_before": miss_before, "rows": len(d), "imputed_rows": int(flag.sum()),
               "rh_available": bool(d.rh_mean.notna().any())}


def sample_weather(today: date = None) -> pd.DataFrame:
    """SYNTHETIC demonstration weather, re-dated so the last 14 days are 'observed' and next 7 'forecast'."""
    today = today or date.today()
    s = pd.read_csv(SAMPLE_CSV)
    s["date"] = [today + timedelta(days=int(o)) for o in s.day_offset]
    s["kind"] = np.where(s.day_offset < 0, "observed", "forecast")
    return s[COLS]


def _norm(x):
    return str(x or "").strip().lower()


def geocode(district: str, state: str, timeout=6):
    """Find (lat, lon) of a district inside `state`. Returns None when nothing inside that state matches,
    so the caller can say the location is approximate instead of silently using the wrong place."""
    import requests
    from .locations import SEARCH_ALIASES
    for name in [district] + SEARCH_ALIASES.get(district, []):
        r = requests.get("https://geocoding-api.open-meteo.com/v1/search",
                         params={"name": name, "count": 20, "country_code": "IN"}, timeout=timeout)
        r.raise_for_status()
        hits = [h for h in r.json().get("results", []) if _norm(h.get("admin1")) == _norm(state)]
        if not hits:
            continue
        # best match first: same name, then same district (admin2), then the first hit in the state
        hits.sort(key=lambda h: (_norm(h.get("name")) != _norm(name), _norm(h.get("admin2")) != _norm(name)))
        return hits[0]["latitude"], hits[0]["longitude"]
    return None


def fetch_open_meteo(lat, lon, past_days=14, forecast_days=7, timeout=8) -> pd.DataFrame:
    import requests
    p = {"latitude": lat, "longitude": lon, "timezone": "auto", "past_days": past_days, "forecast_days": forecast_days,
         "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,et0_fao_evapotranspiration,relative_humidity_2m_mean"}
    r = requests.get("https://api.open-meteo.com/v1/forecast", params=p, timeout=timeout)
    r.raise_for_status()
    j = r.json()["daily"]
    df = pd.DataFrame({"date": j["time"], "tmax": j["temperature_2m_max"], "tmin": j["temperature_2m_min"],
                       "rain_mm": j["precipitation_sum"], "et0_mm": j.get("et0_fao_evapotranspiration"),
                       "rh_mean": j.get("relative_humidity_2m_mean")})
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df["kind"] = np.where(df["date"] < date.today(), "observed", "forecast")
    return df


def locate(state: str, district: str = "", lookup=True):
    """Resolve the farm location. Returns dict(lat, lon, label, exact, note)."""
    lat, lon = STATE_COORDS.get(state, (20.0, 78.0))
    label = f"{district}, {state}" if district else state
    loc = {"lat": lat, "lon": lon, "label": label, "exact": False, "note": None}
    if not lookup or not district:
        return loc
    g = geocode(district, state)          # network errors propagate: the caller decides how to fall back
    if g:
        loc.update(lat=g[0], lon=g[1], exact=True)
    else:
        loc["note"] = f"Could not pin down {district}; weather is for the {state} reference point."
    return loc


def get_live_weather(state: str, district: str = ""):
    """Open-Meteo weather for the district. RAISES on any network/API problem (so callers never cache a fallback)."""
    loc = locate(state, district)
    clean, q = clean_weather(fetch_open_meteo(loc["lat"], loc["lon"]), loc["lat"])
    return clean, {"source": "open-meteo", "lat": loc["lat"], "lon": loc["lon"], "error": loc["note"], "quality": q,
                   "location": loc["label"], "location_exact": loc["exact"], "fetched_at": datetime.now().astimezone().isoformat(timespec="seconds")}


def get_sample_weather(state: str, district: str = "", reason: str = None, today: date = None):
    loc = locate(state, district, lookup=False)
    clean, q = clean_weather(sample_weather(today or date.today()), loc["lat"])
    return clean, {"source": "SAMPLE (synthetic)", "lat": loc["lat"], "lon": loc["lon"], "error": reason, "quality": q,
                   "location": loc["label"], "location_exact": False, "fetched_at": datetime.now().astimezone().isoformat(timespec="seconds")}


def get_weather(state: str, district: str = "", offline: bool = False, today: date = None):
    """Main entry. Returns (clean_df, meta). meta['source'] is 'open-meteo' or 'SAMPLE (synthetic)'."""
    if not offline:
        try:
            return get_live_weather(state, district)
        except Exception as e:  # network/API/parsing failure -> labelled fallback
            return get_sample_weather(state, district, f"Live weather unavailable ({type(e).__name__}); showing sample data instead.", today)
    return get_sample_weather(state, district, None, today)
