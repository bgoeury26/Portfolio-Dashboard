from openbb import obb
import pandas as pd
import numpy as np


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


def extract_close_series(price_df, symbol):
    if price_df.empty:
        return pd.Series(dtype=float)

    close_col_candidates = ["close", "Close", "adj_close", "Adj Close"]

    for col in close_col_candidates:
        if col in price_df.columns:
            series = price_df[col].copy()
            series.name = symbol
            return series.dropna()

    return pd.Series(dtype=float)


def get_multi_asset_close_prices(symbols, start_date=None, end_date=None):
    series_list = []
    valid_symbols = []
    failed_symbols = []

    for symbol in symbols:
        df, provider = get_available_history(symbol, start_date=start_date, end_date=end_date)
        close_series = extract_close_series(df, symbol)

        if close_series.empty or len(close_series) < 30:
            failed_symbols.append(symbol)
            continue

        series_list.append(close_series)
        valid_symbols.append(symbol)

    if not series_list:
        return pd.DataFrame(), valid_symbols, failed_symbols

    prices = pd.concat(series_list, axis=1).dropna(how="any")
    return prices, valid_symbols, failed_symbols


def compute_returns_from_prices(price_df):
    if price_df.empty:
        return pd.DataFrame()

    returns = price_df.pct_change().replace([np.inf, -np.inf], np.nan).dropna(how="any")
    return returns


def compute_weighted_portfolio_returns(asset_returns, weights_series):
    if asset_returns.empty or weights_series.empty:
        return pd.Series(dtype=float)

    common_cols = [col for col in asset_returns.columns if col in weights_series.index]
    if not common_cols:
        return pd.Series(dtype=float)

    aligned_returns = asset_returns[common_cols].copy()
    aligned_weights = weights_series.loc[common_cols].copy()

    if aligned_weights.sum() == 0:
        return pd.Series(dtype=float)

    aligned_weights = aligned_weights / aligned_weights.sum()

    portfolio_returns = aligned_returns.mul(aligned_weights, axis=1).sum(axis=1)
    portfolio_returns.name = "portfolio_return"
    return portfolio_returns


def compute_beta(portfolio_returns, benchmark_returns):
    combined = pd.concat([portfolio_returns, benchmark_returns], axis=1).dropna()
    if combined.empty or combined.shape[0] < 30:
        return np.nan

    combined.columns = ["portfolio", "benchmark"]

    benchmark_var = combined["benchmark"].var()
    if benchmark_var == 0 or pd.isna(benchmark_var):
        return np.nan

    covariance = combined["portfolio"].cov(combined["benchmark"])
    beta = covariance / benchmark_var
    return beta


def compute_annualized_return(return_series):
    if return_series.empty:
        return np.nan
    return return_series.mean() * 252


def compute_treynor_ratio(portfolio_returns, benchmark_returns, risk_free_rate=0.02):
    beta = compute_beta(portfolio_returns, benchmark_returns)
    annual_return = compute_annualized_return(portfolio_returns)

    if pd.isna(beta) or beta == 0 or pd.isna(annual_return):
        return np.nan, beta, annual_return

    treynor = (annual_return - risk_free_rate) / beta
    return treynor, beta, annual_return
