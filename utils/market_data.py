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


def run_monte_carlo_portfolio_simulation(
    asset_returns,
    weights_series,
    initial_value=100000,
    n_days=252,
    n_sims=3000,
    seed=42,
):
    if asset_returns.empty or weights_series.empty:
        return pd.DataFrame(), {}

    common_cols = [col for col in asset_returns.columns if col in weights_series.index]
    if not common_cols:
        return pd.DataFrame(), {}

    returns = asset_returns[common_cols].copy()
    weights = weights_series.loc[common_cols].copy()

    if weights.sum() == 0:
        return pd.DataFrame(), {}

    weights = weights / weights.sum()

    mean_returns = returns.mean().values
    cov_matrix = returns.cov().values

    rng = np.random.default_rng(seed)

    try:
        simulated_daily_returns = rng.multivariate_normal(
            mean=mean_returns,
            cov=cov_matrix,
            size=(n_sims, n_days),
        )
    except Exception:
        return pd.DataFrame(), {}

    portfolio_daily_returns = np.einsum("sda,a->sd", simulated_daily_returns, weights.values)

    portfolio_paths = np.cumprod(1 + portfolio_daily_returns, axis=1) * initial_value
    paths_df = pd.DataFrame(portfolio_paths.T)

    ending_values = portfolio_paths[:, -1]
    total_returns = ending_values / initial_value - 1

    stats = {
        "initial_value": initial_value,
        "median_ending_value": float(np.median(ending_values)),
        "mean_ending_value": float(np.mean(ending_values)),
        "p5_ending_value": float(np.percentile(ending_values, 5)),
        "p95_ending_value": float(np.percentile(ending_values, 95)),
        "probability_of_loss": float(np.mean(ending_values < initial_value)),
        "median_total_return": float(np.median(total_returns)),
        "mean_total_return": float(np.mean(total_returns)),
    }

    return paths_df, stats


def prepare_portfolio_weights_from_holdings(portfolio_df, valid_symbols):
    if portfolio_df is None or portfolio_df.empty:
        return pd.Series(dtype=float)

    weights = (
        portfolio_df[portfolio_df["Symbol"].isin(valid_symbols)]
        .groupby("Symbol")["PositionValue"]
        .sum()
    )

    if weights.empty or weights.sum() == 0:
        return pd.Series(dtype=float)

    weights = weights / weights.sum()
    return weights
