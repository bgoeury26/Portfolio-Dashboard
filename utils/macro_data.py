import os
import pandas as pd

try:
    from fredapi import Fred
    _FRED_OK = True
except ImportError:
    _FRED_OK = False

def get_fred_client():
    if not _FRED_OK:
        return None
    key = os.environ.get("FRED_API_KEY", "")
    return Fred(api_key=key) if key else None

def get_macro_bundle(start_date: str = "2018-01-01") -> dict:
    client = get_fred_client()
    if client is None:
        return {}
    series = {
        "GDP Growth": "A191RL1Q225SBEA",
        "CPI Inflation": "CPIAUCSL",
        "Unemployment": "UNRATE",
        "Fed Funds Rate": "FEDFUNDS",
        "10Y Treasury": "DGS10",
        "2Y Treasury": "DGS2",
        "VIX": "VIXCLS",
        "Credit Spread HY": "BAMLH0A0HYM2",
    }
    bundle = {}
    for name, sid in series.items():
        try:
            bundle[name] = client.get_series(sid, observation_start=start_date)
        except Exception:
            bundle[name] = pd.Series(dtype=float)
    return bundle
