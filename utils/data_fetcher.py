import pandas as pd
import streamlit as st
import yfinance as yf
from openbb import obb


def _normalize_openbb_historical(result):
    try:
        if hasattr(result, "to_dataframe"):
            df = result.to_dataframe()
        elif isinstance(result, pd.DataFrame):
            df = result
        else:
            return pd.DataFrame()
    except Exception:
        return pd.DataFrame()

    if df is None or df.empty:
        return pd.DataFrame()

    df = df.copy()
    df.columns = [str(c).lower() for c in df.columns]

    if "close" not in df.columns:
        return pd.DataFrame()

    series = pd.to_numeric(df["close"], errors="coerce").dropna()
    if series.empty:
        return pd.DataFrame()

    series.index = pd.to_datetime(series.index, errors="coerce")
    series = series[~series.index.isna()]
    return series.sort_index().to_frame(name="Close")


@st.cache_data(ttl=3600)
def get_price_history(symbol: str, period: str = "1y") -> pd.DataFrame:
    symbol = str(symbol).strip().upper()

    openbb_candidates = [
        symbol,
        f"{symbol}.US",
        f"{symbol}.L",
    ]

    for candidate in openbb_candidates:
        try:
            result = obb.equity.price.historical(candidate, provider="yfinance", interval="1d")
            df = _normalize_openbb_historical(result)
            if not df.empty and len(df) >= 30:
                return df
        except Exception:
            pass

    try:
        hist = yf.Ticker(symbol).history(period=period, interval="1d", auto_adjust=False)
        if hist is not None and not hist.empty and "Close" in hist.columns:
            hist = hist[["Close"]].dropna()
            if len(hist) >= 30:
                hist.index = pd.to_datetime(hist.index, errors="coerce")
                hist = hist[~hist.index.isna()]
                return hist.sort_index()
    except Exception:
        pass

    return pd.DataFrame()


@st.cache_data(ttl=3600)
def get_price_matrix(symbols, period: str = "1y"):
    valid_data = {}
    invalid_tickers = []

    for symbol in symbols:
        hist = get_price_history(symbol, period=period)
        if hist.empty:
            invalid_tickers.append(symbol)
        else:
            valid_data[symbol] = hist["Close"].rename(symbol)

    if not valid_data:
        return pd.DataFrame(), [], invalid_tickers

    prices = pd.concat(valid_data.values(), axis=1, sort=False).dropna(how="all")
    prices = prices.dropna(axis=1, how="all")

    valid_tickers = list(prices.columns)
    invalid_tickers = [s for s in symbols if s not in valid_tickers]

    return prices, valid_tickers, invalid_tickers


@st.cache_data(ttl=3600)
def get_returns_from_prices(prices: pd.DataFrame) -> pd.DataFrame:
    if prices is None or prices.empty:
        return pd.DataFrame()
    returns = prices.pct_change().dropna(how="all")
    return returns
