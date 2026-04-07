import os
import pandas as pd
from fredapi import Fred


def get_fred_client():
    api_key = os.getenv("FRED_API_KEY")
    if not api_key:
        return None
    return Fred(api_key=api_key)


def get_fred_series(series_id, start_date=None, end_date=None):
    fred = get_fred_client()
    if fred is None:
        return pd.DataFrame()

    try:
        series = fred.get_series(
            series_id,
            observation_start=start_date,
            observation_end=end_date,
        )
        df = series.reset_index()
        df.columns = ["date", series_id]
        df["date"] = pd.to_datetime(df["date"])
        return df
    except Exception:
        return pd.DataFrame()


def get_macro_bundle(start_date=None, end_date=None):
    series_map = {
        "DGS10": "10Y Treasury Yield",
        "DGS2": "2Y Treasury Yield",
        "FEDFUNDS": "Fed Funds Rate",
        "CPIAUCSL": "CPI",
        "UNRATE": "Unemployment Rate",
    }

    frames = []

    for series_id, label in series_map.items():
        df = get_fred_series(series_id, start_date=start_date, end_date=end_date)
        if not df.empty:
            df = df.rename(columns={series_id: label})
            frames.append(df)

    if not frames:
        return pd.DataFrame()

    out = frames[0]
    for df in frames[1:]:
        out = out.merge(df, on="date", how="outer")

    out = out.sort_values("date").reset_index(drop=True)

    if "10Y Treasury Yield" in out.columns and "2Y Treasury Yield" in out.columns:
        out["10Y-2Y Spread"] = out["10Y Treasury Yield"] - out["2Y Treasury Yield"]

    return out
