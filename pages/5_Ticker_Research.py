import pandas as pd
import streamlit as st

from utils.market_data import (
    compute_beta,
    compute_returns_from_prices,
    compute_treynor_ratio,
    compute_weighted_portfolio_returns,
    extract_close_series,
    get_available_history,
    get_company_profile,
    get_multi_asset_close_prices,
)
from utils.session_state import get_portfolio, initialize_session_state

initialize_session_state()

st.header("Ticker Research")

portfolio_df = get_portfolio()

symbol = st.text_input("Enter a ticker to research", value="MSFT").strip().upper()
benchmark_symbol = st.text_input("Benchmark ticker", value="SPY").strip().upper()
risk_free_rate = st.number_input("Risk-free rate", min_value=0.0, max_value=0.15, value=0.04, step=0.005)

if symbol:
    price_df, provider_used = get_available_history(symbol, start_date="2024-01-01")

    if provider_used:
        st.success(f"Loaded market data for {symbol} using provider: {provider_used}")
        st.dataframe(price_df.tail(), use_container_width=True)
    else:
        st.warning("No market data found for this ticker.")

    profile_df = get_company_profile(symbol)

    if not profile_df.empty:
        st.subheader("Company Profile")
        st.dataframe(profile_df, use_container_width=True)

if portfolio_df is not None:
    st.subheader("Portfolio Benchmark Analytics")

    portfolio_symbols = portfolio_df["Symbol"].dropna().astype(str).unique().tolist()
    prices_df, valid_symbols, failed_symbols = get_multi_asset_close_prices(
        portfolio_symbols,
        start_date="2024-01-01",
    )

    if failed_symbols:
        st.warning("Excluded symbols from benchmark analytics: " + ", ".join(failed_symbols))

    if not prices_df.empty and valid_symbols:
        asset_returns = compute_returns_from_prices(prices_df)

        weights_series = (
            portfolio_df[portfolio_df["Symbol"].isin(valid_symbols)]
            .groupby("Symbol")["PositionValue"]
            .sum()
        )
        weights_series = weights_series / weights_series.sum()

        portfolio_returns = compute_weighted_portfolio_returns(asset_returns, weights_series)

        benchmark_price_df, benchmark_provider = get_available_history(
            benchmark_symbol,
            start_date="2024-01-01",
        )
        benchmark_close = extract_close_series(benchmark_price_df, benchmark_symbol)
        benchmark_returns = benchmark_close.pct_change().dropna()
        benchmark_returns.name = benchmark_symbol

        beta = compute_beta(portfolio_returns, benchmark_returns)
        treynor, annual_return, annualized_return = None, None, None

        treynor, beta, annualized_return = compute_treynor_ratio(
            portfolio_returns,
            benchmark_returns,
            risk_free_rate=risk_free_rate,
        )

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Benchmark", benchmark_symbol)

        with col2:
            st.metric("Portfolio Beta", f"{beta:.3f}" if pd.notna(beta) else "N/A")

        with col3:
            st.metric("Treynor Ratio", f"{treynor:.3f}" if pd.notna(treynor) else "N/A")

        st.caption(
            "Treynor Ratio = (annualized portfolio return - risk-free rate) / portfolio beta"
        )
    else:
        st.info("Not enough valid portfolio market data yet for benchmark analytics.")
else:
    st.info("Upload a portfolio first if you want benchmark and portfolio analytics.")
