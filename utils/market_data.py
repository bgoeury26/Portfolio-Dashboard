from openbb import obb
import pandas as pd


def get_equity_price_history(symbol, provider="yfinance", interval="1d", start_date=None, end_date=None):
    try:
        data = obb.equity.price.historical(
            symbol,
            provider=provider,
            interval=interval,
            start_date=start_date,
            end_date=end_date,
        )
        df = data.to_df()
        return df
    except Exception:
        return pd.DataFrame()


def get_company_profile(symbol, provider="fmp"):
    try:
        data = obb.equity.profile(symbol, provider=provider)
        return data.to_df()
    except Exception:
        return pd.DataFrame()


def get_available_history(symbol, start_date=None, end_date=None):
    providers = ["yfinance"]

    for provider in providers:
        df = get_equity_price_history(
            symbol=symbol,
            provider=provider,
            start_date=start_date,
            end_date=end_date,
        )
        if not df.empty:
            return df, provider

    return pd.DataFrame(), None
