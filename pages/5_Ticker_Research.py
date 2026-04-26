import utils.openbb_patch  # noqa: F401
import pandas as pd
import plotly.express as px
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

    st.subheader("Hypothetical Position Impact")

    candidate_weight_pct = st.slider(
        "Hypothetical weight for selected ticker (%)",
        min_value=1,
        max_value=15,
        value=3,
        step=1,
    )

    if symbol:
        hypothetical_df = portfolio_df.copy()

        current_total_value = hypothetical_df["PositionValue"].sum()
        hypothetical_value = current_total_value * (candidate_weight_pct / 100)

        candidate_sector = "Unknown"
        candidate_currency = "Unknown"
        candidate_description = symbol

        if not profile_df.empty:
            profile_cols = {c.lower(): c for c in profile_df.columns}

            if "sector" in profile_cols:
                candidate_sector = str(profile_df[profile_cols["sector"]].iloc[0])

            if "currency" in profile_cols:
                candidate_currency = str(profile_df[profile_cols["currency"]].iloc[0])

            if "name" in profile_cols:
                candidate_description = str(profile_df[profile_cols["name"]].iloc[0])

        hypothetical_df["ScenarioType"] = "Current"
        hypothetical_df["NewPositionValue"] = hypothetical_df["PositionValue"] * (1 - candidate_weight_pct / 100)

        new_row = pd.DataFrame([{
            "Symbol": symbol,
            "Description": candidate_description,
            "sector": candidate_sector,
            "CurrencyPrimary": candidate_currency,
            "PositionValue": hypothetical_value,
            "ScenarioType": "Hypothetical Add",
            "NewPositionValue": hypothetical_value,
        }])

        compare_df = pd.concat([hypothetical_df, new_row], ignore_index=True)

        current_weights_df = (
            portfolio_df.groupby(["Symbol", "sector", "CurrencyPrimary"], dropna=False)["PositionValue"]
            .sum()
            .reset_index()
        )
        current_weights_df["Weight"] = current_weights_df["PositionValue"] / current_weights_df["PositionValue"].sum()
        current_weights_df["Portfolio"] = "Current"

        hypothetical_weights_df = (
            compare_df.groupby(["Symbol", "sector", "CurrencyPrimary"], dropna=False)["NewPositionValue"]
            .sum()
            .reset_index()
        )
        hypothetical_weights_df["Weight"] = hypothetical_weights_df["NewPositionValue"] / hypothetical_weights_df["NewPositionValue"].sum()
        hypothetical_weights_df["Portfolio"] = "Hypothetical"

        weight_compare = current_weights_df[["Symbol", "Weight"]].merge(
            hypothetical_weights_df[["Symbol", "Weight"]],
            on="Symbol",
            how="outer",
            suffixes=("_Current", "_Hypothetical"),
        ).fillna(0.0)

        weight_compare["WeightChange"] = weight_compare["Weight_Hypothetical"] - weight_compare["Weight_Current"]
        weight_compare = weight_compare.sort_values("Weight_Hypothetical", ascending=False)

        st.markdown("### Allocation Impact")

        st.dataframe(
            weight_compare.style.format({
                "Weight_Current": "{:.2%}",
                "Weight_Hypothetical": "{:.2%}",
                "WeightChange": "{:+.2%}",
            }),
            use_container_width=True,
        )

        fig_alloc = px.bar(
            weight_compare.head(15),
            x="Symbol",
            y=["Weight_Current", "Weight_Hypothetical"],
            barmode="group",
            title="Top Allocation Changes",
        )
        st.plotly_chart(fig_alloc, use_container_width=True)

        st.markdown("### Sector Exposure Impact")

        current_sector = (
            current_weights_df.groupby("sector", dropna=False)["Weight"]
            .sum()
            .reset_index()
            .rename(columns={"Weight": "Current"})
        )
        hypothetical_sector = (
            hypothetical_weights_df.groupby("sector", dropna=False)["Weight"]
            .sum()
            .reset_index()
            .rename(columns={"Weight": "Hypothetical"})
        )

        sector_compare = current_sector.merge(hypothetical_sector, on="sector", how="outer").fillna(0.0)
        sector_compare["Change"] = sector_compare["Hypothetical"] - sector_compare["Current"]

        st.dataframe(
            sector_compare.style.format({
                "Current": "{:.2%}",
                "Hypothetical": "{:.2%}",
                "Change": "{:+.2%}",
            }),
            use_container_width=True,
        )

        fig_sector = px.bar(
            sector_compare,
            x="sector",
            y=["Current", "Hypothetical"],
            barmode="group",
            title="Sector Exposure Comparison",
        )
        st.plotly_chart(fig_sector, use_container_width=True)

        st.markdown("### Currency Exposure Impact")

        current_currency = (
            current_weights_df.groupby("CurrencyPrimary", dropna=False)["Weight"]
            .sum()
            .reset_index()
            .rename(columns={"Weight": "Current"})
        )
        hypothetical_currency = (
            hypothetical_weights_df.groupby("CurrencyPrimary", dropna=False)["Weight"]
            .sum()
            .reset_index()
            .rename(columns={"Weight": "Hypothetical"})
        )

        currency_compare = current_currency.merge(
            hypothetical_currency,
            on="CurrencyPrimary",
            how="outer",
        ).fillna(0.0)

        currency_compare["Change"] = currency_compare["Hypothetical"] - currency_compare["Current"]

        st.dataframe(
            currency_compare.style.format({
                "Current": "{:.2%}",
                "Hypothetical": "{:.2%}",
                "Change": "{:+.2%}",
            }),
            use_container_width=True,
        )

        fig_currency = px.bar(
            currency_compare,
            x="CurrencyPrimary",
            y=["Current", "Hypothetical"],
            barmode="group",
            title="Currency Exposure Comparison",
        )
        st.plotly_chart(fig_currency, use_container_width=True)

        st.markdown("### Concentration Check")

        current_max_weight = current_weights_df["Weight"].max()
        hypothetical_max_weight = hypothetical_weights_df["Weight"].max()

        c1, c2, c3 = st.columns(3)

        with c1:
            st.metric("Added Weight", f"{candidate_weight_pct:.0f}%")

        with c2:
            st.metric("Current Max Position", f"{current_max_weight:.2%}")

        with c3:
            st.metric("Hypothetical Max Position", f"{hypothetical_max_weight:.2%}")

        if hypothetical_max_weight > current_max_weight:
            st.warning("This hypothetical addition increases portfolio concentration in at least one name.")
        else:
            st.success("This hypothetical addition does not increase top-position concentration.")
else:
    st.info("Upload a portfolio first if you want benchmark and portfolio analytics.")
