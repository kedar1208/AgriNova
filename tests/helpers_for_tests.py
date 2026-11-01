from datetime import date, timedelta
import numpy as np, pandas as pd


def make_wx(tmax=30, tmin=20, rain=0.0, rh=60, et0=4.0, past=14, fut=7):
    """Uniform synthetic weather frame for unit tests (arrays or scalars for the forecast part)."""
    today = date.today()
    rows = []
    for o in range(-past, fut):
        g = lambda v: v[o] if isinstance(v, dict) and o in v else (v.get("default", 0) if isinstance(v, dict) else v)
        rows.append(dict(date=today + timedelta(days=o), tmax=g(tmax), tmin=g(tmin), rain_mm=g(rain), rh_mean=g(rh), et0_mm=g(et0),
                         kind="observed" if o < 0 else "forecast", imputed=False))
    return pd.DataFrame(rows)
